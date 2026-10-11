"""AquaRizz Human Review & Approval Service (P0-04, P0-05, P1-13).

Manages the safety-critical human-in-the-loop approval state machine:
  DRAFT -> PENDING_REVIEW -> APPROVED -> DISPATCHED -> OUTCOME_CAPTURED
  (Terminal: REJECTED, EXPIRED, ABSTAINED, INSUFFICIENT_EVIDENCE, FAILED)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.db.models import DecisionCase, Review, Alert
from app.db.enums import AssessmentStatus, UserRole
from app.errors import ConflictError, AuthorizationError, ValidationError, StaleDataError

MAX_ASSESSMENT_AGE_MINUTES = 30
APPROVAL_VALIDITY_MINUTES = 60


class HumanReviewService:
    """Enforces database-backed human review state transitions and dispatch guards."""

    def __init__(self, db: Session):
        self.db = db

    def submit_for_review(
        self,
        assessment_id: uuid.UUID,
        alert_level: str,
        content_hash: str,
        created_by: str = "LangGraph-Orchestrator",
    ) -> DecisionCase:
        """Create or transition a decision case to PENDING_REVIEW."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=MAX_ASSESSMENT_AGE_MINUTES)

        case = (
            self.db.query(DecisionCase)
            .filter(DecisionCase.assessment_id == assessment_id)
            .first()
        )
        if case:
            case.status = AssessmentStatus.PENDING_REVIEW.value
            case.content_hash = content_hash
            case.alert_version += 1
            case.updated_at = now
            case.expires_at = expires_at
        else:
            case = DecisionCase(
                id=uuid.uuid4(),
                assessment_id=assessment_id,
                status=AssessmentStatus.PENDING_REVIEW.value,
                content_hash=content_hash,
                alert_version=1,
                created_by=created_by,
                created_at=now,
                updated_at=now,
                expires_at=expires_at,
            )
            self.db.add(case)

        self.db.commit()
        return case

    def approve_case(
        self,
        case_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        reviewer_role: str,
        rationale: str,
        checklist: Dict[str, bool],
        assessed_at: datetime,
        alert_level: str = "HIGH",
    ) -> DecisionCase:
        """Approve an alert decision case. Enforces guards S-01 to S-05."""
        case = self.db.query(DecisionCase).filter(DecisionCase.id == case_id).first()
        if not case:
            raise ValidationError(f"Decision case {case_id} not found")

        # Guard 1: Status must be PENDING_REVIEW
        if case.status != AssessmentStatus.PENDING_REVIEW.value:
            raise ConflictError(f"Cannot approve case in status {case.status}")

        # Guard 2: Staleness check (max 30 min from assessment in production)
        now = datetime.now(timezone.utc)
        if assessed_at.tzinfo is None:
            assessed_at = assessed_at.replace(tzinfo=timezone.utc)
        age_minutes = (now - assessed_at).total_seconds() / 60.0
        from app.config import get_settings
        if age_minutes > MAX_ASSESSMENT_AGE_MINUTES and get_settings().app_env.value != "development":
            case.status = AssessmentStatus.EXPIRED.value
            self.db.commit()
            raise StaleDataError(f"Assessment age ({age_minutes:.1f}m) exceeds 30m validity window")

        # Guard 3: RBAC check
        # High/Very High alerts require EMERGENCY_COORDINATOR or ADMINISTRATOR
        if alert_level in ("HIGH", "VERY_HIGH"):
            if reviewer_role not in (UserRole.EMERGENCY_COORDINATOR.value, UserRole.ADMINISTRATOR.value):
                raise AuthorizationError(f"Role {reviewer_role} cannot approve {alert_level} alerts")

        # Guard 4: Checklist completeness
        required_checks = ["evidence_reviewed", "risk_verified", "recommendations_approved"]
        for chk in required_checks:
            if not checklist.get(chk, False):
                raise ValidationError(f"Mandatory checklist item '{chk}' is not confirmed")

        # Record approval in append-only reviews table
        rev = Review(
            id=uuid.uuid4(),
            decision_case_id=case.id,
            reviewer_id=reviewer_id,
            decision="APPROVE",
            rationale=rationale,
            checklist=checklist,
            reviewed_at=now,
        )
        self.db.add(rev)

        # Transition status
        case.status = AssessmentStatus.APPROVED.value
        case.updated_at = now
        case.expires_at = now + timedelta(minutes=APPROVAL_VALIDITY_MINUTES)
        self.db.commit()
        return case

    def reject_case(
        self,
        case_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        rationale: str,
        checklist: Dict[str, bool],
    ) -> DecisionCase:
        """Reject an alert decision case."""
        case = self.db.query(DecisionCase).filter(DecisionCase.id == case_id).first()
        if not case:
            raise ValidationError(f"Decision case {case_id} not found")

        now = datetime.now(timezone.utc)
        rev = Review(
            id=uuid.uuid4(),
            decision_case_id=case.id,
            reviewer_id=reviewer_id,
            decision="REJECT",
            rationale=rationale,
            checklist=checklist,
            reviewed_at=now,
        )
        self.db.add(rev)
        case.status = AssessmentStatus.REJECTED.value
        case.updated_at = now
        self.db.commit()
        return case

    def dispatch_alert(
        self, case_id: uuid.UUID, message: str, alert_level: str
    ) -> Alert:
        """Dispatch an approved alert. Fails if case is not APPROVED (P0-04, S-01)."""
        case = self.db.query(DecisionCase).filter(DecisionCase.id == case_id).first()
        if not case:
            raise ValidationError(f"Decision case {case_id} not found")

        if case.status != AssessmentStatus.APPROVED.value:
            raise ConflictError(f"Dispatch blocked: Decision case is {case.status}, not APPROVED")

        now = datetime.now(timezone.utc)
        expires = case.expires_at
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires and now > expires:
            case.status = AssessmentStatus.EXPIRED.value
            self.db.commit()
            raise StaleDataError("Dispatch blocked: Approval validity window has expired")

        alert = Alert(
            id=uuid.uuid4(),
            decision_case_id=case.id,
            alert_level=alert_level,
            message=message,
            dispatched_at=now,
            dispatch_method="SIMULATED_GATEWAY",
            is_simulated=True,
        )
        self.db.add(alert)
        case.status = AssessmentStatus.DISPATCHED.value
        case.updated_at = now
        self.db.commit()
        return alert
