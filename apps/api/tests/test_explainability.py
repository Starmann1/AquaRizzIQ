from datetime import datetime, timezone
import pytest
from app.risk.hazard import HazardEngine
from app.explainability.shapley import ExactShapleyExplainer
from app.explainability.evidence import EvidenceRegistry
from app.explainability.narrative import TemplateNarrator


def test_exact_shapley_attribution():
    hazard_engine = HazardEngine()

    def eval_fn(f):
        h, _, _ = hazard_engine.compute_hazard(f)
        return h

    target_features = {
        "rainfall_1h": 70.0,
        "water_level_m": 2.2,
        "rate_of_rise": 0.6,
        "static_susceptibility": 0.8,
    }

    explainer = ExactShapleyExplainer()
    factors = explainer.explain(target_features, eval_fn)

    assert len(factors) == 4
    # All active positive features must have positive attribution
    for f in factors:
        assert f["contribution"] > 0.0
        assert f["direction"] == "INCREASES_RISK"

    # Sum of Shapley values roughly equals v(target) - v(baseline)
    h_target = eval_fn(target_features)
    h_base = eval_fn(explainer.baseline)
    total_attr = sum(f["contribution"] for f in factors)
    assert pytest.approx(total_attr, abs=0.05) == (h_target - h_base)


def test_evidence_registry_hashing():
    now = datetime.now(timezone.utc)
    ev = EvidenceRegistry.create_evidence_item(
        evidence_type="SENSOR_OBS",
        ward_id="WARD-112",
        source_id="SIM-SWD-W112-001",
        value={"water_level_m": 1.85},
        observed_at=now,
    )

    assert ev["id"].startswith("EV-SENSOR_OBS-WARD-112-")
    assert len(ev["data_hash"]) == 64  # SHA-256


def test_template_narrator():
    factors = [
        {"factor_name": "rainfall_1h", "contribution": 0.35, "observed_value": 75.0},
        {"factor_name": "water_level_m", "contribution": 0.28, "observed_value": 2.2},
    ]
    evidence_ids = ["EV-RAIN-W112-01", "EV-SENS-W112-01"]

    narrative = TemplateNarrator.generate_narrative(
        ward_id="WARD-112",
        risk_level="HIGH",
        hazard_prob=0.68,
        shapley_factors=factors,
        evidence_ids=evidence_ids,
        confidence=0.88,
    )

    assert "Ward WARD-112 assessed at HIGH risk" in narrative
    assert "Rainfall 1H (75.0) contributing +0.35" in narrative
    assert "EV-RAIN-W112-01" in narrative
