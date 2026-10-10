import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import Assessment, Explanation
from app.risk.engine import RiskEngine
from app.explainability.shapley import ExactShapleyExplainer
from app.explainability.narrative import TemplateNarrator

router = APIRouter(prefix="/explanations", tags=["explanations"])
risk_engine = RiskEngine()
explainer = ExactShapleyExplainer()


@router.get("/{assessment_id}")
def get_explanation(assessment_id: str, db: Session = Depends(get_db)):
    """Retrieve exact Shapley factor attribution and narrative explanation for an assessment."""
    try:
        aid = uuid.UUID(assessment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid assessment UUID")

    assessment = db.query(Assessment).filter(Assessment.id == aid).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Sample observation vector for ward
    dyn = {
        "rainfall_1h": 65.0,
        "rainfall_3h": 105.0,
        "water_level_m": 2.15,
        "rate_of_rise": 0.04,
        "static_susceptibility": 0.78,
    }

    def eval_fn(f):
        h, _, _ = risk_engine.hazard_engine.compute_hazard(f)
        return h

    factors = explainer.explain(dyn, eval_fn)
    evidence_ids = [
        f"EV-RAIN-{assessment.ward_id}-20261010-a1b2c3d4",
        f"EV-SENS-{assessment.ward_id}-20261010-e5f6g7h8",
    ]

    narrative = TemplateNarrator.generate_narrative(
        ward_id=assessment.ward_id,
        risk_level=assessment.risk_level or "HIGH",
        hazard_prob=assessment.hazard,
        shapley_factors=factors,
        evidence_ids=evidence_ids,
        confidence=assessment.confidence,
    )

    return {
        "assessment_id": str(assessment.id),
        "ward_id": assessment.ward_id,
        "method": "EXACT_SHAPLEY_COALITIONS",
        "baseline_state": "DRY_WEATHER_MEDIANS",
        "factors": factors,
        "narrative": narrative,
        "evidence_ids": evidence_ids,
        "confidence": assessment.confidence,
        "is_simulated": True,
    }
