"""Verify locally retained Chennai source files against their provenance manifest.

This command is read-only. It never repairs or rewrites source data. Geometry
issues and rainfall ambiguities are reported as findings, not silently fixed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
import numpy as np
import pandas as pd
from scipy.io import netcdf_file
from shapely.geometry import Polygon
from shapely.validation import explain_validity


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KML_NAMESPACE = {"kml": "http://www.opengis.net/kml/2.2"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _parse_coordinates(text: str | None) -> list[tuple[float, float]]:
    coordinates: list[tuple[float, float]] = []
    for coordinate in (text or "").split():
        values = coordinate.split(",")
        if len(values) < 2:
            raise ValueError(f"Malformed KML coordinate tuple: {coordinate!r}")
        longitude, latitude = float(values[0]), float(values[1])
        if not math.isfinite(longitude) or not math.isfinite(latitude):
            raise ValueError(f"Non-finite KML coordinate tuple: {coordinate!r}")
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise ValueError(f"Out-of-range KML coordinate tuple: {coordinate!r}")
        coordinates.append((longitude, latitude))
    return coordinates


def summarize_kml(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    if root.tag != f"{{{KML_NAMESPACE['kml']}}}kml":
        raise ValueError("Document root is not KML 2.2")

    placemarks = root.findall(".//kml:Placemark", KML_NAMESPACE)
    polygon_count = point_count = coordinate_count = 0
    invalid_polygons: list[dict[str, str]] = []
    coordinate_errors: list[str] = []
    all_coordinates: list[tuple[float, float]] = []
    names: list[str] = []

    for placemark in placemarks:
        name = (placemark.findtext("kml:name", default="", namespaces=KML_NAMESPACE) or "").strip()
        names.append(name)
        for polygon_element in placemark.findall(".//kml:Polygon", KML_NAMESPACE):
            polygon_count += 1
            outer = polygon_element.find(
                "./kml:outerBoundaryIs/kml:LinearRing/kml:coordinates", KML_NAMESPACE
            )
            if outer is None:
                coordinate_errors.append(f"{name or '<unnamed>'}: polygon has no outer ring")
                continue
            try:
                exterior = _parse_coordinates(outer.text)
                holes = [
                    _parse_coordinates(element.text)
                    for element in polygon_element.findall(
                        "./kml:innerBoundaryIs/kml:LinearRing/kml:coordinates",
                        KML_NAMESPACE,
                    )
                ]
                all_coordinates.extend(exterior)
                for hole in holes:
                    all_coordinates.extend(hole)
                geometry = Polygon(exterior, holes)
                if not geometry.is_valid:
                    invalid_polygons.append(
                        {"feature": name or "<unnamed>", "reason": explain_validity(geometry)}
                    )
            except (TypeError, ValueError) as error:
                coordinate_errors.append(f"{name or '<unnamed>'}: {error}")

        for point_element in placemark.findall(".//kml:Point", KML_NAMESPACE):
            point_count += 1
            coordinates = point_element.find("kml:coordinates", KML_NAMESPACE)
            try:
                parsed = _parse_coordinates(coordinates.text if coordinates is not None else None)
                if len(parsed) != 1:
                    raise ValueError("Point must contain exactly one coordinate tuple")
                all_coordinates.extend(parsed)
            except (TypeError, ValueError) as error:
                coordinate_errors.append(f"{name or '<unnamed>'}: {error}")

    coordinate_count = len(all_coordinates)
    bounds = None
    if all_coordinates:
        longitudes, latitudes = zip(*all_coordinates)
        bounds = [min(longitudes), min(latitudes), max(longitudes), max(latitudes)]

    return {
        "placemarks": len(placemarks),
        "unique_nonempty_names": len({name for name in names if name}),
        "unnamed_placemarks": sum(not name for name in names),
        "polygon_components": polygon_count,
        "point_components": point_count,
        "coordinate_count": coordinate_count,
        "longitude_latitude_bounds": bounds,
        "invalid_polygon_count": len(invalid_polygons),
        "invalid_polygon_examples": invalid_polygons[:12],
        "coordinate_errors": coordinate_errors[:12],
    }


def summarize_rainfall(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames or []
        required = {"District", "Station", "Rainfall", "Date"}
        if not required.issubset(fields):
            raise ValueError(f"Missing required rainfall fields: {sorted(required - set(fields))}")
        rows = list(reader)

    blank_counts = {field: 0 for field in fields}
    duplicate_counts: Counter[tuple[str, str]] = Counter()
    duplicate_values: dict[tuple[str, str], set[str]] = defaultdict(set)
    stations: set[str] = set()
    districts: set[str] = set()
    dates: list[datetime] = []
    rainfall_values: list[float] = []
    parse_errors = 0
    negative_values = 0

    for row in rows:
        for field in fields:
            if not (row.get(field) or "").strip():
                blank_counts[field] += 1
        station = (row.get("Station") or "").strip()
        date_text = (row.get("Date") or "").strip()
        stations.add(station)
        districts.add((row.get("District") or "").strip())
        key = (station.casefold(), date_text)
        duplicate_counts[key] += 1
        duplicate_values[key].add((row.get("Rainfall") or "").strip())
        try:
            dates.append(datetime.strptime(date_text, "%d-%m-%Y"))
            rainfall = float((row.get("Rainfall") or "").strip())
            if not math.isfinite(rainfall):
                raise ValueError("non-finite rainfall")
            rainfall_values.append(rainfall)
            if rainfall < 0:
                negative_values += 1
        except ValueError:
            parse_errors += 1

    duplicate_keys = [key for key, count in duplicate_counts.items() if count > 1]
    return {
        "rows": len(rows),
        "columns": fields,
        "districts": sorted(value for value in districts if value),
        "station_name_count": len(stations - {""}),
        "date_min": min(dates).date().isoformat() if dates else None,
        "date_max": max(dates).date().isoformat() if dates else None,
        "rainfall_min": min(rainfall_values) if rainfall_values else None,
        "rainfall_max": max(rainfall_values) if rainfall_values else None,
        "negative_value_count": negative_values,
        "blank_counts": blank_counts,
        "parse_error_rows": parse_errors,
        "duplicate_station_date_keys": len(duplicate_keys),
        "duplicate_extra_rows": sum(duplicate_counts[key] - 1 for key in duplicate_keys),
        "conflicting_duplicate_keys": sum(
            len(duplicate_values[key]) > 1 for key in duplicate_keys
        ),
        "units_declared_in_file": False,
        "station_coordinates_in_file": False,
    }


def summarize_tnsmart_station_page(path: Path) -> dict[str, Any]:
    """Inspect a retained TN-SMART station page without treating its values as live."""
    tables = pd.read_html(path)
    station_table = next((table for table in tables if table.shape[1] == 8 and len(table) == 1), None)
    if station_table is None:
        raise ValueError("Expected one eight-column station row")

    row = station_table.iloc[0]
    observation_date = str(station_table.columns[0][0]).removeprefix("Raingauge stations as on ")
    return {
        "observation_date": observation_date,
        "station_name": str(row.iloc[1]),
        "location_hierarchy": str(row.iloc[2]),
        "latitude": float(row.iloc[4]),
        "longitude": float(row.iloc[5]),
        "station_status": str(row.iloc[6]),
        "rainfall_mm": float(row.iloc[7]),
        "row_count": len(station_table),
        "datum_declared": False,
    }


def summarize_tnsmart_daily_page(path: Path) -> dict[str, Any]:
    """Check published TN-SMART interval, values, coordinates, and native map semantics."""
    html = path.read_text(encoding="utf-8", errors="replace")
    expected_interval = "From 10-Oct-2026, 08:30 AM To  11-Oct-2026, 08:30 AM"
    if expected_interval not in html or "All units are shown in mm" not in html:
        raise ValueError("Daily rainfall interval or units are not present in the retained page")
    tables = pd.read_html(path)
    daily_table = next((table for table in tables if table.shape[1] == 5 and len(table) > 50), None)
    if daily_table is None:
        raise ValueError("Expected the TN-SMART daily observation table")
    chennai_rows = daily_table[
        daily_table.iloc[:, 1].astype(str).str.strip().eq("GCC")
        & daily_table.iloc[:, 2].astype(str).str.strip().eq("Chennai")
    ]
    marker = "var rainfall_data = "
    start = html.find(marker)
    if start < 0:
        raise ValueError("TN-SMART page is missing its embedded rainfall_data array")
    start += len(marker)
    end = html.find("];", start)
    if end < 0:
        raise ValueError("TN-SMART embedded rainfall_data array is unterminated")
    all_records = json.loads(html[start : end + 1])
    chennai_records = [
        row for row in all_records
        if str(row.get("district_name", "")).strip().casefold() == "chennai"
    ]
    station_codes: list[str] = []
    coordinate_errors = numeric_errors = date_errors = 0
    positive_count = 0
    for row in chennai_records:
        station_codes.append(str(row.get("station_code", "")).strip())
        try:
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                coordinate_errors += 1
        except (KeyError, TypeError, ValueError):
            coordinate_errors += 1
        try:
            rainfall = float(row["rainfall"])
            if not math.isfinite(rainfall) or rainfall < 0:
                numeric_errors += 1
            elif rainfall > 0:
                positive_count += 1
        except (KeyError, TypeError, ValueError):
            numeric_errors += 1
        if row.get("date") != "2026-10-11":
            date_errors += 1

    duplicate_station_codes = [
        code for code, count in Counter(station_codes).items() if not code or count > 1
    ]
    source_builds_geojson_points = (
        '"type" : "Point","coordinates":[' in html
        and "L.geoJSON(rainfall_location_data" in html
    )
    if not chennai_records or coordinate_errors or numeric_errors or date_errors or duplicate_station_codes:
        raise ValueError("TN-SMART embedded Chennai station data failed coordinate/value/date/duplicate checks")
    if not source_builds_geojson_points:
        raise ValueError("TN-SMART page no longer builds its source map from GeoJSON point coordinates")

    return {
        "observation_date": "2026-10-11",
        "interval": "2026-10-10 08:30 to 2026-10-11 08:30 local time",
        "units": "mm",
        "chennai_gcc_positive_table_row_count": int(len(chennai_rows)),
        "chennai_gcc_station_rows": [
            {"station": str(row.iloc[3]), "rainfall_mm": float(row.iloc[4])}
            for _, row in chennai_rows.iterrows()
        ],
        "embedded_chennai_station_count": len(chennai_records),
        "embedded_unique_station_code_count": len(set(station_codes)),
        "embedded_positive_rainfall_count": positive_count,
        "embedded_coordinate_error_count": coordinate_errors,
        "embedded_numeric_error_count": numeric_errors,
        "embedded_wrong_date_count": date_errors,
        "embedded_duplicate_station_codes": duplicate_station_codes,
        "source_geojson_point_layer": source_builds_geojson_points,
        "geodetic_datum_declared": False,
    }


def summarize_tnswgw_rainfall(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {
            "Station", "District", "Latitude", "Longitude",
            "Data Acquisition Time", "Manual Daily Rainfall (mm)",
        }
        fields = set(reader.fieldnames or [])
        if not required.issubset(fields):
            raise ValueError(f"Missing NWIC rainfall fields: {sorted(required - fields)}")
        rows = list(reader)

    districts: set[str] = set()
    stations: set[str] = set()
    locations: set[tuple[str, str]] = set()
    records: Counter[tuple[str, str, str, str]] = Counter()
    values: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    dates: list[datetime] = []
    coordinate_errors = 0
    rainfall_parse_errors = 0
    for row in rows:
        station = (row.get("Station") or "").strip()
        district = (row.get("District") or "").strip()
        latitude = (row.get("Latitude") or "").strip()
        longitude = (row.get("Longitude") or "").strip()
        acquisition_time = (row.get("Data Acquisition Time") or "").strip()
        stations.add(station)
        districts.add(district)
        try:
            lat_value, lon_value = float(latitude), float(longitude)
            if not -90 <= lat_value <= 90 or not -180 <= lon_value <= 180:
                coordinate_errors += 1
            locations.add((latitude, longitude))
        except ValueError:
            coordinate_errors += 1
        try:
            dates.append(datetime.strptime(acquisition_time, "%d-%m-%Y %H:%M"))
            rainfall = float(row["Manual Daily Rainfall (mm)"])
            if not math.isfinite(rainfall) or rainfall < 0:
                rainfall_parse_errors += 1
        except (KeyError, ValueError):
            rainfall_parse_errors += 1
        key = (station.casefold(), latitude, longitude, acquisition_time)
        records[key] += 1
        values[key].add((row.get("Manual Daily Rainfall (mm)") or "").strip())

    duplicate_keys = [key for key, count in records.items() if count > 1]
    return {
        "rows": len(rows),
        "districts": sorted(value for value in districts if value),
        "chennai_rows": sum(
            (row.get("District") or "").strip().casefold() == "chennai" for row in rows
        ),
        "station_count": len(stations - {""}),
        "distinct_coordinate_count": len(locations),
        "date_min": min(dates).isoformat() if dates else None,
        "date_max": max(dates).isoformat() if dates else None,
        "acquisition_time_distribution": dict(
            Counter(item.strftime("%H:%M") for item in dates)
        ),
        "duplicate_station_location_time_keys": len(duplicate_keys),
        "duplicate_extra_rows": sum(records[key] - 1 for key in duplicate_keys),
        "conflicting_duplicate_keys": sum(len(values[key]) > 1 for key in duplicate_keys),
        "coordinate_error_rows": coordinate_errors,
        "rainfall_parse_error_rows": rainfall_parse_errors,
        "units_declared_in_field": "Manual Daily Rainfall (mm)" in fields,
    }


def summarize_imd_netcdf(path: Path) -> dict[str, Any]:
    with netcdf_file(path, "r", mmap=False) as dataset:
        required = {"TIME", "LATITUDE", "LONGITUDE", "RAINFALL"}
        if not required.issubset(dataset.variables):
            raise ValueError(f"NetCDF is missing required variables: {sorted(required - set(dataset.variables))}")
        time = np.array(dataset.variables["TIME"][:], dtype=np.float64)
        latitude = np.array(dataset.variables["LATITUDE"][:], dtype=np.float64)
        longitude = np.array(dataset.variables["LONGITUDE"][:], dtype=np.float64)
        rainfall_variable = dataset.variables["RAINFALL"]
        rainfall = np.array(rainfall_variable[:], dtype=np.float64)
        missing_value = float(getattr(rainfall_variable, "missing_value", np.nan))
        time_units = getattr(dataset.variables["TIME"], "units", b"")
        rain_units = getattr(rainfall_variable, "units", b"")
        lat_units = getattr(dataset.variables["LATITUDE"], "units", b"")
        lon_units = getattr(dataset.variables["LONGITUDE"], "units", b"")

    time_unit_text = time_units.decode() if isinstance(time_units, bytes) else str(time_units)
    rainfall_unit_text = rain_units.decode() if isinstance(rain_units, bytes) else str(rain_units)
    latitude_unit_text = lat_units.decode() if isinstance(lat_units, bytes) else str(lat_units)
    longitude_unit_text = lon_units.decode() if isinstance(lon_units, bytes) else str(lon_units)
    if rainfall.shape != (len(time), len(latitude), len(longitude)):
        raise ValueError("RAINFALL dimensions do not match TIME, LATITUDE, LONGITUDE axes")
    if time_unit_text != "days since 1900-12-31 00:00:00":
        raise ValueError(f"Unexpected IMD time units: {time_unit_text!r}")
    if rainfall_unit_text.casefold() != "mm":
        raise ValueError(f"Unexpected rainfall units: {rainfall_unit_text!r}")

    valid = np.isfinite(rainfall) & (rainfall != missing_value)
    valid_values = rainfall[valid]
    invalid_negative_count = int(np.sum(valid_values < 0))
    date_values = [datetime(1900, 12, 31) + timedelta(days=int(value)) for value in time]
    lon_spacing = float(np.median(np.diff(longitude))) if len(longitude) > 1 else None
    lat_spacing = float(np.median(np.diff(latitude))) if len(latitude) > 1 else None
    return {
        "dimensions": {
            "time": len(time),
            "latitude": len(latitude),
            "longitude": len(longitude),
        },
        "date_min": min(date_values).date().isoformat() if date_values else None,
        "date_max": max(date_values).date().isoformat() if date_values else None,
        "time_units": time_unit_text,
        "rainfall_units": rainfall_unit_text,
        "latitude_units": latitude_unit_text,
        "longitude_units": longitude_unit_text,
        "latitude_bounds": [float(np.min(latitude)), float(np.max(latitude))],
        "longitude_bounds": [float(np.min(longitude)), float(np.max(longitude))],
        "latitude_spacing": lat_spacing,
        "longitude_spacing": lon_spacing,
        "missing_value": missing_value,
        "missing_value_count": int(np.sum(~valid)),
        "valid_value_count": int(np.sum(valid)),
        "valid_rainfall_min_mm": float(np.min(valid_values)) if valid_values.size else None,
        "valid_rainfall_max_mm": float(np.max(valid_values)) if valid_values.size else None,
        "invalid_negative_count": invalid_negative_count,
    }


def validate_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    result: dict[str, Any] = {"sources": [], "errors": []}

    for source in manifest.get("sources", []):
        file_path = (PROJECT_ROOT / source["file"]).resolve()
        try:
            file_path.relative_to(PROJECT_ROOT)
        except ValueError:
            result["errors"].append(f"{source['id']}: file path escapes the project")
            continue
        if not file_path.is_file():
            result["errors"].append(f"{source['id']}: missing file {source['file']}")
            continue

        actual_hash = sha256_file(file_path)
        actual_size = file_path.stat().st_size
        source_result: dict[str, Any] = {
            "id": source["id"],
            "file": source["file"],
            "size_bytes": actual_size,
            "size_matches": actual_size == source["size_bytes"],
            "sha256": actual_hash,
            "sha256_matches": actual_hash.casefold() == source["sha256"].casefold(),
            "status": source["status"],
        }
        if not source_result["size_matches"]:
            result["errors"].append(f"{source['id']}: file size differs from manifest")
        if not source_result["sha256_matches"]:
            result["errors"].append(f"{source['id']}: SHA-256 differs from manifest")

        try:
            if source["format"] == "CSV" and source["id"] == "tnswgw-manual-daily-rainfall-1991-2020":
                source_result["inspection"] = summarize_tnswgw_rainfall(file_path)
            elif source["format"] == "CSV":
                source_result["inspection"] = summarize_rainfall(file_path)
            elif source["format"].startswith("KML"):
                source_result["inspection"] = summarize_kml(file_path)
            elif source["format"].startswith("NetCDF"):
                source_result["inspection"] = summarize_imd_netcdf(file_path)
            elif source["format"] == "HTML" and source["id"] == "tnsmart-nungambakkam-rainfall-2026-10-11":
                source_result["inspection"] = summarize_tnsmart_station_page(file_path)
            elif source["format"] == "HTML" and source["id"] == "tnsmart-daily-rainfall-2026-10-11":
                source_result["inspection"] = summarize_tnsmart_daily_page(file_path)
            elif source["format"].startswith("PDF"):
                with file_path.open("rb") as pdf_file:
                    header = pdf_file.read(5)
                if header != b"%PDF-":
                    raise ValueError("file does not have a PDF header")
                source_result["inspection"] = {
                    "pdf_header_valid": True,
                    "content_review": "manual text and visual review recorded in source audit",
                }
            else:
                result["errors"].append(f"{source['id']}: unsupported format {source['format']}")
        except (ET.ParseError, OSError, ValueError) as error:
            result["errors"].append(f"{source['id']}: inspection failed: {error}")
        result["sources"].append(source_result)

    result["integrity_ok"] = not result["errors"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT / "data" / "manifest.yaml",
        help="Path to the provenance manifest (default: data/manifest.yaml)",
    )
    args = parser.parse_args()
    result = validate_manifest(args.manifest.resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["integrity_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
