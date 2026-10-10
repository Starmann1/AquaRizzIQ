from datetime import datetime, timezone, timedelta
import pytest
from app.db.enums import DataQualityState
from app.services.data_quality import DataQualityEvaluator
from app.schemas.data import RainfallObservationCreate, SensorObservationCreate
from app.services.ingestion import IngestionService


def test_data_quality_evaluator_bounds():
    qc = DataQualityEvaluator()
    now = datetime.now(timezone.utc)

    # Valid reading
    state, msg = qc.evaluate_water_level(1.2, now, as_of_time=now)
    assert state == DataQualityState.VALID

    # Physical outlier (negative)
    state, msg = qc.evaluate_water_level(-0.5, now, as_of_time=now)
    assert state == DataQualityState.OUTLIER

    # Physical outlier (above 5m limit)
    state, msg = qc.evaluate_water_level(6.2, now, as_of_time=now)
    assert state == DataQualityState.OUTLIER

    # Stale reading (> 30 min)
    stale_time = now - timedelta(minutes=45)
    state, msg = qc.evaluate_water_level(1.0, stale_time, as_of_time=now)
    assert state == DataQualityState.STALE


def test_data_quality_rate_of_rise():
    qc = DataQualityEvaluator(max_rate_of_rise_m_min=0.20)
    now = datetime.now(timezone.utc)
    prev_time = now - timedelta(minutes=2)

    # Rose 0.8m in 2 minutes = 0.40 m/min > 0.20 limit -> SUSPECT
    state, msg = qc.evaluate_water_level(
        current_level_m=1.8,
        observed_at=now,
        as_of_time=now,
        previous_level_m=1.0,
        previous_observed_at=prev_time,
    )
    assert state == DataQualityState.SUSPECT


@pytest.mark.asyncio
async def test_ingestion_service_db(db_session):
    service = IngestionService(db_session)
    now = datetime.now(timezone.utc)

    records = [
        RainfallObservationCreate(
            station_id="STN-01",
            observed_at=now,
            rainfall_mm=25.0,
            accumulation_1h=25.0,
            is_simulated=True,
        ),
        RainfallObservationCreate(
            station_id="STN-01",
            observed_at=now,  # Duplicate
            rainfall_mm=25.0,
            accumulation_1h=25.0,
            is_simulated=True,
        ),
    ]

    res = service.ingest_rainfall_batch(records)
    assert res.accepted == 1
    assert res.duplicates == 1
    assert res.rejected == 0
