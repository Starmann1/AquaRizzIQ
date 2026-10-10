import uuid
from datetime import datetime, timezone, timedelta
import pytest

from app.db.models import DecisionCase, User
from app.db.enums import AssessmentStatus, UserRole
from app.services.review import HumanReviewService
from app.errors import ConflictError, AuthorizationError, StaleDataError, ValidationError


@pytest.fixture
def test_user(db_session):
    uid = uuid.uuid4().hex[:6]
    u = User(
        id=uuid.uuid4(),
        username=f"coordinator_{uid}",
        password_hash="hash",
        role=UserRole.EMERGENCY_COORDINATOR.value,
        email=f"coord_{uid}@test.gov.in",
    )
    db_session.add(u)
    db_session.commit()
    return u


def test_approval_and_dispatch_flow(db_session, test_user):
    service = HumanReviewService(db_session)
    assessment_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # 1. Submit for review
    case = service.submit_for_review(
        assessment_id=assessment_id,
        alert_level="HIGH",
        content_hash="hash123",
    )
    assert case.status == AssessmentStatus.PENDING_REVIEW.value

    # 2. Cannot dispatch directly while PENDING_REVIEW
    with pytest.raises(ConflictError):
        service.dispatch_alert(case.id, message="Test alert", alert_level="HIGH")

    # 3. Approve with complete checklist and authorized role
    checklist = {
        "evidence_reviewed": True,
        "risk_verified": True,
        "recommendations_approved": True,
    }
    approved_case = service.approve_case(
        case_id=case.id,
        reviewer_id=test_user.id,
        reviewer_role=test_user.role,
        rationale="Telemetry verified. Canal overtopping imminent.",
        checklist=checklist,
        assessed_at=now,
        alert_level="HIGH",
    )
    assert approved_case.status == AssessmentStatus.APPROVED.value

    # 4. Dispatch now succeeds
    alert = service.dispatch_alert(case.id, message="Evacuation Warning", alert_level="HIGH")
    assert alert.dispatched_at is not None
    assert approved_case.status == AssessmentStatus.DISPATCHED.value


def test_rbac_approval_enforcement(db_session, test_user):
    service = HumanReviewService(db_session)
    assessment_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    case = service.submit_for_review(
        assessment_id=assessment_id,
        alert_level="HIGH",
        content_hash="hash123",
    )

    checklist = {
        "evidence_reviewed": True,
        "risk_verified": True,
        "recommendations_approved": True,
    }

    # CITIZEN role cannot approve HIGH alert
    with pytest.raises(AuthorizationError):
        service.approve_case(
            case_id=case.id,
            reviewer_id=test_user.id,
            reviewer_role=UserRole.CITIZEN.value,
            rationale="Citizen trying to approve",
            checklist=checklist,
            assessed_at=now,
            alert_level="HIGH",
        )


def test_stale_assessment_rejection(db_session, test_user):
    service = HumanReviewService(db_session)
    assessment_id = uuid.uuid4()
    # 45 minutes old (> 30 min limit)
    stale_time = datetime.now(timezone.utc) - timedelta(minutes=45)

    case = service.submit_for_review(
        assessment_id=assessment_id,
        alert_level="HIGH",
        content_hash="hash123",
    )

    checklist = {
        "evidence_reviewed": True,
        "risk_verified": True,
        "recommendations_approved": True,
    }

    with pytest.raises(StaleDataError):
        service.approve_case(
            case_id=case.id,
            reviewer_id=test_user.id,
            reviewer_role=test_user.role,
            rationale="Trying to approve old data",
            checklist=checklist,
            assessed_at=stale_time,
            alert_level="HIGH",
        )
