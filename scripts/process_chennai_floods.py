"""Validate and clip the 2015 NRSC inundation KML to verified GCC divisions."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

import pyproj
import shapely
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, mapping, shape
from shapely.ops import transform, unary_union
from shapely.validation import explain_validity

from validate_chennai_sources import KML_NAMESPACE, PROJECT_ROOT, validate_manifest


SOURCE_ID = "chennai-2015-nrsc-inundation"
SOURCE_PATH = PROJECT_ROOT / "data/raw/chennai/flood-2015-nrsc.kml"
BOUNDARIES_PATH = PROJECT_ROOT / "data/processed/chennai/gcc-divisions-2022.geojson"
OUTPUT_PATH = PROJECT_ROOT / "data/processed/chennai/flood-inundation-2015-gcc.geojson"
AUDIT_PATH = PROJECT_ROOT / "data/processed/chennai/flood-inundation-2015-audit.json"
TO_METRIC = pyproj.Transformer.from_crs(4326, 32644, always_xy=True).transform


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _polygonal_parts(geometry: Any) -> list[Polygon]:
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, (MultiPolygon, GeometryCollection)):
        parts: list[Polygon] = []
        for component in geometry.geoms:
            parts.extend(_polygonal_parts(component))
        return parts
    return []


def _parse_coordinates(text: str | None) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for token in (text or "").split():
        values = token.split(",")
        if len(values) < 2:
            raise ValueError(f"Malformed KML coordinate: {token!r}")
        longitude, latitude = float(values[0]), float(values[1])
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            raise ValueError(f"Out-of-range KML coordinate: {token!r}")
        result.append((longitude, latitude))
    return result


def _polygon_from_kml(element: ET.Element) -> Polygon:
    outer = element.find("./kml:outerBoundaryIs/kml:LinearRing/kml:coordinates", KML_NAMESPACE)
    if outer is None:
        raise ValueError("Polygon has no outer ring")
    exterior = _parse_coordinates(outer.text)
    interiors = [
        _parse_coordinates(item.text)
        for item in element.findall("./kml:innerBoundaryIs/kml:LinearRing/kml:coordinates", KML_NAMESPACE)
    ]
    return Polygon(exterior, interiors)


def process(*, force: bool = False) -> dict[str, Any]:
    manifest = validate_manifest(PROJECT_ROOT / "data/manifest.yaml")
    if not manifest["integrity_ok"]:
        raise ValueError("Raw-source manifest verification failed: " + "; ".join(manifest["errors"]))
    if not BOUNDARIES_PATH.is_file():
        raise FileNotFoundError(f"Processed GCC divisions are missing: {BOUNDARIES_PATH}")
    if not force and (OUTPUT_PATH.exists() or AUDIT_PATH.exists()):
        raise FileExistsError("Processed output exists; pass --force to replace this pipeline's outputs")

    boundaries = json.loads(BOUNDARIES_PATH.read_text(encoding="utf-8"))
    division_geometries = [shape(feature["geometry"]) for feature in boundaries["features"]]
    if len(division_geometries) != 200 or any(not geometry.is_valid for geometry in division_geometries):
        raise ValueError("GCC boundary input must contain 200 valid processed division geometries")
    gcc_union = unary_union(division_geometries)

    root = ET.parse(SOURCE_PATH).getroot()
    if root.tag != f"{{{KML_NAMESPACE['kml']}}}kml":
        raise ValueError("Flood source is not KML 2.2")
    placemarks = root.findall(".//kml:Placemark", KML_NAMESPACE)
    output_features: list[dict[str, Any]] = []
    all_source_coordinates: list[tuple[float, float]] = []
    invalid_features: list[dict[str, str]] = []
    duplicate_geometry_counts: Counter[str] = Counter()
    source_area_m2 = overlap_area_m2 = 0.0
    partially_clipped_count = fully_outside_count = empty_intersection_count = 0

    for placemark in placemarks:
        data = {
            item.attrib["name"]: (item.text or "").strip()
            for item in placemark.findall(".//kml:SimpleData", KML_NAMESPACE)
            if item.attrib.get("name")
        }
        source_feature_id = data.get("id", "").strip()
        if not source_feature_id:
            raise ValueError("NRSC flood source includes an unidentifiable polygon placemark")

        polygons: list[Polygon] = []
        for polygon_element in placemark.findall(".//kml:Polygon", KML_NAMESPACE):
            polygon = _polygon_from_kml(polygon_element)
            if polygon.is_empty:
                raise ValueError(f"Empty source geometry for feature {source_feature_id}")
            if not polygon.is_valid:
                invalid_features.append(
                    {"id": source_feature_id, "reason": explain_validity(polygon)}
                )
                raise ValueError(f"Invalid source polygon {source_feature_id}; no repair was authorized")
            polygons.append(polygon)
            all_source_coordinates.extend(polygon.exterior.coords)
        if not polygons:
            raise ValueError(f"Source feature {source_feature_id} has no polygon geometry")

        source_geometry = unary_union(polygons)
        duplicate_geometry_counts[hashlib.sha256(shapely.normalize(source_geometry).wkb).hexdigest()] += 1
        projected_source = transform(TO_METRIC, source_geometry)
        source_area_m2 += projected_source.area
        clipped = source_geometry.intersection(gcc_union)
        if clipped.is_empty:
            fully_outside_count += 1
            empty_intersection_count += 1
            continue
        clipped_parts = _polygonal_parts(clipped)
        if not clipped_parts:
            empty_intersection_count += 1
            continue
        clipped_geometry = unary_union(clipped_parts)
        if clipped_geometry.is_empty or not clipped_geometry.is_valid:
            raise ValueError(f"Clipped geometry {source_feature_id} is empty or invalid")
        overlap_area_m2 += transform(TO_METRIC, clipped_geometry).area
        if not gcc_union.covers(source_geometry):
            partially_clipped_count += 1

        output_features.append(
            {
                "type": "Feature",
                "id": f"NRSC15-{source_feature_id}",
                "geometry": mapping(clipped_geometry),
                "properties": {
                    "source_id": SOURCE_ID,
                    "source_feature_id": source_feature_id,
                    "event_year": 2015,
                    "layer_type": "HISTORICAL_INUNDATION",
                    "source_pixelvalue": data.get("pixelvalue"),
                    "source_area_raw": data.get("area"),
                    "source_perimeter_raw": data.get("perimeter"),
                    "geometry_status": "VALIDATED_AND_CLIPPED",
                    "acquisition_timestamp": None,
                },
            }
        )

    longitudes, latitudes = zip(*all_source_coordinates)
    source_bounds = [min(longitudes), min(latitudes), max(longitudes), max(latitudes)]
    clipped_geometry_union = unary_union([shape(feature["geometry"]) for feature in output_features])
    output_bounds = list(clipped_geometry_union.bounds)
    source_coordinate_count = len(all_source_coordinates)
    feature_count = len(output_features)
    if len(placemarks) != 4001 or feature_count == 0:
        raise ValueError(f"Unexpected source/output feature counts: {len(placemarks)} / {feature_count}")

    metadata = {
        "layer_id": "chennai-historical-inundation-2015",
        "layer_name": "2015 Historical Flood / Inundation",
        "source_id": SOURCE_ID,
        "source_sha256": _sha256(SOURCE_PATH),
        "source_crs": "KML 2.2 longitude/latitude in WGS 84",
        "output_crs": "RFC 7946 longitude/latitude",
        "event_year": 2015,
        "feature_timestamp_available": False,
        "spatial_operation": "Intersect each source polygon with the union of the 200 processed GCC 2022 divisions.",
        "source_feature_count": len(placemarks),
        "output_feature_count": feature_count,
        "source_bounds": source_bounds,
        "output_bounds": output_bounds,
        "invalid_source_geometry_count": len(invalid_features),
        "duplicate_source_geometry_groups": sum(count > 1 for count in duplicate_geometry_counts.values()),
        "duplicate_source_geometry_extra_features": sum(count - 1 for count in duplicate_geometry_counts.values() if count > 1),
        "fully_outside_gcc_count": fully_outside_count,
        "partially_clipped_count": partially_clipped_count,
        "empty_intersection_count": empty_intersection_count,
        "projected_area_crs": "EPSG:32644",
        "source_geometry_area_m2_sum": round(source_area_m2, 3),
        "clipped_geometry_area_m2_sum": round(overlap_area_m2, 3),
        "raw_file_modified": False,
    }
    collection = {
        "type": "FeatureCollection",
        "name": metadata["layer_name"],
        "dataset_metadata": metadata,
        "features": output_features,
    }
    audit = {
        **metadata,
        "source_file": SOURCE_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "output_file": OUTPUT_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "coordinate_count": source_coordinate_count,
        "repair_count": 0,
        "clipping_geometry_source": "data/processed/chennai/gcc-divisions-2022.geojson",
        "clipping_geometry_count": len(division_geometries),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(collection, ensure_ascii=False) + "\n", encoding="utf-8")
    audit["output_sha256"] = _sha256(OUTPUT_PATH)
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Replace processed flood output")
    arguments = parser.parse_args()
    print(json.dumps(process(force=arguments.force), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
