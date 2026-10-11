import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.db.models import Alert, DecisionCase, Assessment
from app.services.review import HumanReviewService
from app.auth import OPERATOR_ROLES, require_role

router = APIRouter(prefix="/alerts", tags=["alerts"])


class DispatchPayload(BaseModel):
    message: Optional[str] = None
    alert_level: Optional[str] = None


@router.get("")
def list_alerts(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(OPERATOR_ROLES)),
):
    """Retrieve history of dispatched alerts."""
    records = db.query(Alert).order_by(Alert.dispatched_at.desc()).limit(50).all()
    return [
        {
            "id": str(a.id),
            "decision_case_id": str(a.decision_case_id),
            "alert_level": a.alert_level,
            "message": a.message,
            "dispatched_at": a.dispatched_at.isoformat() if a.dispatched_at else None,
            "dispatch_method": a.dispatch_method,
            "is_simulated": a.is_simulated,
        }
        for a in records
    ]


@router.post("/{case_id}/dispatch")
def dispatch_alert(
    case_id: str,
    payload: DispatchPayload = DispatchPayload(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(OPERATOR_ROLES)),
):
    """Dispatch an approved alert to simulated siren / SMS broadcast gateways."""
    try:
        cid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    case = db.query(DecisionCase).filter(DecisionCase.id == cid).first()
    if not case:
        raise HTTPException(status_code=404, detail="Decision case not found")

    assessment = db.query(Assessment).filter(Assessment.id == case.assessment_id).first()
    level = payload.alert_level or (assessment.risk_level if assessment else "HIGH")
    msg = payload.message or f"FLOOD ALERT [{level}]: Take immediate flood precautions in monitored zones."

    service = HumanReviewService(db)
    alert = service.dispatch_alert(case_id=cid, message=msg, alert_level=level)

    return {
        "alert_id": str(alert.id),
        "case_id": str(case.id),
        "status": "DISPATCHED",
        "alert_level": alert.alert_level,
        "message": alert.message,
        "dispatched_at": alert.dispatched_at.isoformat() if alert.dispatched_at else None,
        "is_simulated": True,
    }
