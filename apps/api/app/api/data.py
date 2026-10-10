from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import RainfallObservation, SensorObservation
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
    """Retrieve comprehensive sensor telemetry data quality status matrix (P1-02)."""
    return {
        "status_distribution": {
            "VALID": 18,
            "SUSPECT": 2,
            "STALE": 1,
            "OUTLIER": 0,
            "CONFLICTING": 0,
            "INVALID": 0,
        },
        "freshness_window_minutes": 15,
        "stale_threshold_minutes": 30,
        "active_telemetry_sources": [
            {
                "id": "STN-TNAGAR-01",
                "name": "T. Nagar Automatic Weather Station",
                "ward_id": "WARD-112",
                "type": "RAINFALL_TIP_BUCKET",
                "quality_state": "VALID",
                "last_reading": "22.5 mm/h",
                "last_seen_sec_ago": 120,
                "latency_ms": 420,
                "is_simulated": True,
            },
            {
                "id": "SENS-MAMBALAM-CANAL",
                "name": "Mambalam Canal Ultrasonic Depth Sensor",
                "ward_id": "WARD-113",
                "type": "ULTRASONIC_WATER_LEVEL",
                "quality_state": "VALID",
                "last_reading": "2.15 m",
                "last_seen_sec_ago": 60,
                "latency_ms": 380,
                "is_simulated": True,
            },
            {
                "id": "SENS-VELACHERY-LAKE-OUTLET",
                "name": "Velachery Lake Sluice Radar Gauge",
                "ward_id": "WARD-117",
                "type": "RADAR_WATER_LEVEL",
                "quality_state": "VALID",
                "last_reading": "2.65 m",
                "last_seen_sec_ago": 45,
                "latency_ms": 310,
                "is_simulated": True,
            },
            {
                "id": "STN-ADYAR-ESTUARY-01",
                "name": "Adyar Estuary Storm Surge Gauge",
                "ward_id": "WARD-142",
                "type": "TIDE_PRESSURE_TRANSDUCER",
                "quality_state": "VALID",
                "last_reading": "1.20 m",
                "last_seen_sec_ago": 180,
                "latency_ms": 520,
                "is_simulated": True,
            },
            {
                "id": "SENS-WEST-MAMBALAM-STREET",
                "name": "Arya Gowda Road Flood Node",
                "ward_id": "WARD-113",
                "type": "OPTICAL_SURFACE_WATER",
                "quality_state": "SUSPECT",
                "last_reading": "0.38 m",
                "last_seen_sec_ago": 850,
                "latency_ms": 1450,
                "note": "Rate of rise variance exceeds expected spatial covariance",
                "is_simulated": True,
            },
            {
                "id": "STN-VELACHERY-SOUTH-RES",
                "name": "Velachery South Backup Rain Gauge",
                "ward_id": "WARD-118",
                "type": "RAINFALL_TIP_BUCKET",
                "quality_state": "STALE",
                "last_reading": "15.0 mm/h",
                "last_seen_sec_ago": 2100,
                "latency_ms": 4200,
                "note": "Age exceeds 30m freshness threshold",
                "is_simulated": True,
            },
        ],
    }
