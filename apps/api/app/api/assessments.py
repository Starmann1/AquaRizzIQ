import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import Assessment, Recommendation, DecisionCase, Explanation
from app.schemas.assessments import AssessmentCreate
from app.agents.graph import FloodAnalysisGraph

router = APIRouter(prefix="/assessments", tags=["assessments"])
analysis_graph = FloodAnalysisGraph()


@router.post("", status_code=202)
def trigger_assessment(payload: AssessmentCreate, db: Session = Depends(get_db)):
    """Execute LangGraph 6-Agent pipeline to evaluate risk for a ward and store to PostgreSQL."""
    ward_id = payload.ward_id

    # Execute compiled LangGraph workflow
    initial_state = {
        "ward_id": ward_id,
        "as_of": datetime.now(timezone.utc),
        "nodes_executed": [],
    }

    result_state = analysis_graph.graph.invoke(initial_state)

    risk_res = result_state.get("risk_assessment", {})
    r_level = risk_res.get("risk_level", "MEDIUM")
    hazard = risk_res.get("hazard", 0.45)
    h_band = risk_res.get("hazard_band", "MEDIUM")
    exposure = risk_res.get("exposure", 0.55)
    vulnerability = risk_res.get("vulnerability", 0.50)
    impact = risk_res.get("impact", 0.52)
    risk_score = risk_res.get("risk_score", 0.35)
    confidence = risk_res.get("confidence", 0.90)

    # Persist Assessment in PostgreSQL
    aid = uuid.uuid4()
    assessment = Assessment(
        id=aid,
        ward_id=ward_id,
        assessed_at=datetime.now(timezone.utc),
        status="APPROVED" if r_level in ["HIGH", "VERY_HIGH"] else "DRAFT",
        hazard=hazard,
        hazard_band=h_band,
        exposure=exposure,
        vulnerability=vulnerability,
        impact=impact,
        risk_score=risk_score,
        risk_level=r_level,
        confidence=confidence,
        input_snapshot={
            "dynamic_features": result_state.get("dynamic_features"),
            "static_features": result_state.get("static_features"),
            "feature_contributions": risk_res.get("feature_contributions", {}),
            "nodes_executed": result_state.get("nodes_executed", []),
        },
        is_simulated=False,
    )
    db.add(assessment)

    # Persist Explanation
    shapley_factors = result_state.get("shapley_factors", [])
    narrative = result_state.get("narrative", "")
    expl = Explanation(
        id=uuid.uuid4(),
        assessment_id=aid,
        method="EXACT_SHAPLEY_COALITION",
        factors={"shapley_factors": shapley_factors},
        narrative=narrative,
        model_version="1.0.0",
    )
    db.add(expl)

    # Persist Recommendations
    recs = result_state.get("recommendations", [])
    for r in recs:
        rec_obj = Recommendation(
            id=uuid.uuid4(),
            assessment_id=aid,
            recommendation_type=r.get("type", "ROUTINE_MONITORING"),
            priority=r.get("priority", "LOW"),
            description=r.get("description", ""),
            actions=r.get("actions", {}),
        )
        db.add(rec_obj)

    # Persist Decision Case
    case_id = uuid.uuid4()
    dcase = DecisionCase(
        id=case_id,
        assessment_id=aid,
        status="PENDING_REVIEW" if r_level in ["HIGH", "VERY_HIGH"] else "APPROVED",
        content_hash=uuid.uuid4().hex[:16],
        alert_version=1,
        created_by="system",
    )
    db.add(dcase)
    db.commit()

    return {
        "id": str(aid),
        "ward_id": ward_id,
        "status": assessment.status,
        "risk_level": r_level,
        "hazard": hazard,
        "hazard_band": h_band,
        "exposure": exposure,
        "vulnerability": vulnerability,
        "impact": impact,
        "risk_score": risk_score,
        "confidence": confidence,
        "is_abstained": False,
        "is_simulated": False,
        "decision_case_id": str(case_id),
        "nodes_executed": result_state.get("nodes_executed", []),
        "narrative": narrative,
        "recommendations": recs,
    }


@router.get("")
def list_assessments(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """List recent assessments from PostgreSQL."""
    records = db.query(Assessment).order_by(Assessment.assessed_at.desc()).limit(limit).all()
    return [
        {
            "id": str(r.id),
            "ward_id": r.ward_id,
            "assessed_at": r.assessed_at.isoformat(),
            "status": r.status,
            "hazard": r.hazard,
            "hazard_band": r.hazard_band,
            "exposure": r.exposure,
            "vulnerability": r.vulnerability,
            "impact": r.impact,
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
    expl = db.query(Explanation).filter(Explanation.assessment_id == aid).first()

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
        "narrative": expl.narrative if expl else None,
        "shapley_factors": expl.factors.get("shapley_factors", []) if expl and expl.factors else [],
        "recommendations": [
            {"type": r.recommendation_type, "priority": r.priority, "description": r.description}
            for r in recs
        ],
    }
