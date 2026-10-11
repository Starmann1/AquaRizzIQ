"""Normalize the verified GCC 2022 KML boundaries into RFC 7946 GeoJSON.

Original KML files are never modified. Invalid source rings require an explicit
``--repair-invalid`` choice; each repair is checked, measured, and written to an
audit report. Zone assignment is a derived overlay and is withheld when the
largest zone intersection covers less than 99 percent of a division.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

import pyproj
import shapely
from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.ops import unary_union
from shapely.validation import explain_validity, make_valid

from validate_chennai_sources import PROJECT_ROOT, KML_NAMESPACE, validate_manifest


RAW_DIRECTORY = PROJECT_ROOT / "data" / "raw" / "chennai"
OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "processed" / "chennai"
ZONE_JOIN_MIN_FRACTION = 0.99
MAX_REPAIR_AREA_CHANGE_PERCENT = 0.01
TO_METRIC = pyproj.Transformer.from_crs(4326, 32644, always_xy=True).transform


def _to_metric(geometry: Any) -> Any:
    return shapely.transform(geometry, TO_METRIC, interleaved=False)


def _parse_ring(coordinates: str | None) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for item in (coordinates or "").split():
        values = item.split(",")
        if len(values) < 2:
            raise ValueError(f"Malformed KML coordinate tuple: {item!r}")
        longitude, latitude = float(values[0]), float(values[1])
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise ValueError(f"Out-of-range longitude/latitude: {item!r}")
        points.append((longitude, latitude))
    return points


def _polygonal_parts(geometry: Any) -> list[Polygon]:
    if geometry.geom_type == "Polygon":
        return [geometry]
    if hasattr(geometry, "geoms"):
        parts: list[Polygon] = []
        for item in geometry.geoms:
            parts.extend(_polygonal_parts(item))
        return parts
    return []


def _feature_properties(placemark: ET.Element) -> dict[str, str]:
    return {
        element.attrib["name"]: (element.text or "").strip()
        for element in placemark.findall(".//kml:SimpleData", KML_NAMESPACE)
        if element.attrib.get("name")
    }


def _zone_number(value: str) -> int:
    match = re.search(r"([IVXLCDM]+)\s*$", value.strip(), flags=re.IGNORECASE)
    if match is None:
        raise ValueError(f"Zone has no parseable Roman numeral: {value!r}")
    numerals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = previous = 0
    for character in reversed(match.group(1).upper()):
        current = numerals[character]
        total += -current if current < previous else current
        previous = max(previous, current)
    return total


def _load_kml_polygons(
    path: Path,
    *,
    identifier_field: str,
    allow_repair: bool,
    audit: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    root = ET.parse(path).getroot()
    if root.tag != f"{{{KML_NAMESPACE['kml']}}}kml":
        raise ValueError(f"{path.name} is not KML 2.2")
    records: list[dict[str, Any]] = []

    for placemark in root.findall(".//kml:Placemark", KML_NAMESPACE):
        name = (placemark.findtext("kml:name", default="", namespaces=KML_NAMESPACE) or "").strip()
        properties = _feature_properties(placemark)
        identifiers = [name, properties.get(identifier_field, "")]
        feature_id = next((value for value in identifiers if value), "")
        if not feature_id:
            audit.append({"source_feature": "<unnamed>", "action": "excluded", "reason": "missing identifier"})
            continue

        polygon_parts: list[Polygon] = []
        for polygon_element in placemark.findall(".//kml:Polygon", KML_NAMESPACE):
            outer = polygon_element.find(
                "./kml:outerBoundaryIs/kml:LinearRing/kml:coordinates", KML_NAMESPACE
            )
            if outer is None:
                raise ValueError(f"Feature {feature_id} has a polygon without an outer ring")
            exterior = _parse_ring(outer.text)
            holes = [
                _parse_ring(element.text)
                for element in polygon_element.findall(
                    "./kml:innerBoundaryIs/kml:LinearRing/kml:coordinates",
                    KML_NAMESPACE,
                )
            ]
            original = Polygon(exterior, holes)
            if not original.is_valid:
                reason = explain_validity(original)
                if not allow_repair:
                    raise ValueError(
                        f"Feature {feature_id} has invalid geometry ({reason}); "
                        "rerun with --repair-invalid after reviewing the audit findings"
                    )
                repaired = make_valid(original)
                polygonal = _polygonal_parts(repaired)
                if not polygonal or any(not item.is_valid for item in polygonal):
                    raise ValueError(f"Feature {feature_id} could not be repaired to valid polygon geometry")
                before_area = _to_metric(original).area
                after_area = sum(_to_metric(item).area for item in polygonal)
                change_percent = abs(after_area - before_area) / after_area * 100 if after_area else 0.0
                if change_percent > MAX_REPAIR_AREA_CHANGE_PERCENT:
                    raise ValueError(
                        f"Feature {feature_id} repair changes projected area by "
                        f"{change_percent:.6f}% (limit {MAX_REPAIR_AREA_CHANGE_PERCENT}%)"
                    )
                audit.append(
                    {
                        "source_feature": feature_id,
                        "action": "make_valid",
                        "reason": reason,
                        "output_geometry_types": sorted({item.geom_type for item in polygonal}),
                        "output_polygon_parts": len(polygonal),
                        "projected_area_before_m2": round(before_area, 6),
                        "projected_area_after_m2": round(after_area, 6),
                        "projected_area_change_percent": round(change_percent, 9),
                        "source_bytes_modified": False,
                    }
                )
                polygon_parts.extend(polygonal)
            else:
                polygon_parts.append(original)

        if not polygon_parts:
            audit.append({"source_feature": feature_id, "action": "excluded", "reason": "no polygon geometry"})
            continue
        dissolved = unary_union(polygon_parts)
        final_parts = _polygonal_parts(dissolved)
        if not final_parts or any(not item.is_valid for item in final_parts):
            raise ValueError(f"Feature {feature_id} did not normalize to valid polygon geometry")
        records.append(
            {
                "source_id": feature_id,
                "properties": properties,
                "geometry": MultiPolygon(final_parts),
            }
        )
    return records


def _feature(geometry: Any, properties: dict[str, Any]) -> dict[str, Any]:
    return {"type": "Feature", "geometry": mapping(geometry), "properties": properties}


def _write_json(path: Path, value: Any, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing output: {path}; pass --force to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def import_boundaries(*, allow_repair: bool, force: bool) -> dict[str, Any]:
    validation = validate_manifest(PROJECT_ROOT / "data" / "manifest.yaml")
    if not validation["integrity_ok"]:
        raise ValueError("Source integrity check failed: " + "; ".join(validation["errors"]))

    audit: list[dict[str, Any]] = []
    divisions = _load_kml_polygons(
        RAW_DIRECTORY / "gcc-wards-2022.kml",
        identifier_field="id_2",
        allow_repair=allow_repair,
        audit=audit,
    )
    zones_all = _load_kml_polygons(
        RAW_DIRECTORY / "gcc-zones-2022.kml",
        identifier_field="ZONE_NAME",
        allow_repair=allow_repair,
        audit=audit,
    )

    zone_records: list[dict[str, Any]] = []
    for zone in zones_all:
        zone_name = zone["properties"].get("ZONE_NAME", "").strip()
        zone_number_text = zone["properties"].get("ZONE", "").strip()
        if not zone_name or not zone_number_text:
            audit.append(
                {"source_feature": zone["source_id"], "action": "excluded", "reason": "unnamed zone polygon"}
            )
            continue
        number = _zone_number(zone_number_text)
        zone_records.append(
            {
                "zone_id": f"ZONE-{number:02d}",
                "zone_number": number,
                "zone_name": zone_name,
                "region": zone["properties"].get("Region"),
                "geometry": zone["geometry"],
            }
        )

    division_numbers: set[int] = set()
    for division in divisions:
        try:
            number = int(division["source_id"])
        except ValueError as error:
            raise ValueError(f"Unexpected division identifier: {division['source_id']!r}") from error
        division_numbers.add(number)
        division["number"] = number
    if division_numbers != set(range(1, 201)):
        raise ValueError("2022 division identifiers are not exactly 1 through 200")
    if len(zone_records) != 15 or {zone["zone_number"] for zone in zone_records} != set(range(1, 16)):
        raise ValueError("2022 zone identifiers are not exactly 1 through 15")

    zone_features = [
        _feature(
            zone["geometry"],
            {
                "zone_id": zone["zone_id"],
                "zone_number": zone["zone_number"],
                "zone_name": zone["zone_name"],
                "region": zone["region"],
                "source_id": "gcc-zones-2022",
                "geometry_repaired": any(
                    item["source_feature"] == zone["zone_name"] and item["action"] == "make_valid"
                    for item in audit
                ),
            },
        )
        for zone in zone_records
    ]

    division_features: list[dict[str, Any]] = []
    join_counts: Counter[str] = Counter()
    ambiguous_divisions: list[dict[str, Any]] = []
    for division in divisions:
        geometry = division["geometry"]
        metric_geometry = _to_metric(geometry)
        ranked = sorted(
            (
                (
                    metric_geometry.intersection(_to_metric(zone["geometry"])).area
                    / metric_geometry.area,
                    zone,
                )
                for zone in zone_records
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )
        match_fraction, candidate = ranked[0]
        if match_fraction >= ZONE_JOIN_MIN_FRACTION:
            zone_id: str | None = candidate["zone_id"]
            zone_name: str | None = candidate["zone_name"]
            join_status = "MATCHED"
        else:
            zone_id = zone_name = None
            join_status = "AMBIGUOUS"
            ambiguous_divisions.append(
                {
                    "ward_id": f"WARD-{division['number']:03d}",
                    "candidate_zone_id": candidate["zone_id"],
                    "candidate_zone_name": candidate["zone_name"],
                    "intersection_fraction": round(match_fraction, 8),
                }
            )
        join_counts[join_status] += 1
        repaired = any(
            item["source_feature"] == division["source_id"] and item["action"] == "make_valid"
            for item in audit
        )
        division_features.append(
            _feature(
                geometry,
                {
                    "ward_id": f"WARD-{division['number']:03d}",
                    "ward_number": division["number"],
                    "name": f"Ward {division['number']}",
                    "zone_id": zone_id,
                    "zone": zone_name,
                    "zone_join_status": join_status,
                    "zone_join_fraction": round(match_fraction, 8),
                    "zone_candidate_id": candidate["zone_id"],
                    "zone_candidate": candidate["zone_name"],
                    "source_id": "gcc-divisions-2022",
                    "geometry_repaired": repaired,
                    "data_classification": "OBSERVED_BOUNDARY",
                },
            )
        )

    audit_report = {
        "source_files_unchanged": True,
        "crs_input": "EPSG:4326 (KML 2.2 WGS 84 longitude/latitude)",
        "metric_area_crs": "EPSG:32644",
        "output_crs": "EPSG:4326 per RFC 7946 GeoJSON",
        "repair_policy": {
            "enabled": allow_repair,
            "method": "Shapely make_valid",
            "maximum_projected_area_change_percent": MAX_REPAIR_AREA_CHANGE_PERCENT,
        },
        "repairs_and_exclusions": audit,
        "ward_count": len(division_features),
        "zone_count": len(zone_features),
        "zone_join_min_fraction": ZONE_JOIN_MIN_FRACTION,
        "zone_join_counts": dict(join_counts),
        "ambiguous_zone_joins": ambiguous_divisions,
    }

    _write_json(
        OUTPUT_DIRECTORY / "gcc-divisions-2022.geojson",
        {"type": "FeatureCollection", "name": "GCC Divisions 2022", "features": division_features},
        force=force,
    )
    _write_json(
        OUTPUT_DIRECTORY / "gcc-zones-2022.geojson",
        {"type": "FeatureCollection", "name": "GCC Zones 2022", "features": zone_features},
        force=force,
    )
    _write_json(OUTPUT_DIRECTORY / "boundary-import-audit.json", audit_report, force=force)
    return audit_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repair-invalid",
        action="store_true",
        help="Explicitly run audited Shapely make_valid repairs for source rings",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing generated files under data/processed/chennai/",
    )
    args = parser.parse_args()
    try:
        report = import_boundaries(allow_repair=args.repair_invalid, force=args.force)
    except (ET.ParseError, OSError, ValueError, FileExistsError) as error:
        print(f"Boundary import failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
