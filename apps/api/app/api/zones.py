import json
import os
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/zones", tags=["zones"])

FIXTURES_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "fixtures", "wards.geojson")
)


def _load_wards_geojson():
    if os.path.exists(FIXTURES_PATH):
        with open(FIXTURES_PATH, "r") as f:
            return json.load(f)
    return {"type": "FeatureCollection", "features": []}


@router.get("")
def get_zones():
    """Retrieve GeoJSON FeatureCollection of all monitored GCC ward boundaries."""
    return _load_wards_geojson()


@router.get("/{ward_id}")
def get_zone_by_id(ward_id: str):
    """Retrieve a single ward GeoJSON Feature."""
    data = _load_wards_geojson()
    for feat in data.get("features", []):
        if feat.get("properties", {}).get("ward_id") == ward_id:
            return feat
    raise HTTPException(status_code=404, detail=f"Ward {ward_id} not found")
