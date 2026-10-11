from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.auth import hash_password
from app.config import get_settings
from app.db.enums import AssessmentStatus, UserRole
from app.db.models import Alert, Assessment, DecisionCase, Review, User


@pytest.fixture
def jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret-with-at-least-32-characters")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def add_operator(db_session, *, role: str = UserRole.EMERGENCY_COORDINATOR.value) -> User:
    operator = User(
        id=uuid.uuid4(),
        username=f"operator-{uuid.uuid4().hex}",
        email=f"operator-{uuid.uuid4().hex}@test.example",
        role=role,
        password_hash=hash_password("secure-test-password-12"),
    )
    db_session.add(operator)
    db_session.commit()
    return operator


@pytest.mark.asyncio
async def test_shared_demo_credentials_are_rejected(client: AsyncClient, jwt_secret):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_operator_routes_require_authentication(client: AsyncClient, jwt_secret):
    case_id = str(uuid.uuid4())
    checklist = {
        "evidence_reviewed": True,
        "risk_verified": True,
        "recommendations_approved": True,
    }
    assert (await client.get("/api/v1/reviews/pending")).status_code == 401
    assert (await client.get("/api/v1/alerts")).status_code == 401
    assert (await client.post(
        f"/api/v1/reviews/{case_id}/approve",
        json={"rationale": "Review attempted without operator identity", "checklist": checklist},
    )).status_code == 401
    assert (await client.post(
        f"/api/v1/reviews/{case_id}/reject",
        json={"rationale": "Review attempted without operator identity"},
    )).status_code == 401
    assert (await client.post(f"/api/v1/alerts/{case_id}/dispatch", json={})).status_code == 401


@pytest.mark.asyncio
async def test_operator_login_binds_review_and_dispatch_to_authenticated_user(
    client: AsyncClient, db_session, jwt_secret
):
    operator = add_operator(db_session)
    assessment_id = uuid.uuid4()
    case_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    db_session.add(
        Assessment(
            id=assessment_id,
            ward_id="WARD-112",
            assessed_at=now,
            status=AssessmentStatus.PENDING_REVIEW.value,
            hazard=0.7,
            hazard_band="HIGH",
            exposure=0.7,
            vulnerability=0.7,
            impact=0.7,
            risk_score=0.7,
            risk_level="HIGH",
            confidence=0.7,
            is_simulated=False,
        )
    )
    db_session.add(
        DecisionCase(
            id=case_id,
            assessment_id=assessment_id,
            status=AssessmentStatus.PENDING_REVIEW.value,
            content_hash="source-backed-test-case",
            created_by="test",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": operator.username, "password": "secure-test-password-12"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    forged_reviewer_id = str(uuid.uuid4())
    approval = await client.post(
        f"/api/v1/reviews/{case_id}/approve",
        headers=headers,
        json={
            "reviewer_id": forged_reviewer_id,
            "reviewer_role": UserRole.ADMINISTRATOR.value,
            "rationale": "Verified the case and completed the required review.",
            "checklist": {
                "evidence_reviewed": True,
                "risk_verified": True,
                "recommendations_approved": True,
            },
        },
    )
    assert approval.status_code == 200
    review = db_session.query(Review).filter(Review.decision_case_id == case_id).one()
    assert review.reviewer_id == operator.id

    dispatch = await client.post(
        f"/api/v1/alerts/{case_id}/dispatch",
        headers=headers,
        json={"message": "Test dispatch; simulated only."},
    )
    assert dispatch.status_code == 200
    alert = db_session.query(Alert).filter(Alert.decision_case_id == case_id).one()
    assert alert.is_simulated is True


@pytest.mark.asyncio
async def test_non_operator_role_cannot_review_or_dispatch(client: AsyncClient, db_session, jwt_secret):
    citizen = add_operator(db_session, role=UserRole.CITIZEN.value)
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": citizen.username, "password": "secure-test-password-12"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    case_id = str(uuid.uuid4())
    assert (await client.get("/api/v1/reviews/pending", headers=headers)).status_code == 403
    assert (await client.post(f"/api/v1/alerts/{case_id}/dispatch", headers=headers, json={})).status_code == 403


def test_password_hash_rejects_plaintext_and_checks_password():
    encoded = hash_password("secure-test-password-12")
    from app.auth import verify_password

    assert encoded != "secure-test-password-12"
    assert verify_password("secure-test-password-12", encoded)
    assert not verify_password("wrong-password", encoded)
    assert not verify_password("admin", "hash")
