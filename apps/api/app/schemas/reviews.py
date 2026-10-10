from pydantic import BaseModel
from typing import Optional

class ReviewCreate(BaseModel):
    decision: str
    rationale: str

class ReviewResponse(BaseModel):
    id: str
    decision: str
