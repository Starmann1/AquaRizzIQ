"""Deterministic scenario replay kept separate from current ward-risk APIs.

All scenario inputs are teaching fixtures. Calculated values are useful for a
repeatable demonstration only and must never be interpreted as observations or
operational forecasts.
"""
from __future__ import annotations

import math
import hashlib
import threading
from pathlib import Path
from typing import Any, Literal

import yaml

from app.risk.engine import RiskEngine

DemoAction = Literal["step", "reset", "advance_to_peak", "set_step"]
_SERVICE_LOCK = threading.Lock()
_SERVICE: DemoScenarioService | None = None


class DemoScenarioService:
    """Manage a single process-local, deterministic demo scenario cursor."""

    def __init__(self, scenario: dict[str, Any]):
        self.scenario_id = str(scenario.get("scenario_id", ""))
        self.name = str(scenario.get("name", ""))
        self.description = str(scenario.get("description", ""))
        self.data_classification = str(scenario.get("data_classification", ""))
        self.assumption_note = str(scenario.get("assumption_note", ""))
        self.fixture_sha256 = hashlib.sha256(
            yaml.safe_dump(scenario, sort_keys=True).encode("utf-8")
        ).hexdigest()
        self.static_features = self._validate_static_features(scenario.get("static_features"))
        self.sensor_depth_m = float(scenario.get("sensor_depth_m", float("nan")))
        if not math.isfinite(self.sensor_depth_m) or self.sensor_depth_m <= 0:
            raise ValueError("Demo scenario must declare a positive sensor_depth_m fixture")
        self.ward_id = str(scenario.get("ward_id", ""))
        self.policy_version = str(scenario.get("policy_version", ""))
        self.timeline = scenario.get("timeline")
        if not self.scenario_id or not self.ward_id or not isinstance(self.timeline, list) or not self.timeline:
            raise ValueError("Demo scenario requires an id, ward, and non-empty timeline")
        self._validate_timeline(self.timeline)
        self._risk_engine = RiskEngine()
        self._current_step = 0
        self._lock = threading.RLock()

    @staticmethod
    def _validate_static_features(values: Any) -> dict[str, float]:
        if not isinstance(values, dict) or not values:
            raise ValueError("Demo scenario must declare explicit static fixture features")
        validated: dict[str, float] = {}
        for name, raw_value in values.items():
            value = float(raw_value)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"Demo static feature {name!r} must be a finite normalized value in [0, 1]")
            validated[str(name)] = value
        return validated

    @staticmethod
    def _validate_timeline(timeline: list[Any]) -> None:
        required = (
            "step",
            "time_offset_min",
            "phase",
            "rainfall_intensity_mmh",
            "rainfall_1h_mm",
            "rainfall_3h_mm",
            "water_level_m",
            "rate_of_rise_m_min",
            "static_susceptibility",
        )
        for expected_index, frame in enumerate(timeline):
            if not isinstance(frame, dict):
                raise ValueError(f"Demo timeline frame {expected_index} must be an object")
            missing = [key for key in required if key not in frame]
            if missing:
                raise ValueError(f"Demo timeline frame {expected_index} is missing {', '.join(missing)}")
            if int(frame["step"]) != expected_index:
                raise ValueError("Demo timeline steps must be contiguous and start at zero")
            numeric_keys = required[1:2] + required[3:8]
            for key in numeric_keys:
                value = float(frame[key])
                if not math.isfinite(value) or value < 0.0:
                    raise ValueError(f"Demo timeline value {key!r} must be finite and non-negative")
            susceptibility = float(frame["static_susceptibility"])
            if susceptibility > 1.0:
                raise ValueError("Demo susceptibility fixture must be in [0, 1]")

    @classmethod
    def from_file(cls, path: Path) -> DemoScenarioService:
        if not path.is_file():
            raise FileNotFoundError(f"Demo scenario file not found: {path}")
        with path.open(encoding="utf-8") as scenario_file:
            document = yaml.safe_load(scenario_file)
        if not isinstance(document, dict):
            raise ValueError("Demo scenario file must contain a YAML object")
        return cls(document)

    def control(self, action: DemoAction, step: int | None = None) -> dict[str, Any]:
        with self._lock:
            if action == "reset":
                self._current_step = 0
                status = "RESET"
            elif action == "step":
                self._current_step = min(self._current_step + 1, len(self.timeline) - 1)
                status = "ADVANCED"
            elif action == "advance_to_peak":
                self._current_step = max(
                    range(len(self.timeline)),
                    key=lambda index: float(self.timeline[index]["rainfall_intensity_mmh"]),
                )
                status = "PEAK_REACHED"
            elif action == "set_step":
                if step is None:
                    raise ValueError("The set_step action requires a step value")
                if step >= len(self.timeline):
                    raise ValueError(f"Step must be between 0 and {len(self.timeline) - 1}")
                self._current_step = step
                status = "STEP_SELECTED"
            else:  # pragma: no cover - Literal rejects unsupported API actions
                raise ValueError(f"Unsupported demo action: {action}")
            return {"status": status, **self._state_unlocked()}

    def state(self) -> dict[str, Any]:
        with self._lock:
            return self._state_unlocked()

    def _state_unlocked(self) -> dict[str, Any]:
        current = self._assessment_for(self._current_step)
        timeline = [self._assessment_for(index)["summary"] for index in range(len(self.timeline))]
        return {
            "scenario_id": self.scenario_id,
            "fixture_sha256": self.fixture_sha256,
            "assessment_reference": f"{self.scenario_id}:{self.fixture_sha256[:12]}:step-{self._current_step}",
            "name": self.name,
            "description": self.description,
            "data_classification": self.data_classification,
            "assumption_note": self.assumption_note,
            "current_step": self._current_step,
            "max_step": len(self.timeline) - 1,
            "peak_step": max(
                range(len(self.timeline)),
                key=lambda index: float(self.timeline[index]["rainfall_intensity_mmh"]),
            ),
            "phase": current["summary"]["phase"],
            "is_simulated": True,
            "assessment": current,
            "timeline": timeline,
        }

    def _assessment_for(self, step_index: int) -> dict[str, Any]:
        frame = self.timeline[step_index]
        dynamic_features = {
            "rainfall_1h": float(frame["rainfall_1h_mm"]),
            "rainfall_3h": float(frame["rainfall_3h_mm"]),
            "water_level_m": float(frame["water_level_m"]),
            "rate_of_rise": float(frame["rate_of_rise_m_min"]),
            "static_susceptibility": float(frame["static_susceptibility"]),
        }
        result = self._risk_engine.evaluate_risk(
            ward_id=self.ward_id,
            dynamic_features=dynamic_features,
            static_features=self.static_features,
            sensor_depth_m=self.sensor_depth_m,
            rate_of_rise_m_min=dynamic_features["rate_of_rise"],
            quality_score=1.0,
        )
        explanation = [
            {
                "feature": name,
                "input_value": dynamic_features[name],
                "weighted_ramp_term": term,
            }
            for name, term in sorted(
                result["feature_contributions"].items(),
                key=lambda item: abs(item[1]),
                reverse=True,
            )
        ]
        return {
            "status": "SIMULATED_SCENARIO_ONLY",
            "is_simulated": True,
            "data_classification": self.data_classification,
            "ward_id": self.ward_id,
            "config_version": self.policy_version,
            "fixture_sha256": self.fixture_sha256,
            "summary": {
                "step": step_index,
                "time_offset_min": int(frame["time_offset_min"]),
                "phase": str(frame["phase"]),
                "rainfall_intensity_mmh": float(frame["rainfall_intensity_mmh"]),
                "water_level_m": dynamic_features["water_level_m"],
                "hazard": result["hazard"],
                "hazard_band": result["hazard_band"],
                "risk_level": result["risk_level"],
                "risk_score": result["risk_score"],
            },
            "inputs": dynamic_features,
            "exposure": result["exposure"],
            "vulnerability": result["vulnerability"],
            "impact": result["impact"],
            "risk_level": result["risk_level"],
            "risk_score": result["risk_score"],
            "hazard": result["hazard"],
            "hazard_band": result["hazard_band"],
            "safety_floor_triggered": result["safety_floor_triggered"],
            "confidence": None,
            "confidence_note": "Not evaluated for simulated scenario fixtures.",
            "explanation": {
                "method": "deterministic weighted-ramp model trace",
                "causal_claim": False,
                "factors": explanation,
            },
            "recommendations": self._recommendations(result["risk_level"]),
            "limitations": [
                "Scenario values are deterministic teaching fixtures, not measurements or forecasts.",
                "Exposure and vulnerability inputs are normalized demonstration assumptions, not verified ward statistics.",
                "Prototype policy thresholds are not approved warning thresholds.",
                "No alert is sent or dispatched from this scenario endpoint.",
            ],
        }

    def _recommendations(self, risk_level: str) -> list[dict[str, Any]]:
        action = (
            "Review simulated evidence and prepare a human-led exercise briefing."
            if risk_level in {"HIGH", "VERY_HIGH"}
            else "Continue the simulated monitoring exercise and review the next scenario step."
        )
        return [
            {
                "type": "EXERCISE_REVIEW",
                "catalogue_id": "DEMO-EXERCISE-REVIEW-01",
                "text": action,
                "status": "DRAFT",
                "approval_required": True,
                "is_simulated": True,
                "scope": "SIMULATED_EXERCISE_ONLY",
                "affected_ward": self.ward_id,
                "urgency": "EXERCISE_ONLY",
                "reason": "Illustrative scenario risk state crossed the prototype review threshold.",
                "assumptions": [self.assumption_note],
                "confidence": None,
                "evidence_requirements": ["review scenario fixtures", "confirm scenario step and assumptions"],
            }
        ]


def get_demo_scenario_service() -> DemoScenarioService:
    global _SERVICE
    with _SERVICE_LOCK:
        if _SERVICE is None:
            repository_root = Path(__file__).resolve().parents[4]
            scenario_path = repository_root / "configs" / "scenarios" / "demo-storm-01.yaml"
            _SERVICE = DemoScenarioService.from_file(scenario_path)
        return _SERVICE


def reset_demo_scenario_service() -> None:
    """Reset the process-local singleton for deterministic tests and demos."""
    global _SERVICE
    with _SERVICE_LOCK:
        _SERVICE = None
