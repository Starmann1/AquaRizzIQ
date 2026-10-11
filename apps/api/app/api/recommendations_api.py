import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit.logger import AuditLogger
from app.database import get_db
from app.db.enums import AssessmentStatus
from app.db.models import Recommendation, Assessment, DecisionCase, Ward

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class ActionDispatchRequest(BaseModel):
    action_id: str
    action_title: str
    action_description: str
    ward_id: str
    ward_name: Optional[str] = None
    zone: Optional[str] = None
    department: str
    authority_of_control: Optional[str] = None
    priority: str = "MEDIUM"
    urgency: Optional[str] = "Immediate (Within 30 mins)"
    actor: Optional[str] = "EMERGENCY_COORDINATOR"


@router.get("")
def list_recommendations(assessment_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Return active municipal action recommendations from PostgreSQL."""
    query = db.query(Recommendation)
    if assessment_id:
        try:
            aid = uuid.UUID(assessment_id)
            query = query.filter(Recommendation.assessment_id == aid)
        except ValueError:
            return []

    records = query.order_by(Recommendation.created_at.desc()).limit(50).all()

    results = []
    for r in records:
        a = db.query(Assessment).filter(Assessment.id == r.assessment_id).first()
        results.append({
            "id": str(r.id),
            "assessment_id": str(r.assessment_id),
            "ward_id": a.ward_id if a else None,
            "type": r.recommendation_type,
            "priority": r.priority,
            "description": r.description,
            "actions": r.actions,
            "created_at": r.created_at.isoformat(),
        })

    return results


@router.post("/dispatch")
def dispatch_recommendation(payload: ActionDispatchRequest, db: Session = Depends(get_db)):
    """Dispatch a recommended action: creates an Assessment, Recommendation, DecisionCase (PENDING_REVIEW)
    for the respective department/authority, and cryptographically logs an append-only audit trail."""
    now = datetime.now(timezone.utc)
    target_authority = payload.authority_of_control or payload.department

    # Check if a pending case already exists for this exact action_id and ward_id
    existing_cases = (
        db.query(DecisionCase)
        .join(Assessment, DecisionCase.assessment_id == Assessment.id)
        .filter(Assessment.ward_id == payload.ward_id, DecisionCase.status == "PENDING_REVIEW")
        .all()
    )
    for ec in existing_cases:
        ass = db.query(Assessment).filter(Assessment.id == ec.assessment_id).first()
        if ass and ass.input_snapshot and ass.input_snapshot.get("action_id") == payload.action_id:
            return {
                "status": "PENDING_REVIEW",
                "case_id": str(ec.id),
                "assessment_id": str(ass.id),
                "action_id": payload.action_id,
                "department": payload.department,
                "authority_of_control": target_authority,
                "ward_id": payload.ward_id,
                "priority": payload.priority,
                "message": f"Action {payload.action_id} is already in Human Review queue for {target_authority}.",
            }

    # Query ward's latest assessment values if available, or default to realistic parameters
    latest_ward_assessment = (
        db.query(Assessment)
        .filter(Assessment.ward_id == payload.ward_id)
        .order_by(Assessment.created_at.desc())
        .first()
    )

    hazard = latest_ward_assessment.hazard if latest_ward_assessment else 0.72
    hazard_band = latest_ward_assessment.hazard_band if latest_ward_assessment else "HIGH"
    exposure = latest_ward_assessment.exposure if latest_ward_assessment else 0.80
    vulnerability = latest_ward_assessment.vulnerability if latest_ward_assessment else 0.65
    impact = latest_ward_assessment.impact if latest_ward_assessment else 0.52
    risk_score = latest_ward_assessment.risk_score if latest_ward_assessment else 0.70

    # 1. Create a specialized assessment for this action dispatch
    action_assessment = Assessment(
        id=uuid.uuid4(),
        ward_id=payload.ward_id,
        assessed_at=now,
        status=AssessmentStatus.PENDING_REVIEW.value,
        hazard=hazard,
        hazard_band=hazard_band,
        exposure=exposure,
        vulnerability=vulnerability,
        impact=impact,
        risk_score=risk_score,
        risk_level=payload.priority if payload.priority in ("CRITICAL", "HIGH", "MEDIUM", "LOW") else "HIGH",
        confidence=0.96,
        input_snapshot={
            "action_id": payload.action_id,
            "action_title": payload.action_title,
            "action_description": payload.action_description,
            "department": payload.department,
            "authority_of_control": target_authority,
            "ward_id": payload.ward_id,
            "ward_name": payload.ward_name or payload.ward_id,
            "zone": payload.zone or "Greater Chennai Corporation",
            "priority": payload.priority,
            "urgency": payload.urgency or "Immediate (Within 30 mins)",
            "dispatched_at": now.isoformat(),
            "is_simulated": True,
        },
        is_simulated=True,
        created_at=now,
    )
    db.add(action_assessment)
    db.flush()

    # 2. Create the recommendation row
    rec = Recommendation(
        id=uuid.uuid4(),
        assessment_id=action_assessment.id,
        recommendation_type=payload.action_id,
        priority=payload.priority,
        description=f"[{target_authority}] {payload.action_title}: {payload.action_description}",
        actions={
            "action_id": payload.action_id,
            "title": payload.action_title,
            "description": payload.action_description,
            "department": payload.department,
            "authority_of_control": target_authority,
            "ward_id": payload.ward_id,
            "ward_name": payload.ward_name,
            "zone": payload.zone,
            "urgency": payload.urgency,
            "priority": payload.priority,
        },
        created_at=now,
    )
    db.add(rec)

    # 3. Create the DecisionCase
    hash_content = f"{payload.action_id}:{payload.ward_id}:{target_authority}:{now.isoformat()}"
    content_hash = f"EV-ACT-{hashlib.sha256(hash_content.encode('utf-8')).hexdigest()[:12]}"

    decision_case = DecisionCase(
        id=uuid.uuid4(),
        assessment_id=action_assessment.id,
        status=AssessmentStatus.PENDING_REVIEW.value,
        content_hash=content_hash,
        alert_version=1,
        created_by=f"ActionDispatch:{target_authority}",
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(minutes=60),
    )
    db.add(decision_case)
    db.commit()
    db.refresh(decision_case)

    # 4. Cryptographic Audit Trail Log
    audit_logger = AuditLogger(db)
    audit_record = audit_logger.log_event(
        event_type="RECOMMENDED_ACTION_SUBMITTED_FOR_REVIEW",
        entity_type="RECOMMENDED_ACTION",
        entity_id=payload.action_id,
        actor=payload.actor or "EMERGENCY_COORDINATOR",
        details={
            "action_id": payload.action_id,
            "case_id": str(decision_case.id),
            "assessment_id": str(action_assessment.id),
            "title": payload.action_title,
            "department": payload.department,
            "authority_of_control": target_authority,
            "ward_id": payload.ward_id,
            "ward_name": payload.ward_name or payload.ward_id,
            "zone": payload.zone or "Greater Chennai Corporation",
            "priority": payload.priority,
            "urgency": payload.urgency,
            "status": "PENDING_REVIEW",
            "description": payload.action_description,
            "dispatched_by": payload.actor or "EMERGENCY_COORDINATOR",
            "notes": f"Pending authorization required by {target_authority}",
        },
    )

    return {
        "status": "PENDING_REVIEW",
        "case_id": str(decision_case.id),
        "assessment_id": str(action_assessment.id),
        "action_id": payload.action_id,
        "department": payload.department,
        "authority_of_control": target_authority,
        "ward_id": payload.ward_id,
        "priority": payload.priority,
        "audit_record": {
            "id": str(audit_record.id),
            "event_type": audit_record.event_type,
            "prev_hash": audit_record.prev_hash,
            "row_hash": audit_record.row_hash,
            "created_at": audit_record.created_at.isoformat(),
        },
        "message": f"Action {payload.action_id} logged in Human Review for {target_authority}. Cryptographic audit trail recorded.",
    }
