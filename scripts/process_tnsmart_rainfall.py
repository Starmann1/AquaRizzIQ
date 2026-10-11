"""Process the retained TN-SMART daily Chennai station snapshot."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from shapely.geometry import Point, shape
from shapely.ops import unary_union

from validate_chennai_sources import PROJECT_ROOT, sha256_file, validate_manifest


SOURCE_ID = "tnsmart-daily-rainfall-2026-10-11"
SOURCE_PATH = PROJECT_ROOT / "data/raw/chennai/tnsmart-daily-rainfall-page-2026-10-11.html"
BOUNDARIES_PATH = PROJECT_ROOT / "data/processed/chennai/gcc-divisions-2022.geojson"
OUTPUT_PATH = PROJECT_ROOT / "data/processed/chennai/tnsmart-rainfall-2026-10-11.geojson"
AUDIT_PATH = PROJECT_ROOT / "data/processed/chennai/tnsmart-rainfall-2026-10-11-audit.json"
EXPECTED_DATE = "2026-10-11"
EXPECTED_INTERVAL = "From 10-Oct-2026, 08:30 AM To  11-Oct-2026, 08:30 AM"


def _read_source_records(path: Path) -> list[dict[str, Any]]:
    html = path.read_text(encoding="utf-8", errors="replace")
    if EXPECTED_INTERVAL not in html or "All units are shown in mm" not in html:
        raise ValueError("The retained TN-SMART page does not declare the expected interval and mm units")

    marker = "var rainfall_data = "
    start = html.find(marker)
    if start < 0:
        raise ValueError("TN-SMART daily page is missing its embedded rainfall_data array")
    start += len(marker)
    end = html.find("];", start)
    if end < 0:
        raise ValueError("TN-SMART daily rainfall array is unterminated")

    records = json.loads(html[start : end + 1])
    chennai_records = [
        record
        for record in records
        if str(record.get("district_name", "")).strip().casefold() == "chennai"
    ]
    if not chennai_records:
        raise ValueError("TN-SMART daily page contains no Chennai station records")
    return chennai_records


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    required = ("date", "location_name", "district_name", "station_code", "source", "latitude", "longitude", "rainfall")
    missing = [field for field in required if record.get(field) in (None, "")]
    if missing:
        raise ValueError(f"TN-SMART station record is missing fields: {missing}")
    if record["date"] != EXPECTED_DATE:
        raise ValueError(f"Unexpected TN-SMART observation date: {record['date']!r}")

    latitude = float(record["latitude"])
    longitude = float(record["longitude"])
    rainfall_mm = float(record["rainfall"])
    if not all(math.isfinite(value) for value in (latitude, longitude, rainfall_mm)):
        raise ValueError(f"Non-finite TN-SMART station value for {record['station_code']}")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError(f"Out-of-range TN-SMART coordinates for {record['station_code']}")
    if rainfall_mm < 0:
        raise ValueError(f"Negative TN-SMART rainfall for {record['station_code']}")

    return {
        "date": record["date"],
        "station_code": str(record["station_code"]).strip(),
        "station_name": str(record["location_name"]).strip(),
        "district": str(record["district_name"]).strip(),
        "reporting_agency": str(record["source"]).strip(),
        "latitude": latitude,
        "longitude": longitude,
        "rainfall_mm": rainfall_mm,
    }


def process(*, force: bool = False) -> dict[str, Any]:
    manifest_result = validate_manifest(PROJECT_ROOT / "data/manifest.yaml")
    if not manifest_result["integrity_ok"]:
        raise ValueError("Raw-source manifest verification failed: " + "; ".join(manifest_result["errors"]))
    if not BOUNDARIES_PATH.is_file():
        raise FileNotFoundError(f"Processed GCC divisions are missing: {BOUNDARIES_PATH}")
    if not force and (OUTPUT_PATH.exists() or AUDIT_PATH.exists()):
        raise FileExistsError("Processed TN-SMART output exists; pass --force to replace it")

    source_records = _read_source_records(SOURCE_PATH)
    records = [_normalize_record(record) for record in source_records]
    station_codes = [record["station_code"] for record in records]
    if len(station_codes) != len(set(station_codes)):
        raise ValueError("TN-SMART Chennai station codes are not unique for the observation date")

    boundaries = json.loads(BOUNDARIES_PATH.read_text(encoding="utf-8"))
    gcc_union = unary_union([shape(feature["geometry"]) for feature in boundaries["features"]])
    inside: list[dict[str, Any]] = []
    outside: list[dict[str, Any]] = []
    for record in records:
        point = Point(record["longitude"], record["latitude"])
        (inside if gcc_union.covers(point) else outside).append(record)

    source_hash = sha256_file(SOURCE_PATH)
    source_url = "https://tnsmart-beta.rimes.int/index.php/Rainfall/daily_data"
    coordinate_note = (
        "Coordinates are published in the source's embedded GeoJSON point layer and rendered by its Leaflet map. "
        "Datum is unspecified; no datum transformation is applied."
    )
    features = [
        {
            "type": "Feature",
            "id": record["station_code"],
            "geometry": {"type": "Point", "coordinates": [record["longitude"], record["latitude"]]},
            "properties": {
                "station_id": record["station_code"],
                "station_name": record["station_name"],
                "district": record["district"],
                "reporting_agency": record["reporting_agency"],
                "observation_date": record["date"],
                "rainfall_mm": record["rainfall_mm"],
                "units": "mm",
                "measurement_interval": EXPECTED_INTERVAL,
                "source_id": SOURCE_ID,
                "source_url": source_url,
                "source_sha256": source_hash,
                "coordinate_note": coordinate_note,
                "risk_input_eligible": False,
            },
        }
        for record in inside
    ]
    collection = {
        "type": "FeatureCollection",
        "features": features,
        "dataset_metadata": {
            "status": "SOURCE_RENDERED_DAILY_STATION_OBSERVATIONS",
            "source_id": SOURCE_ID,
            "source_sha256": source_hash,
            "observation_date": EXPECTED_DATE,
            "measurement_interval": EXPECTED_INTERVAL,
            "units": "mm",
            "station_count_chennai": len(records),
            "station_count_inside_gcc": len(inside),
            "station_count_outside_gcc": len(outside),
            "mapped_feature_count": len(features),
            "positive_rainfall_station_count": sum(record["rainfall_mm"] > 0 for record in inside),
            "risk_input_eligible": False,
            "coordinate_reference_note": coordinate_note,
            "output_crs": "Coordinates preserved as published; no datum transformation. Source datum is unspecified.",
            "limitation": (
                "Single dated 24-hour snapshot, not a live feed or forecast. Source coordinates are mapped using "
                "the source page's own GeoJSON/Leaflet rendering convention; datum is not explicitly stated. "
                "Not used for ward-level risk calculations."
            ),
        },
    }
    audit = {
        "source_id": SOURCE_ID,
        "source_sha256": source_hash,
        "observation_date": EXPECTED_DATE,
        "measurement_interval": EXPECTED_INTERVAL,
        "units": "mm",
        "source_page_geojson_point_layer": True,
        "coordinate_datum_explicit": False,
        "coordinate_rendering_convention": "The source constructs GeoJSON Point features [longitude, latitude] and passes them to Leaflet L.geoJSON on the source map.",
        "metric_transform_applied": False,
        "source_record_count_chennai": len(records),
        "unique_station_code_count": len(set(station_codes)),
        "source_duplicate_station_codes": [],
        "inside_gcc_station_count": len(inside),
        "outside_gcc_station_count": len(outside),
        "outside_gcc_station_codes": [record["station_code"] for record in outside],
        "positive_rainfall_inside_gcc_count": sum(record["rainfall_mm"] > 0 for record in inside),
        "missing_or_invalid_record_count": 0,
        "risk_input_eligible": False,
        "raw_file_unchanged": True,
        "output_feature_count": len(features),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(collection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Replace processed output from this pipeline")
    arguments = parser.parse_args()
    print(json.dumps(process(force=arguments.force), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
