"""AquaRizz Ingestion Service.

Handles batch validation, deduplication, quality state assignment, and database persistence.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.db.models import RainfallObservation, SensorObservation
from app.db.enums import DataQualityState
from app.schemas.data import RainfallObservationCreate, SensorObservationCreate, BatchIngestionResponse
from app.services.data_quality import DataQualityEvaluator


class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.qc = DataQualityEvaluator()

    def ingest_rainfall_batch(
        self, records: List[RainfallObservationCreate]
    ) -> BatchIngestionResponse:
        accepted = 0
        rejected = 0
        duplicates = 0
        now = datetime.now(timezone.utc)

        seen_keys: set[Tuple[str, datetime]] = set()

        for rec in records:
            # Evaluate QC
            qc_state, _ = self.qc.evaluate_rainfall(rec.rainfall_mm, rec.observed_at, now)
            if qc_state == DataQualityState.INVALID:
                rejected += 1
                continue

            # Idempotency check: in-batch and in-db
            key = (rec.station_id, rec.observed_at)
            if key in seen_keys:
                duplicates += 1
                continue
            seen_keys.add(key)

            existing = (
                self.db.query(RainfallObservation)
                .filter(
                    RainfallObservation.station_id == rec.station_id,
                    RainfallObservation.observed_at == rec.observed_at,
                )
                .first()
            )
            if existing:
                duplicates += 1
                continue

            obs = RainfallObservation(
                id=uuid.uuid4(),
                station_id=rec.station_id,
                observed_at=rec.observed_at,
                rainfall_mm=rec.rainfall_mm,
                accumulation_1h=rec.accumulation_1h,
                accumulation_3h=rec.accumulation_3h,
                quality=qc_state.value,
                is_simulated=rec.is_simulated,
                source_id=rec.source_id,
                ingested_at=now,
            )
            self.db.add(obs)
            accepted += 1

        self.db.commit()
        return BatchIngestionResponse(
            accepted=accepted,
            rejected=rejected,
            duplicates=duplicates,
            run_id=str(uuid.uuid4()),
        )

    def ingest_water_level_batch(
        self, records: List[SensorObservationCreate]
    ) -> BatchIngestionResponse:
        accepted = 0
        rejected = 0
        duplicates = 0
        seen_keys: set[Tuple[str, datetime]] = set()
        now = datetime.now(timezone.utc)

        for rec in records:
            qc_state, _ = self.qc.evaluate_water_level(
                rec.water_level_m, rec.observed_at, now
            )
            if qc_state == DataQualityState.INVALID:
                rejected += 1
                continue

            key = (rec.sensor_id, rec.observed_at)
            if key in seen_keys:
                duplicates += 1
                continue
            seen_keys.add(key)

            existing = (
                self.db.query(SensorObservation)
                .filter(
                    SensorObservation.sensor_id == rec.sensor_id,
                    SensorObservation.observed_at == rec.observed_at,
                )
                .first()
            )
            if existing:
                duplicates += 1
                continue

            obs = SensorObservation(
                id=uuid.uuid4(),
                sensor_id=rec.sensor_id,
                observed_at=rec.observed_at,
                water_level_m=rec.water_level_m,
                quality=qc_state.value,
                is_simulated=rec.is_simulated,
                source_id=rec.source_id,
                ingested_at=now,
            )
            self.db.add(obs)
            accepted += 1

        self.db.commit()
        return BatchIngestionResponse(
            accepted=accepted,
            rejected=rejected,
            duplicates=duplicates,
            run_id=str(uuid.uuid4()),
        )
