from datetime import datetime, timezone
import pytest
from app.agents.graph import FloodAnalysisGraph


def test_langgraph_pipeline_execution():
    pipeline = FloodAnalysisGraph()

    initial_state = {
        "ward_id": "WARD-112",
        "as_of": datetime.now(timezone.utc),
        "dynamic_features": {
            "rainfall_1h": 80.0,
            "rainfall_3h": 120.0,
            "water_level_m": 2.2,
            "rate_of_rise": 0.05,
            "static_susceptibility": 0.85,
        },
        "static_features": {
            "population_at_risk": 0.85,
            "critical_facilities": 0.80,
            "sensitive_population_share": 0.70,
            "shelter_distance_gap": 0.60,
            "housing_density": 0.85,
        },
    }

    final_state = pipeline.graph.invoke(initial_state)

    nodes = final_state.get("nodes_executed", [])
    assert "plan" in nodes
    assert "retrieve_validate" in nodes
    assert "forecast" in nodes
    assert "risk" in nodes
    assert "rca_explain" in nodes
    assert "decide" in nodes
    assert "policy_check" in nodes
    assert "abstain" not in nodes

    # High risk -> alert draft must be produced for human review
    assert final_state["risk_assessment"]["risk_level"] in ("HIGH", "VERY_HIGH")
    alert_draft = final_state["alert_draft"]
    assert alert_draft is not None
    assert alert_draft["status"] == "PENDING_REVIEW"
    assert len(alert_draft["recommendations"]) > 0


def test_langgraph_abstention_on_empty_data():
    pipeline = FloodAnalysisGraph()

    # Empty dynamic features
    initial_state = {
        "ward_id": "WARD-118",
        "as_of": datetime.now(timezone.utc),
        "dynamic_features": {},
    }

    final_state = pipeline.graph.invoke(initial_state)
    nodes = final_state.get("nodes_executed", [])

    assert "abstain" in nodes
    assert final_state.get("is_abstained") is True
