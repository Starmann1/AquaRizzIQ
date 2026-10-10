import pytest
from app.risk.hazard import HazardEngine
from app.risk.engine import RiskEngine


def test_hazard_monotonicity():
    engine = HazardEngine()

    # Dry conditions
    h_dry, band_dry, _ = engine.compute_hazard({"rainfall_1h": 0.0, "water_level_m": 0.2})
    # Moderate rain
    h_med, band_med, _ = engine.compute_hazard({"rainfall_1h": 35.0, "water_level_m": 1.2})
    # Severe cloudburst
    h_sev, band_sev, _ = engine.compute_hazard({
        "rainfall_1h": 85.0,
        "water_level_m": 2.4,
        "rate_of_rise": 0.8,
        "static_susceptibility": 0.7,
    })

    assert h_dry < h_med < h_sev
    assert band_dry == "LOW"
    assert band_sev in ("HIGH", "VERY_HIGH")


def test_risk_matrix_gating():
    engine = RiskEngine()

    # Low hazard with high exposure/vulnerability -> must stay LOW
    res_gated = engine.evaluate_risk(
        ward_id="WARD-112",
        dynamic_features={"rainfall_1h": 2.0, "water_level_m": 0.2},
        static_features={"population_at_risk": 0.95, "critical_facilities": 0.95},
    )
    assert res_gated["hazard_band"] == "LOW"
    assert res_gated["risk_level"] == "LOW"


def test_safety_floor_override():
    engine = RiskEngine()

    # Low rainfall, but physical sensor fill = 2.6m / 3.0m = 86.7% >= 85% F1 threshold
    res_floor = engine.evaluate_risk(
        ward_id="WARD-113",
        dynamic_features={"rainfall_1h": 5.0, "water_level_m": 2.60},
        static_features={"population_at_risk": 0.3, "critical_facilities": 0.2},
        sensor_depth_m=3.0,
    )

    assert res_floor["risk_level"] in ("HIGH", "VERY_HIGH")
    assert "F1:" in res_floor["safety_floor_triggered"]


def test_confidence_abstention():
    engine = RiskEngine()

    # Very low quality score (< 0.20)
    res_abstain = engine.evaluate_risk(
        ward_id="WARD-117",
        dynamic_features={"rainfall_1h": 40.0, "water_level_m": 1.5},
        static_features={},
        quality_score=0.15,
    )

    assert res_abstain["is_abstained"] is True
    assert res_abstain["risk_level"] == "ABSTAINED"
