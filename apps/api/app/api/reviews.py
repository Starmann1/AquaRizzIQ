import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.db.models import DecisionCase, Assessment, User
from app.services.review import HumanReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


class ApprovalPayload(BaseModel):
    reviewer_id: str
    reviewer_role: str = "EMERGENCY_COORDINATOR"
    rationale: str
    checklist: Dict[str, bool]


class RejectionPayload(BaseModel):
    reviewer_id: str
    rationale: str
    checklist: Dict[str, bool] = {}


@router.get("/pending")
def list_pending_reviews(db: Session = Depends(get_db)):
    """Retrieve decision cases waiting for operator approval."""
    cases = (
        db.query(DecisionCase)
        .filter(DecisionCase.status == "PENDING_REVIEW")
        .order_by(DecisionCase.created_at.desc())
        .all()
    )
    results = []
    for c in cases:
        assessment = db.query(Assessment).filter(Assessment.id == c.assessment_id).first()
        results.append({
            "case_id": str(c.id),
            "assessment_id": str(c.assessment_id),
            "ward_id": assessment.ward_id if assessment else "UNKNOWN",
            "risk_level": assessment.risk_level if assessment else "HIGH",
            "status": c.status,
            "created_at": c.created_at.isoformat(),
            "expires_at": c.expires_at.isoformat() if c.expires_at else None,
            "content_hash": c.content_hash,
        })
    return results


@router.post("/{case_id}/approve")
def approve_review(
    case_id: str,
    payload: ApprovalPayload,
    db: Session = Depends(get_db),
):
    """Approve a flood warning or evacuation advisory alert."""
    try:
        cid = uuid.UUID(case_id)
        rid = uuid.UUID(payload.reviewer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    case = db.query(DecisionCase).filter(DecisionCase.id == cid).first()
    if not case:
        raise HTTPException(status_code=404, detail="Decision case not found")

    assessment = db.query(Assessment).filter(Assessment.id == case.assessment_id).first()
    assessed_at = assessment.assessed_at if assessment else datetime.now(timezone.utc)
    alert_level = assessment.risk_level if assessment else "HIGH"

    service = HumanReviewService(db)
    approved = service.approve_case(
        case_id=cid,
        reviewer_id=rid,
        reviewer_role=payload.reviewer_role,
        rationale=payload.rationale,
        checklist=payload.checklist,
        assessed_at=assessed_at,
        alert_level=alert_level or "HIGH",
    )

    return {
        "case_id": str(approved.id),
        "status": approved.status,
        "message": "Alert decision case approved. Ready for dispatch.",
        "expires_at": approved.expires_at.isoformat() if approved.expires_at else None,
    }


@router.post("/{case_id}/reject")
def reject_review(
    case_id: str,
    payload: RejectionPayload,
    db: Session = Depends(get_db),
):
    """Reject an alert decision case."""
    try:
        cid = uuid.UUID(case_id)
        rid = uuid.UUID(payload.reviewer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    service = HumanReviewService(db)
    rejected = service.reject_case(
        case_id=cid,
        reviewer_id=rid,
        rationale=payload.rationale,
        checklist=payload.checklist,
    )

    return {
        "case_id": str(rejected.id),
        "status": rejected.status,
        "message": "Alert decision case rejected.",
    }
