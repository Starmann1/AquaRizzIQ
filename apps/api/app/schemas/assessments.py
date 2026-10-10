from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List

class AssessmentCreate(BaseModel):
    ward_id: str
    dynamic_features: Optional[Dict[str, float]] = None

class AssessmentResponse(BaseModel):
    id: str
    ward_id: str
    status: str
    risk_level: Optional[str] = None
    hazard: Optional[float] = None
    confidence: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)

class AssessmentDetail(AssessmentResponse):
    hazard_band: Optional[str] = None
    exposure: Optional[float] = None
    vulnerability: Optional[float] = None
    impact: Optional[float] = None
    risk_score: Optional[float] = None
    is_simulated: bool = False
    decision_case_id: Optional[str] = None
    recommendations: List[Dict[str, Any]] = []
