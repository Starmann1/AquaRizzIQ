import pytest
from app.audit.logger import AuditLogger


def test_audit_logger_hash_chain(db_session):
    logger = AuditLogger(db_session)

    entry1 = logger.log_event(
        event_type="ASSESSMENT_COMPLETED",
        entity_type="ASSESSMENT",
        entity_id="A-101",
        actor="LangGraph-Orchestrator",
        details={"risk_level": "HIGH", "hazard": 0.72},
    )

    entry2 = logger.log_event(
        event_type="ALERT_APPROVED",
        entity_type="DECISION_CASE",
        entity_id="DC-501",
        actor="coordinator_suresh",
        details={"status": "APPROVED", "alert_level": "HIGH"},
    )

    assert entry1.prev_hash == "GENESIS"
    assert len(entry1.row_hash) == 64  # SHA-256
    assert entry2.prev_hash == entry1.row_hash
    assert len(entry2.row_hash) == 64
    assert entry1.row_hash != entry2.row_hash
