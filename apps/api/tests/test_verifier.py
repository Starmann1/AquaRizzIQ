import pytest
from app.llm.verifier import NarrativeVerifier


def test_narrative_verifier_success():
    text = "Ward WARD-112 is at HIGH risk. Primary driver is rainfall 75.0 mm contributing to hazard."
    is_valid, violations = NarrativeVerifier.verify(
        narrative_text=text,
        allowed_numbers=[75.0, 112.0],
        valid_evidence_ids=["EV-RAIN-01"],
    )
    assert is_valid is True
    assert len(violations) == 0


def test_narrative_verifier_prohibited_certainty_v4():
    text = "The catchment will definitely flood within 30 minutes."
    is_valid, violations = NarrativeVerifier.verify(
        narrative_text=text,
        allowed_numbers=[30.0],
        valid_evidence_ids=[],
    )
    assert is_valid is False
    assert any("V4:" in v for v in violations)


def test_narrative_verifier_prohibited_imperative_v5():
    text = "Residents must evacuate immediately to avoid danger."
    is_valid, violations = NarrativeVerifier.verify(
        narrative_text=text,
        allowed_numbers=[],
        valid_evidence_ids=[],
    )
    assert is_valid is False
    assert any("V5:" in v for v in violations)


def test_narrative_verifier_hallucinated_number_v1():
    text = "Flood waters are rising at 98.4 meters per hour."
    is_valid, violations = NarrativeVerifier.verify(
        narrative_text=text,
        allowed_numbers=[12.0, 5.0],  # 98.4 is not in input payload
        valid_evidence_ids=[],
    )
    assert is_valid is False
    assert any("V1:" in v for v in violations)
