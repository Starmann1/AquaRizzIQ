from pydantic import BaseModel

class HazardDetail(BaseModel):
    score: float

class ExposureDetail(BaseModel):
    score: float

class VulnerabilityDetail(BaseModel):
    score: float

class RiskSummary(BaseModel):
    level: str
    score: float

class WardRiskResponse(BaseModel):
    ward_id: str
    risk: RiskSummary
