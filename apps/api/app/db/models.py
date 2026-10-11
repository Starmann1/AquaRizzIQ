from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import Float, Integer, String, Boolean, DateTime, JSON, ForeignKey, CheckConstraint, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry
import uuid
from app.database import Base
from app.db.enums import (
    RiskLevel, DataQualityState, AssessmentStatus, UserRole,
    ModelReadiness, ValidationDomain, PolicyStatus, SensorStatus
)

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    
    __table_args__ = (
        CheckConstraint(f"role IN ({','.join([repr(e.value) for e in UserRole])})", name='check_user_role'),
    )

class Ward(Base):
    __tablename__ = 'wards'
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    zone: Mapped[str] = mapped_column(String)
    geom: Mapped[Any] = mapped_column(Geometry('MULTIPOLYGON', srid=32644))
    area_sq_km: Mapped[float] = mapped_column(Float)
    population: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class GridCell(Base):
    __tablename__ = 'grid_cells'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ward_id: Mapped[str] = mapped_column(ForeignKey('wards.id'), index=True)
    ix: Mapped[int] = mapped_column(Integer)
    iy: Mapped[int] = mapped_column(Integer)
    geom: Mapped[Any] = mapped_column(Geometry('POLYGON', srid=32644))
    
    __table_args__ = (
        UniqueConstraint('ix', 'iy', name='uix_grid_cell_ix_iy'),
    )

class GridFeature(Base):
    __tablename__ = 'grid_features'
    
    grid_cell_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('grid_cells.id'), primary_key=True)
    elevation: Mapped[float] = mapped_column(Float)
    slope: Mapped[float] = mapped_column(Float)
    hand: Mapped[float] = mapped_column(Float)
    twi: Mapped[float] = mapped_column(Float)
    drain_proximity: Mapped[float] = mapped_column(Float)
    drain_density: Mapped[float] = mapped_column(Float)
    imperviousness: Mapped[float] = mapped_column(Float)
    land_cover: Mapped[str] = mapped_column(String)
    hist_flood_freq: Mapped[float] = mapped_column(Float)
    susceptibility: Mapped[float] = mapped_column(Float)

class WardFeature(Base):
    __tablename__ = 'ward_features'
    
    ward_id: Mapped[str] = mapped_column(ForeignKey('wards.id'), primary_key=True)
    elevation_mean: Mapped[float] = mapped_column(Float)
    elevation_p90: Mapped[float] = mapped_column(Float)
    slope_mean: Mapped[float] = mapped_column(Float)
    hand_mean: Mapped[float] = mapped_column(Float)
    imperviousness_mean: Mapped[float] = mapped_column(Float)
    susceptibility_mean: Mapped[float] = mapped_column(Float)
    susceptibility_p90: Mapped[float] = mapped_column(Float)
    e_score: Mapped[float] = mapped_column(Float)
    v_score: Mapped[float] = mapped_column(Float)
    pop_density: Mapped[float] = mapped_column(Float)
    sensitive_pop_share: Mapped[float] = mapped_column(Float)
    shelter_count: Mapped[int] = mapped_column(Integer)
    shelter_gap: Mapped[float] = mapped_column(Float)
    road_km: Mapped[float] = mapped_column(Float)
    crit_facility_count: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class RainfallStation(Base):
    __tablename__ = 'rainfall_stations'
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    ward_id: Mapped[Optional[str]] = mapped_column(ForeignKey('wards.id'))
    geom: Mapped[Any] = mapped_column(Geometry('POINT', srid=32644))
    source: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class RainfallObservation(Base):
    __tablename__ = 'rainfall_observations'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    station_id: Mapped[str] = mapped_column(String, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rainfall_mm: Mapped[float] = mapped_column(Float)
    accumulation_1h: Mapped[Optional[float]] = mapped_column(Float)
    accumulation_3h: Mapped[Optional[float]] = mapped_column(Float)
    quality: Mapped[str] = mapped_column(String)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    source_id: Mapped[Optional[str]] = mapped_column(String)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    
    __table_args__ = (
        CheckConstraint(f"quality IN ({','.join([repr(e.value) for e in DataQualityState])})", name='check_rain_obs_quality'),
    )

class Sensor(Base):
    __tablename__ = 'sensors'
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    ward_id: Mapped[str] = mapped_column(ForeignKey('wards.id'))
    geom: Mapped[Any] = mapped_column(Geometry('POINT', srid=32644))
    sensor_type: Mapped[str] = mapped_column(String)
    depth_m: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)

class SensorObservation(Base):
    __tablename__ = 'sensor_observations'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sensor_id: Mapped[str] = mapped_column(String, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    water_level_m: Mapped[float] = mapped_column(Float)
    quality: Mapped[str] = mapped_column(String)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    source_id: Mapped[Optional[str]] = mapped_column(String)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    
    __table_args__ = (
        CheckConstraint(f"quality IN ({','.join([repr(e.value) for e in DataQualityState])})", name='check_sensor_obs_quality'),
    )

class ModelVersion(Base):
    __tablename__ = 'model_versions'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    model_type: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)
    validation_domain: Mapped[str] = mapped_column(String)
    readiness_status: Mapped[str] = mapped_column(String)
    metrics: Mapped[dict] = mapped_column(JSON)
    config_hash: Mapped[str] = mapped_column(String)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    
    __table_args__ = (
        CheckConstraint(f"validation_domain IN ({','.join([repr(e.value) for e in ValidationDomain])})", name='check_model_val_domain'),
        CheckConstraint(f"readiness_status IN ({','.join([repr(e.value) for e in ModelReadiness])})", name='check_model_readiness'),
    )

class ConfigVersion(Base):
    __tablename__ = 'config_versions'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    config_name: Mapped[str] = mapped_column(String)
    config_hash: Mapped[str] = mapped_column(String)
    config_data: Mapped[dict] = mapped_column(JSON)
    policy_status: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    
    __table_args__ = (
        CheckConstraint(f"policy_status IN ({','.join([repr(e.value) for e in PolicyStatus])})", name='check_config_policy'),
    )

class Assessment(Base):
    __tablename__ = 'assessments'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ward_id: Mapped[str] = mapped_column(String, index=True)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String)
    hazard: Mapped[float] = mapped_column(Float)
    hazard_band: Mapped[str] = mapped_column(String)
    exposure: Mapped[float] = mapped_column(Float)
    vulnerability: Mapped[float] = mapped_column(Float)
    impact: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[Optional[str]] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float)
    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    config_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    input_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    
    __table_args__ = (
        CheckConstraint(f"status IN ({','.join([repr(e.value) for e in AssessmentStatus])})", name='check_assessment_status'),
        CheckConstraint(f"risk_level IN ({','.join([repr(e.value) for e in RiskLevel])}) OR risk_level IS NULL", name='check_assessment_risk_level'),
    )

class EvidenceItem(Base):
    __tablename__ = 'evidence_items'
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('assessments.id'), index=True)
    evidence_type: Mapped[str] = mapped_column(String)
    source_id: Mapped[str] = mapped_column(String)
    data_hash: Mapped[str] = mapped_column(String)
    value: Mapped[dict] = mapped_column(JSON)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Explanation(Base):
    __tablename__ = 'explanations'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('assessments.id'), unique=True)
    method: Mapped[str] = mapped_column(String)
    factors: Mapped[dict] = mapped_column(JSON)
    narrative: Mapped[Optional[str]] = mapped_column(String)
    model_version: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AgentExecution(Base):
    __tablename__ = 'agent_executions'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    graph_name: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String)
    nodes_executed: Mapped[dict] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(String)

class Recommendation(Base):
    __tablename__ = 'recommendations'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('assessments.id'), index=True)
    recommendation_type: Mapped[str] = mapped_column(String)
    priority: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    actions: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class DecisionCase(Base):
    __tablename__ = 'decision_cases'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('assessments.id'), unique=True)
    status: Mapped[str] = mapped_column(String)
    content_hash: Mapped[str] = mapped_column(String)
    alert_version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    __table_args__ = (
        CheckConstraint(f"status IN ({','.join([repr(e.value) for e in AssessmentStatus])})", name='check_decision_case_status'),
    )

class Review(Base):
    __tablename__ = 'reviews'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    decision_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('decision_cases.id'), index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    decision: Mapped[str] = mapped_column(String)
    rationale: Mapped[str] = mapped_column(String)
    checklist: Mapped[dict] = mapped_column(JSON)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    
    __table_args__ = (
        CheckConstraint("decision IN ('APPROVE','REJECT','REQUEST_CHANGES')", name='check_review_decision'),
    )

class Alert(Base):
    __tablename__ = 'alerts'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    decision_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('decision_cases.id'), index=True)
    alert_level: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    dispatch_method: Mapped[Optional[str]] = mapped_column(String)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)

class Route(Base):
    __tablename__ = 'routes'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey('assessments.id'))
    origin_geom: Mapped[Any] = mapped_column(Geometry('POINT', srid=32644))
    destination_geom: Mapped[Any] = mapped_column(Geometry('POINT', srid=32644))
    route_geom: Mapped[Optional[Any]] = mapped_column(Geometry('LINESTRING', srid=32644))
    distance_m: Mapped[Optional[float]] = mapped_column(Float)
    duration_s: Mapped[Optional[float]] = mapped_column(Float)
    srs_score: Mapped[Optional[float]] = mapped_column(Float)
    risk_summary: Mapped[Optional[dict]] = mapped_column(JSON)
    hazard_assessment_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Outcome(Base):
    __tablename__ = 'outcomes'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('assessments.id'), index=True)
    alert_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey('alerts.id'))
    actual_level: Mapped[Optional[str]] = mapped_column(String)
    actual_water_level: Mapped[Optional[float]] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AuditLog(Base):
    __tablename__ = 'audit_log'
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String)
    entity_type: Mapped[str] = mapped_column(String)
    entity_id: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)
    details: Mapped[dict] = mapped_column(JSON)
    prev_hash: Mapped[Optional[str]] = mapped_column(String)
    row_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class DataSource(Base):
    __tablename__ = 'data_sources'
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    source_type: Mapped[str] = mapped_column(String)
    url: Mapped[Optional[str]] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    resolution: Mapped[Optional[str]] = mapped_column(String)
    frequency: Mapped[Optional[str]] = mapped_column(String)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)


class SpatialDataset(Base):
    """Portable dataset catalog shared by SQLite and PostgreSQL deployments.

    Geometry stays GeoJSON (EPSG:4326) at this boundary so the local SQLite
    prototype does not require a spatial extension. A PostGIS deployment can
    add a projected geometry column and indexes without changing API payloads.
    """

    __tablename__ = "spatial_datasets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    metadata_json: Mapped[dict] = mapped_column(JSON)
    feature_count: Mapped[int] = mapped_column(Integer, default=0)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SpatialDatasetFeature(Base):
    """One source feature stored in its exchange CRS with intact attributes."""

    __tablename__ = "spatial_dataset_features"

    dataset_id: Mapped[str] = mapped_column(ForeignKey("spatial_datasets.id", ondelete="CASCADE"), primary_key=True)
    feature_id: Mapped[str] = mapped_column(String, primary_key=True)
    geometry_geojson: Mapped[dict] = mapped_column(JSON)
    properties: Mapped[dict] = mapped_column(JSON)
