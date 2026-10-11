from pathlib import Path

import pytest

from app.services.demo_scenario import DemoScenarioService


SCENARIO_PATH = Path(__file__).resolve().parents[3] / "configs" / "scenarios" / "demo-storm-01.yaml"


def test_demo_scenario_is_deterministic_and_explicitly_simulated():
    scenario = DemoScenarioService.from_file(SCENARIO_PATH)

    first = scenario.state()
    peak = scenario.control("advance_to_peak")
    reset = scenario.control("reset")
    repeated_peak = scenario.control("advance_to_peak")

    assert first["data_classification"] == "SIMULATED_SCENARIO"
    assert first["assessment"]["risk_score"] is not None
    assert first["assessment"]["confidence"] is None
    assert peak["current_step"] == 3
    assert peak["assessment"]["risk_level"] in {"HIGH", "VERY_HIGH"}
    assert peak["assessment"]["explanation"]["causal_claim"] is False
    assert peak["assessment"]["recommendations"][0]["status"] == "DRAFT"
    assert peak["assessment"]["recommendations"][0]["approval_required"] is True
    assert reset["current_step"] == 0
    assert repeated_peak["assessment"] == peak["assessment"]


def test_demo_scenario_rejects_step_outside_timeline():
    scenario = DemoScenarioService.from_file(SCENARIO_PATH)

    with pytest.raises(ValueError, match="between 0 and 6"):
        scenario.control("set_step", 7)


def test_demo_scenario_requires_explicit_static_fixture_inputs():
    with pytest.raises(ValueError, match="explicit static fixture"):
        DemoScenarioService(
            {
                "scenario_id": "bad-demo",
                "ward_id": "WARD-117",
                "timeline": [{"step": 0}],
                "static_features": {},
            }
        )
