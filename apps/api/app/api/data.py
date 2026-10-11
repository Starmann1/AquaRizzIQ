from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import RainfallObservation, Sensor, SensorObservation
from app.db.enums import DataQualityState
from app.services.quality_policy import decide_quality_use
from app.schemas.data import (
    RainfallObservationCreate,
    SensorObservationCreate,
    BatchIngestionResponse,
)
from app.services.ingestion import IngestionService

router = APIRouter(prefix="/data", tags=["data"])


@router.post("/rainfall", status_code=202, response_model=BatchIngestionResponse)
def ingest_rainfall(
    data: List[RainfallObservationCreate],
    db: Session = Depends(get_db),
):
    service = IngestionService(db)
    return service.ingest_rainfall_batch(data)


@router.post("/water-level", status_code=202, response_model=BatchIngestionResponse)
def ingest_water_level(
    data: List[SensorObservationCreate],
    db: Session = Depends(get_db),
):
    service = IngestionService(db)
    return service.ingest_water_level_batch(data)


@router.get("/rainfall")
def get_rainfall(
    station_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(RainfallObservation).order_by(RainfallObservation.observed_at.desc())
    if station_id:
        query = query.filter(RainfallObservation.station_id == station_id)
    records = query.limit(limit).all()
    return [
        {
            "id": str(r.id),
            "station_id": r.station_id,
            "observed_at": r.observed_at.isoformat(),
            "rainfall_mm": r.rainfall_mm,
            "accumulation_1h": r.accumulation_1h,
            "quality": r.quality,
            "is_simulated": r.is_simulated,
        }
        for r in records
    ]


@router.get("/water-level")
def get_water_level(
    sensor_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(SensorObservation).order_by(SensorObservation.observed_at.desc())
    if sensor_id:
        query = query.filter(SensorObservation.sensor_id == sensor_id)
    records = query.limit(limit).all()
    return [
        {
            "id": str(r.id),
            "sensor_id": r.sensor_id,
            "observed_at": r.observed_at.isoformat(),
            "water_level_m": r.water_level_m,
            "quality": r.quality,
            "is_simulated": r.is_simulated,
        }
        for r in records
    ]


@router.get("/quality")
def get_data_quality_summary(db: Session = Depends(get_db)):
    """Summarize quality from latest stored observations; never synthesize telemetry."""
    sensors = db.query(Sensor).filter(Sensor.is_active.is_(True)).order_by(Sensor.id).all()
    latest_by_sensor = (
        db.query(
            SensorObservation.sensor_id.label("sensor_id"),
            func.max(SensorObservation.observed_at).label("observed_at"),
        )
        .group_by(SensorObservation.sensor_id)
        .subquery()
    )
    latest_observations = (
        db.query(SensorObservation)
        .join(
            latest_by_sensor,
            and_(
                SensorObservation.sensor_id == latest_by_sensor.c.sensor_id,
                SensorObservation.observed_at == latest_by_sensor.c.observed_at,
            ),
        )
        .all()
    )
    observations_by_sensor = {observation.sensor_id: observation for observation in latest_observations}
    as_of = datetime.now(timezone.utc)
    stale_after_seconds = 30 * 60
    freshness_window_seconds = 15 * 60
    states = ("VALID", "SUSPECT", "STALE", "MISSING", "CONFLICTING", "OUTLIER", "INVALID")
    distribution = {state: 0 for state in states}
    sources = []
    quality_policy = [
        {
            "state": state.value,
            "critical_input": decide_quality_use(state, critical_input=True).disposition,
            "non_critical_input": decide_quality_use(state, critical_input=False).disposition,
        }
        for state in DataQualityState
    ]

    for sensor in sensors:
        observation = observations_by_sensor.get(sensor.id)
        if observation is None:
            state = "MISSING"
            age_seconds = None
            observed_at = None
            reading = None
            is_simulated = bool(sensor.is_simulated)
            note = "No stored observation for this registered sensor."
            freshness = "MISSING"
        else:
            observed_at = observation.observed_at
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=timezone.utc)
            age_seconds = max(0, int((as_of - observed_at).total_seconds()))
            if (observed_at - as_of).total_seconds() > 0:
                state = "INVALID"
            elif age_seconds > stale_after_seconds:
                state = "STALE"
            else:
                state = observation.quality
            freshness = (
                "FRESH" if age_seconds <= freshness_window_seconds
                else "AGING" if age_seconds <= stale_after_seconds
                else "STALE"
            )
            reading = observation.water_level_m
            is_simulated = bool(sensor.is_simulated or observation.is_simulated)
            note = None

        distribution[state] += 1
        sources.append(
            {
                "id": sensor.id,
                "name": sensor.name,
                "ward_id": sensor.ward_id,
                "type": sensor.sensor_type,
                "quality_state": state,
                "freshness_state": freshness,
                "last_reading": f"{reading:.3f} m" if reading is not None else None,
                "observed_at": observed_at.isoformat() if observed_at else None,
                "age_seconds": age_seconds,
                "latency_ms": None,
                "note": note,
                "is_simulated": is_simulated,
            }
        )

    rainfall_total = db.query(func.count(RainfallObservation.id)).scalar() or 0
    rainfall_simulated = (
        db.query(func.count(RainfallObservation.id))
        .filter(RainfallObservation.is_simulated.is_(True))
        .scalar()
        or 0
    )
    rainfall_observed = rainfall_total - rainfall_simulated
    sensor_observation_count = len(latest_observations)
    sensor_simulation_flags = {sensor.id: sensor.is_simulated for sensor in sensors}
    simulated_sensor_observation_count = sum(
        observation.is_simulated or sensor_simulation_flags.get(observation.sensor_id, False)
        for observation in latest_observations
    )
    unmarked_sensor_observation_count = sensor_observation_count - simulated_sensor_observation_count
    simulated_observation_count = simulated_sensor_observation_count + rainfall_simulated
    unmarked_observation_count = unmarked_sensor_observation_count + rainfall_observed
    if unmarked_observation_count and simulated_observation_count:
        data_status = "MIXED"
    elif unmarked_observation_count:
        data_status = "STORED_UNVERIFIED"
    elif simulated_observation_count:
        data_status = "SIMULATED_ONLY"
    else:
        data_status = "NO_DATA"
    return {
        "as_of": as_of.isoformat(),
        "data_status": data_status,
        "verified_live_source_available": False,
        "status_distribution": distribution,
        "quality_use_policy": quality_policy,
        "freshness_window_minutes": freshness_window_seconds // 60,
        "stale_threshold_minutes": stale_after_seconds // 60,
        "active_sensor_count": len(sensors),
        "simulated_sensor_count": sum(source["is_simulated"] for source in sources),
        "sensor_observation_count": sensor_observation_count,
        "simulated_sensor_observation_count": simulated_sensor_observation_count,
        "unmarked_sensor_observation_count": unmarked_sensor_observation_count,
        "rainfall_observation_count": rainfall_total,
        "simulated_rainfall_observation_count": rainfall_simulated,
        "unmarked_rainfall_observation_count": rainfall_observed,
        "active_telemetry_sources": sources,
    }
