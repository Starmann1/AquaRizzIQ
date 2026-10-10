from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from app.db.enums import DataQualityState

class RainfallObservationCreate(BaseModel):
    station_id: str
    observed_at: datetime
    rainfall_mm: float
    accumulation_1h: Optional[float] = None
    accumulation_3h: Optional[float] = None
    quality: DataQualityState = DataQualityState.VALID
    is_simulated: bool = False
    source_id: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class SensorObservationCreate(BaseModel):
    sensor_id: str
    observed_at: datetime
    water_level_m: float
    quality: DataQualityState = DataQualityState.VALID
    is_simulated: bool = False
    source_id: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class BatchIngestionResponse(BaseModel):
    accepted: int
    rejected: int = 0
    duplicates: int = 0
    run_id: Optional[str] = None
