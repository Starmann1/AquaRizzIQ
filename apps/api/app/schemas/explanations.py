from pydantic import BaseModel
from typing import List

class FactorContribution(BaseModel):
    factor: str
    contribution: float

class ExplanationResponse(BaseModel):
    assessment_id: str
    factors: List[FactorContribution]
