"""Load and query the source-backed GeoJSON datasets used by the local demo."""
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.db.models import SpatialDataset, SpatialDatasetFeature


PROJECT_ROOT = Path(__file__).resolve().parents[4]
CHENNAI_DATA = PROJECT_ROOT / "data" / "processed" / "chennai"


@dataclass(frozen=True)
class DatasetFile:
    dataset_id: str
    name: str
    path: Path
    metadata_path: Path | None = None
    metadata: dict[str, Any] | None = None


DEMO_DATASETS = (
    DatasetFile(
        "gcc-divisions-2022", "GCC divisions (2022)",
        CHENNAI_DATA / "gcc-divisions-2022.geojson",
        metadata={
            "status": "SOURCE_VERIFIED_BOUNDARY", "source_crs": "EPSG:4326", "output_crs": "EPSG:4326",
            "risk_input_eligible": False,
        },
    ),
    DatasetFile(
        "gcc-zones-2022", "GCC zones (2022)",
        CHENNAI_DATA / "gcc-zones-2022.geojson",
        metadata={
            "status": "SOURCE_VERIFIED_BOUNDARY", "source_crs": "EPSG:4326", "output_crs": "EPSG:4326",
            "risk_input_eligible": False,
        },
    ),
    DatasetFile(
        "chennai-2015-nrsc-inundation", "NRSC Chennai inundation (2015)",
        CHENNAI_DATA / "flood-inundation-2015-gcc.geojson",
        CHENNAI_DATA / "flood-inundation-2015-audit.json",
        {"status": "HISTORICAL_OBSERVATION", "risk_input_eligible": False},
    ),
    DatasetFile(
        "tnsmart-daily-rainfall-2026-10-11", "TN-SMART rainfall snapshot (2026-10-11)",
        CHENNAI_DATA / "tnsmart-rainfall-2026-10-11.geojson",
        CHENNAI_DATA / "tnsmart-rainfall-2026-10-11-audit.json",
        {"status": "DATED_OBSERVATION_SNAPSHOT", "risk_input_eligible": False},
    ),
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_fingerprint(source: DatasetFile) -> str:
    digest = hashlib.sha256()
    for path in (source.path, source.metadata_path):
        if path is None or not path.is_file():
            continue
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def load_bundled_datasets(db: Session) -> dict[str, int]:
    """Synchronize processed files into SQL tables as one all-or-nothing unit.

    Missing optional files are skipped. An invalid present file raises and
    rolls back the transaction rather than leaving a partially refreshed store.
    """
    loaded: dict[str, int] = {}
    try:
        for source in DEMO_DATASETS:
            if not source.path.is_file():
                continue

            source_fingerprint = _source_fingerprint(source)
            dataset = db.get(SpatialDataset, source.dataset_id)
            if (
                dataset is not None
                and dataset.metadata_json.get("file_sha256") == source_fingerprint
                and db.scalar(select(SpatialDatasetFeature.feature_id).where(
                    SpatialDatasetFeature.dataset_id == source.dataset_id
                ).limit(1)) is not None
            ):
                loaded[source.dataset_id] = dataset.feature_count
                continue

            collection = _load_json(source.path)
            features = collection.get("features", [])
            metadata = dict(source.metadata or {})
            metadata["file_sha256"] = source_fingerprint
            if source.metadata_path and source.metadata_path.is_file():
                metadata.update(_load_json(source.metadata_path))
            if isinstance(collection.get("dataset_metadata"), dict):
                metadata.update(collection["dataset_metadata"])

            db.execute(delete(SpatialDatasetFeature).where(
                SpatialDatasetFeature.dataset_id == source.dataset_id
            ))
            if dataset is None:
                dataset = SpatialDataset(id=source.dataset_id, name=source.name, metadata_json=metadata)
                db.add(dataset)
            else:
                dataset.name = source.name
                dataset.metadata_json = metadata
                dataset.loaded_at = datetime.now(timezone.utc)
            db.flush()

            rows = []
            for index, feature in enumerate(features):
                geometry = feature.get("geometry")
                if not isinstance(geometry, dict):
                    continue
                identifier = feature.get("id")
                if identifier is None:
                    identifier = feature.get("properties", {}).get("id", index)
                rows.append({
                    "dataset_id": source.dataset_id,
                    "feature_id": str(identifier),
                    "geometry_geojson": geometry,
                    "properties": feature.get("properties") or {},
                })
            if rows:
                db.bulk_insert_mappings(SpatialDatasetFeature, rows)
            dataset.feature_count = len(rows)
            loaded[source.dataset_id] = len(rows)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return loaded


def get_dataset_collection(db: Session, dataset_id: str) -> dict[str, Any] | None:
    """Return a GeoJSON FeatureCollection from the configured SQL database."""
    dataset = db.get(SpatialDataset, dataset_id)
    if dataset is None:
        return None

    rows = db.scalars(
        select(SpatialDatasetFeature)
        .where(SpatialDatasetFeature.dataset_id == dataset_id)
        .order_by(SpatialDatasetFeature.feature_id)
    ).all()
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": row.feature_id,
                "geometry": row.geometry_geojson,
                "properties": row.properties,
            }
            for row in rows
        ],
        "dataset_metadata": {**(dataset.metadata_json or {}), "feature_count": dataset.feature_count},
    }
