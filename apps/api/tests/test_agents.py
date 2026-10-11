from datetime import datetime, timezone
import pytest
from app.agents.graph import FloodAnalysisGraph


def test_langgraph_abstains_when_source_adapters_are_unavailable():
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
    assert nodes == ["plan", "retrieve_validate", "abstain"]
    assert final_state["is_abstained"] is True
    assert final_state["dynamic_features"] == {}
    assert final_state["static_features"] == {}
    assert final_state["evidence_items"] == []
    assert final_state["quality_report"]["source_verified"] is False
    assert "risk_assessment" not in final_state
    assert "alert_draft" not in final_state
    assert "caller-supplied numeric values are not accepted" in final_state["abstention_reason"]


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
