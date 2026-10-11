"""Extract IMD's 2015 daily gridded rainfall nodes inside GCC divisions.

The source NetCDF is never modified. The output retains one row per grid point
and source date, including explicit missing observations.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import netcdf_file
from shapely.geometry import Point, shape
from shapely.ops import unary_union

from validate_chennai_sources import PROJECT_ROOT, validate_manifest


SOURCE_ID = "imd-daily-gridded-rainfall-025-2015"
SOURCE_PATH = PROJECT_ROOT / "data/raw/chennai/imd-rainfall-grid-025-2015.nc"
BOUNDARIES_PATH = PROJECT_ROOT / "data/processed/chennai/gcc-divisions-2022.geojson"
OUTPUT_CSV = PROJECT_ROOT / "data/processed/chennai/imd-rainfall-grid-025-2015-chennai.csv"
OUTPUT_AUDIT = PROJECT_ROOT / "data/processed/chennai/imd-rainfall-grid-025-2015-audit.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _load_axes_and_rainfall(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    with netcdf_file(path, "r", mmap=False) as dataset:
        required = {"TIME", "LATITUDE", "LONGITUDE", "RAINFALL"}
        if not required.issubset(dataset.variables):
            raise ValueError(f"Missing NetCDF variables: {sorted(required - set(dataset.variables))}")
        time_var = dataset.variables["TIME"]
        lat_var = dataset.variables["LATITUDE"]
        lon_var = dataset.variables["LONGITUDE"]
        rainfall_var = dataset.variables["RAINFALL"]
        time_units = getattr(time_var, "units", b"")
        rain_units = getattr(rainfall_var, "units", b"")
        lat_units = getattr(lat_var, "units", b"")
        lon_units = getattr(lon_var, "units", b"")
        to_text = lambda value: value.decode() if isinstance(value, bytes) else str(value)
        if to_text(time_units) != "days since 1900-12-31 00:00:00":
            raise ValueError(f"Unsupported time coordinate: {to_text(time_units)}")
        if to_text(rain_units).casefold() != "mm":
            raise ValueError(f"Unsupported rainfall units: {to_text(rain_units)}")
        if to_text(lat_units) != "degrees_north" or to_text(lon_units) != "degrees_east":
            raise ValueError("Unexpected geographic coordinate axis units")
        time = np.array(time_var[:], dtype=np.float64)
        latitude = np.array(lat_var[:], dtype=np.float64)
        longitude = np.array(lon_var[:], dtype=np.float64)
        rainfall = np.array(rainfall_var[:], dtype=np.float64)
        missing_value = float(getattr(rainfall_var, "missing_value", np.nan))

    if rainfall.shape != (len(time), len(latitude), len(longitude)):
        raise ValueError("RAINFALL axis order/shape differs from documented NetCDF variables")
    expected_start = float((datetime(2015, 1, 1) - datetime(1900, 12, 31)).days)
    expected_end = float((datetime(2015, 12, 31) - datetime(1900, 12, 31)).days)
    if (
        len(time) != 365
        or time[0] != expected_start
        or time[-1] != expected_end
        or not np.array_equal(np.diff(time), np.ones(364, dtype=np.float64))
    ):
        raise ValueError("The 2015 file does not contain 365 consecutive daily coordinates for 2015")
    if not np.all(np.diff(latitude) > 0) or not np.all(np.diff(longitude) > 0):
        raise ValueError("Coordinate axes must be strictly increasing")
    if not np.allclose(np.diff(latitude), 0.25) or not np.allclose(np.diff(longitude), 0.25):
        raise ValueError("Source coordinate spacing is not the documented 0.25 degrees")
    return time, latitude, longitude, rainfall, missing_value


def process(*, force: bool = False) -> dict[str, Any]:
    manifest_result = validate_manifest(PROJECT_ROOT / "data/manifest.yaml")
    if not manifest_result["integrity_ok"]:
        raise ValueError("Raw-source manifest verification failed: " + "; ".join(manifest_result["errors"]))
    if not BOUNDARIES_PATH.is_file():
        raise FileNotFoundError(f"Processed GCC divisions are missing: {BOUNDARIES_PATH}")
    if not force and (OUTPUT_CSV.exists() or OUTPUT_AUDIT.exists()):
        raise FileExistsError("Processed output exists; pass --force to replace this pipeline's outputs")
    source_hash = _sha256(SOURCE_PATH)

    boundary_collection = json.loads(BOUNDARIES_PATH.read_text(encoding="utf-8"))
    gcc_union = unary_union([shape(feature["geometry"]) for feature in boundary_collection["features"]])
    time, latitude, longitude, rainfall, missing_value = _load_axes_and_rainfall(SOURCE_PATH)
    inside_grid_nodes = [
        (lat_index, lon_index, float(lat), float(lon))
        for lat_index, lat in enumerate(latitude)
        for lon_index, lon in enumerate(longitude)
        if gcc_union.covers(Point(float(lon), float(lat)))
    ]
    if not inside_grid_nodes:
        raise ValueError("No IMD grid nodes fall within the authoritative GCC division union")

    records: list[dict[str, Any]] = []
    missing_records = 0
    negative_records = 0
    for lat_index, lon_index, lat, lon in inside_grid_nodes:
        grid_id = f"IMD025-{lon:.2f}-{lat:.2f}"
        for time_index, time_value in enumerate(time):
            date = datetime(1900, 12, 31) + timedelta(days=int(time_value))
            value = float(rainfall[time_index, lat_index, lon_index])
            is_missing = not np.isfinite(value) or value == missing_value
            if not is_missing and value < 0:
                negative_records += 1
                raise ValueError(f"Unexpected negative rainfall at {grid_id} on {date.date()}: {value}")
            if is_missing:
                missing_records += 1
                rainfall_mm = ""
                source_status = "MISSING"
            else:
                rainfall_mm = f"{value:.6g}"
                source_status = "DERIVED_FROM_VERIFIED_IMD_GRID"
            records.append(
                {
                    "source_id": SOURCE_ID,
                    "grid_id": grid_id,
                    "latitude": f"{lat:.8f}",
                    "longitude": f"{lon:.8f}",
                    "date": date.date().isoformat(),
                    "rainfall_mm": rainfall_mm,
                    "source_status": source_status,
                    "source_sha256": source_hash,
                }
            )

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    audit = {
        "source_id": SOURCE_ID,
        "source_file": SOURCE_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "source_sha256": source_hash,
        "source_crs_note": "Geographic longitude/latitude axes; datum is not declared in the NetCDF.",
        "metric_transform_applied": False,
        "selection_geometry": "Union of repaired GCC 2022 divisions, serialized in the pipeline's EPSG:4326 coordinates.",
        "selection_rule": "Grid point is included only when the GCC union covers its longitude/latitude point.",
        "grid_nodes_inside_gcc": [
            {"grid_id": f"IMD025-{lon:.2f}-{lat:.2f}", "latitude": lat, "longitude": lon}
            for _, _, lat, lon in inside_grid_nodes
        ],
        "daily_records": len(records),
        "missing_records": missing_records,
        "invalid_negative_records": negative_records,
        "date_min": records[0]["date"],
        "date_max": records[-1]["date"],
        "daily_semantics": "IMD daily rainfall; published date labels each 24-hour accumulation ending 08:30 IST on that date.",
        "raw_file_unchanged": True,
        "output_csv": OUTPUT_CSV.relative_to(PROJECT_ROOT).as_posix(),
    }
    OUTPUT_AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Replace processed output from this pipeline")
    arguments = parser.parse_args()
    print(json.dumps(process(force=arguments.force), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
