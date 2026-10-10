from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Generic, TypeVar, List, Optional

def utcnow():
    return datetime.now(timezone.utc)

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int

class ErrorDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: Optional[str] = None
    instance: Optional[str] = None

class TimestampMixin(BaseModel):
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

class GeoJSONPoint(BaseModel):
    type: str = "Point"
    coordinates: List[float]

class GeoJSONPolygon(BaseModel):
    type: str = "Polygon"
    coordinates: List[List[List[float]]]
