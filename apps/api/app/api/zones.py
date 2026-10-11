import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform
from shapely.strtree import STRtree
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import Ward, WardFeature, Assessment
from app.services.spatial_datasets import get_dataset_collection

router = APIRouter(prefix="/zones", tags=["zones"])

PROJECT_ROOT = Path(__file__).resolve().parents[4]
PROCESSED_WARDS_PATH = PROJECT_ROOT / "data" / "processed" / "chennai" / "gcc-divisions-2022.geojson"
PROCESSED_ZONES_PATH = PROJECT_ROOT / "data" / "processed" / "chennai" / "gcc-zones-2022.geojson"
FIXTURE_WARDS_PATH = PROJECT_ROOT / "data" / "fixtures" / "wards.geojson"


def load_ward_collection() -> dict:
    """Load authoritative processed divisions, or explicitly marked fixtures."""
    if PROCESSED_WARDS_PATH.is_file():
        with PROCESSED_WARDS_PATH.open("r", encoding="utf-8") as source:
            collection = json.load(source)
        zone_collection = None
        if PROCESSED_ZONES_PATH.is_file():
            with PROCESSED_ZONES_PATH.open("r", encoding="utf-8") as source:
                zone_collection = json.load(source)
        collection["zone_features"] = zone_collection.get("features", []) if zone_collection else []
        collection["dataset_metadata"] = {
            "status": "SOURCE_VERIFIED_BOUNDARY",
            "source_id": "gcc-divisions-2022",
            "zone_source_id": "gcc-zones-2022" if zone_collection else None,
            "division_count": len(collection.get("features", [])),
            "zone_count": len(collection["zone_features"]),
            "risk_assessment_status": "CALCULATED",
            "storage": "PostgreSQL with PostGIS geometry support",
        }
        return collection

    if FIXTURE_WARDS_PATH.is_file():
        with FIXTURE_WARDS_PATH.open("r", encoding="utf-8") as source:
            collection = json.load(source)
        collection["dataset_metadata"] = {
            "status": "CALCULATED",
            "source_id": "fixture-wards",
            "division_count": len(collection.get("features", [])),
            "zone_count": 0,
        }
        return collection

    return {"type": "FeatureCollection", "features": [], "dataset_metadata": {}}


@router.get("")
def get_zones(db: Session = Depends(get_db)):
    """Retrieve GCC divisions with verified geometries, demographics, and computed risk."""
    collection = get_dataset_collection(db, "gcc-divisions-2022")
    if collection is None:
        collection = load_ward_collection()
        if not collection.get("features"):
            return collection
    else:
        zone_collection = get_dataset_collection(db, "gcc-zones-2022")
        collection["zone_features"] = zone_collection.get("features", []) if zone_collection else []
        collection["dataset_metadata"].update({
            "status": "SOURCE_VERIFIED_BOUNDARY",
            "source_id": "gcc-divisions-2022",
            "zone_source_id": "gcc-zones-2022" if zone_collection else None,
            "division_count": len(collection["features"]),
            "zone_count": len(collection["zone_features"]),
            "risk_assessment_status": "CALCULATED",
            "storage": "PostgreSQL with PostGIS geometry support",
        })

    flood_collection = get_dataset_collection(db, "chennai-2015-nrsc-inundation")
    rainfall_collection = get_dataset_collection(db, "tnsmart-daily-rainfall-2026-10-11")
    if flood_collection is None and PROCESSED_WARDS_PATH.is_file():
        flood_path = PROJECT_ROOT / "data" / "processed" / "chennai" / "flood-inundation-2015-gcc.geojson"
        if flood_path.is_file():
            flood_collection = json.loads(flood_path.read_text(encoding="utf-8"))
    if rainfall_collection is None:
        rainfall_path = PROJECT_ROOT / "data" / "processed" / "chennai" / "tnsmart-rainfall-2026-10-11.geojson"
        if rainfall_path.is_file():
            rainfall_collection = json.loads(rainfall_path.read_text(encoding="utf-8"))

    flood_geometries = [shape(feature["geometry"]) for feature in (flood_collection or {}).get("features", []) if feature.get("geometry")]
    flood_tree = STRtree(flood_geometries) if flood_geometries else None
    station_features = [feature for feature in (rainfall_collection or {}).get("features", []) if feature.get("geometry")]
    station_geometries = [shape(feature["geometry"]) for feature in station_features]
    station_tree = STRtree(station_geometries) if station_geometries else None
    to_projected = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True).transform

    # Query database for enriched ward records and features
    db_wards = {w.id: w for w in db.query(Ward).all()}
    db_features = {f.ward_id: f for f in db.query(WardFeature).all()}
    latest_assessments = {}
    for a in db.query(Assessment).order_by(Assessment.assessed_at.desc()).all():
        if a.ward_id not in latest_assessments:
            latest_assessments[a.ward_id] = a

    for feature in collection.get("features", []):
        geometry_json = feature.get("geometry")
        if not geometry_json:
            continue
        ward_geometry = shape(geometry_json)
        properties = feature.setdefault("properties", {})
        wid = properties.get("ward_id")

        properties["area_sq_km"] = round(transform(to_projected, ward_geometry).area / 1_000_000, 3)
        properties["historical_flood_feature_count"] = (
            len(flood_tree.query(ward_geometry, predicate="intersects")) if flood_tree is not None else 0
        )
        station_indexes = station_tree.query(ward_geometry) if station_tree is not None else []
        properties["rainfall_station_count"] = sum(
            1 for index in station_indexes if ward_geometry.covers(station_geometries[int(index)])
        )

        # Attach demographic and hydrological terrain attributes from PostgreSQL
        w_rec = db_wards.get(wid)
        f_rec = db_features.get(wid)
        a_rec = latest_assessments.get(wid)

        if w_rec:
            properties["population"] = w_rec.population
            if not properties.get("name"):
                properties["name"] = w_rec.name
            if not properties.get("zone"):
                properties["zone"] = w_rec.zone

        if f_rec:
            properties["elevation_mean"] = f_rec.elevation_mean
            properties["elevation_p90"] = f_rec.elevation_p90
            properties["slope_mean"] = f_rec.slope_mean
            properties["hand_mean"] = f_rec.hand_mean
            properties["imperviousness_mean"] = f_rec.imperviousness_mean
            properties["susceptibility_mean"] = f_rec.susceptibility_mean
            properties["e_score"] = f_rec.e_score
            properties["v_score"] = f_rec.v_score
            properties["shelter_count"] = f_rec.shelter_count
            properties["road_km"] = f_rec.road_km
            properties["crit_facility_count"] = f_rec.crit_facility_count

        if a_rec:
            properties["risk_score"] = a_rec.risk_score
            properties["risk_level"] = a_rec.risk_level
            properties["hazard"] = a_rec.hazard
            properties["hazard_band"] = a_rec.hazard_band
            properties["exposure"] = a_rec.exposure
            properties["vulnerability"] = a_rec.vulnerability
            properties["impact"] = a_rec.impact
            properties["confidence"] = a_rec.confidence
            properties["assessment_id"] = str(a_rec.id)

        properties["summary_data_classification"] = "DERIVED_FROM_POSTGRESQL_ANALYSIS"

    return collection


@router.get("/{ward_id}")
def get_zone_by_id(ward_id: str, db: Session = Depends(get_db)):
    """Retrieve a single ward GeoJSON Feature with enriched attributes."""
    data = get_zones(db)
    for feat in data.get("features", []):
        if feat.get("properties", {}).get("ward_id") == ward_id:
            return feat
    raise HTTPException(status_code=404, detail=f"Ward {ward_id} not found")
