"""Serve locally processed, source-attributed Chennai observation layers."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.spatial_datasets import get_dataset_collection


router = APIRouter(prefix="/layers", tags=["observed-layers"])
PROJECT_ROOT = Path(__file__).resolve().parents[4]
FLOOD_PATH = PROJECT_ROOT / "data/processed/chennai/flood-inundation-2015-gcc.geojson"
FLOOD_AUDIT_PATH = PROJECT_ROOT / "data/processed/chennai/flood-inundation-2015-audit.json"
RAINFALL_PATH = PROJECT_ROOT / "data/processed/chennai/imd-rainfall-grid-025-2015-chennai.csv"
RAINFALL_AUDIT_PATH = PROJECT_ROOT / "data/processed/chennai/imd-rainfall-grid-025-2015-audit.json"
TNSMART_RAINFALL_PATH = PROJECT_ROOT / "data/processed/chennai/tnsmart-rainfall-2026-10-11.geojson"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/historical-floods/2015")
def get_historical_flood_layer(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return the 2015 NRSC inundation polygons clipped to GCC divisions."""
    stored_collection = get_dataset_collection(db, "chennai-2015-nrsc-inundation")
    if stored_collection is not None:
        stored_collection["dataset_metadata"].update({
            "source_id": "chennai-2015-nrsc-inundation",
            "status": "HISTORICAL_OBSERVATION",
            "risk_input_eligible": False,
            "limitation": "The source has no per-feature acquisition date; the dataset is presented only as the 2015 historical layer.",
        })
        return stored_collection

    collection = _read_json(FLOOD_PATH)
    audit = _read_json(FLOOD_AUDIT_PATH)
    if collection is None or audit is None:
        return {
            "type": "FeatureCollection",
            "features": [],
            "dataset_metadata": {"status": "UNAVAILABLE", "source_id": "chennai-2015-nrsc-inundation"},
        }
    collection["dataset_metadata"] = {
        "status": "HISTORICAL_OBSERVATION",
        "source_id": audit["source_id"],
        "source_sha256": audit["source_sha256"],
        "source_crs": audit["source_crs"],
        "output_crs": audit["output_crs"],
        "feature_timestamp_available": audit["feature_timestamp_available"],
        "source_feature_count": audit["source_feature_count"],
        "output_feature_count": audit["output_feature_count"],
        "fully_outside_gcc_count": audit["fully_outside_gcc_count"],
        "partially_clipped_count": audit["partially_clipped_count"],
        "repair_count": audit["repair_count"],
        "limitation": "The source has no per-feature acquisition date; the dataset is presented only as the 2015 historical layer.",
    }
    return collection


@router.get("/rainfall/2015")
def get_historical_rainfall_layer() -> dict[str, Any]:
    """Return valid IMD 0.25-degree 2015 values; keep missing values out of map marks."""
    audit = _read_json(RAINFALL_AUDIT_PATH)
    features: list[dict[str, Any]] = []
    if audit is not None and RAINFALL_PATH.is_file():
        with RAINFALL_PATH.open("r", encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source):
                if row["rainfall_mm"] == "":
                    continue
                features.append(
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [float(row["longitude"]), float(row["latitude"])]},
                        "properties": {
                            "grid_id": row["grid_id"],
                            "date": row["date"],
                            "rainfall_mm": float(row["rainfall_mm"]),
                            "source_id": row["source_id"],
                            "source_status": row["source_status"],
                        },
                    }
                )
    metadata = {
        "status": "UNAVAILABLE" if audit is None else ("OBSERVATIONS_AVAILABLE" if features else "NO_VALID_OBSERVATIONS"),
        "source_id": "imd-daily-gridded-rainfall-025-2015",
        "source_sha256": audit.get("source_sha256") if audit else None,
        "units": "mm per IMD daily accumulation",
        "temporal_coverage": [audit.get("date_min"), audit.get("date_max")] if audit else None,
        "candidate_grid_nodes": audit.get("grid_nodes_inside_gcc", []) if audit else [],
        "valid_observation_count": len(features),
        "missing_observation_count": audit.get("missing_records") if audit else None,
        "source_crs_note": audit.get("source_crs_note") if audit else "",
        "limitation": "The only grid node selected by coordinate overlay is missing for the full year; the NetCDF does not declare its geodetic datum. No rainfall values are shown or used for risk.",
    }
    return {"type": "FeatureCollection", "features": features, "dataset_metadata": metadata}


@router.get("/rainfall/tnsmart/2026-10-11")
def get_tnsmart_rainfall_layer(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return the locally processed TN-SMART daily station snapshot."""
    stored_collection = get_dataset_collection(db, "tnsmart-daily-rainfall-2026-10-11")
    if stored_collection is not None:
        stored_collection["dataset_metadata"].update({
            "source_id": "tnsmart-daily-rainfall-2026-10-11",
            "status": "DATED_OBSERVATION_SNAPSHOT",
            "risk_input_eligible": False,
        })
        return stored_collection

    collection = _read_json(TNSMART_RAINFALL_PATH)
    if collection is None:
        return {
            "type": "FeatureCollection",
            "features": [],
            "dataset_metadata": {
                "status": "UNAVAILABLE",
                "source_id": "tnsmart-daily-rainfall-2026-10-11",
                "station_count_chennai": 0,
                "station_count_inside_gcc": 0,
                "risk_input_eligible": False,
                "limitation": "Processed source data are unavailable.",
            },
        }
    return collection
