import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import Assessment, EvidenceItem, Recommendation, DecisionCase
from app.schemas.assessments import AssessmentCreate, AssessmentResponse, AssessmentDetail
from app.agents.graph import FloodAnalysisGraph
from app.services.review import HumanReviewService

router = APIRouter(prefix="/assessments", tags=["assessments"])
pipeline = FloodAnalysisGraph()


@router.post("", status_code=202)
def trigger_assessment(payload: AssessmentCreate, db: Session = Depends(get_db)):
    """Trigger the LangGraph 6-agent flood early warning analysis pipeline."""
    now = datetime.now(timezone.utc)
    assessment_id = uuid.uuid4()

    # Dynamic features for ward
    dynamic_features = payload.dynamic_features or {
        "rainfall_1h": 65.0,
        "rainfall_3h": 105.0,
        "water_level_m": 2.15,
        "rate_of_rise": 0.04,
        "static_susceptibility": 0.78,
    }

    initial_state = {
        "ward_id": payload.ward_id,
        "as_of": now,
        "dynamic_features": dynamic_features,
    }

    # Execute LangGraph Pipeline
    final_state = pipeline.graph.invoke(initial_state)
    risk_res = final_state.get("risk_assessment", {})
    alert_draft = final_state.get("alert_draft")

    # Persist Assessment
    rec = Assessment(
        id=assessment_id,
        ward_id=payload.ward_id,
        assessed_at=now,
        status="PENDING_REVIEW" if not final_state.get("is_abstained") else "ABSTAINED",
        hazard=risk_res.get("hazard", 0.0),
        hazard_band=risk_res.get("hazard_band", "LOW"),
        exposure=risk_res.get("exposure", 0.0),
        vulnerability=risk_res.get("vulnerability", 0.0),
        impact=risk_res.get("impact", 0.0),
        risk_score=risk_res.get("risk_score", 0.0),
        risk_level=risk_res.get("risk_level", "LOW"),
        confidence=risk_res.get("confidence", 0.8),
        is_simulated=True,
    )
    db.add(rec)

    # Persist Recommendations
    for r in final_state.get("recommendations", []):
        db.add(
            Recommendation(
                id=uuid.uuid4(),
                assessment_id=assessment_id,
                recommendation_type=r["type"],
                priority=r["priority"],
                description=r["description"],
                actions={},
            )
        )

    # If alert draft generated, submit for Human Review (PENDING_REVIEW)
    case_id = None
    if alert_draft:
        review_service = HumanReviewService(db)
        case = review_service.submit_for_review(
            assessment_id=assessment_id,
            alert_level=alert_draft["alert_level"],
            content_hash=alert_draft.get("content_hash", "hash"),
        )
        case_id = str(case.id)

    db.commit()

    return {
        "assessment_id": str(assessment_id),
        "ward_id": payload.ward_id,
        "status": rec.status,
        "risk_level": rec.risk_level,
        "hazard": rec.hazard,
        "confidence": rec.confidence,
        "decision_case_id": case_id,
        "narrative": final_state.get("narrative", ""),
        "nodes_executed": final_state.get("nodes_executed", []),
        "is_simulated": True,
    }


@router.get("")
def list_assessments(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """List recent assessments."""
    records = db.query(Assessment).order_by(Assessment.assessed_at.desc()).limit(limit).all()
    return [
        {
            "id": str(r.id),
            "ward_id": r.ward_id,
            "assessed_at": r.assessed_at.isoformat(),
            "status": r.status,
            "hazard": r.hazard,
            "hazard_band": r.hazard_band,
            "risk_score": r.risk_score,
            "risk_level": r.risk_level,
            "confidence": r.confidence,
            "is_simulated": r.is_simulated,
        }
        for r in records
    ]


@router.get("/{assessment_id}")
def get_assessment_detail(assessment_id: str, db: Session = Depends(get_db)):
    """Retrieve full detail for an assessment."""
    try:
        aid = uuid.UUID(assessment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid assessment UUID")

    rec = db.query(Assessment).filter(Assessment.id == aid).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Assessment not found")

    recs = db.query(Recommendation).filter(Recommendation.assessment_id == aid).all()
    case = db.query(DecisionCase).filter(DecisionCase.assessment_id == aid).first()

    return {
        "id": str(rec.id),
        "ward_id": rec.ward_id,
        "assessed_at": rec.assessed_at.isoformat(),
        "status": rec.status,
        "hazard": rec.hazard,
        "hazard_band": rec.hazard_band,
        "exposure": rec.exposure,
        "vulnerability": rec.vulnerability,
        "impact": rec.impact,
        "risk_score": rec.risk_score,
        "risk_level": rec.risk_level,
        "confidence": rec.confidence,
        "is_simulated": rec.is_simulated,
        "decision_case_id": str(case.id) if case else None,
        "decision_case_status": case.status if case else None,
        "recommendations": [
            {"type": r.recommendation_type, "priority": r.priority, "description": r.description}
            for r in recs
        ],
    }
