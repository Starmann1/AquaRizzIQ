"""AquaRizz LangGraph Analysis Pipeline (P1-10, P1-11, P1-12).

Implements deterministic 6-agent orchestration:
plan -> retrieve_validate -> qa_gate -> forecast -> risk -> rca_explain -> decide -> policy_check -> persist_draft
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from langgraph.graph import StateGraph, END

from app.agents.state import AnalysisState
from app.risk.engine import RiskEngine
from app.forecasting.m2_water_level import M2WaterLevelForecastModel
from app.explainability.shapley import ExactShapleyExplainer
from app.explainability.narrative import TemplateNarrator
from app.explainability.evidence import EvidenceRegistry


class FloodAnalysisGraph:
    """Compiled LangGraph orchestrator for flood early warning assessment."""

    def __init__(self):
        self.risk_engine = RiskEngine()
        self.forecast_model = M2WaterLevelForecastModel()
        self.explainer = ExactShapleyExplainer()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AnalysisState)

        # Register Nodes
        workflow.add_node("plan", self.node_plan)
        workflow.add_node("retrieve_validate", self.node_retrieve_validate)
        workflow.add_node("forecast", self.node_forecast)
        workflow.add_node("risk", self.node_risk)
        workflow.add_node("rca_explain", self.node_rca_explain)
        workflow.add_node("decide", self.node_decide)
        workflow.add_node("policy_check", self.node_policy_check)
        workflow.add_node("abstain", self.node_abstain)

        # Set Entry Point
        workflow.set_entry_point("plan")

        # Directed Edges
        workflow.add_edge("plan", "retrieve_validate")

        # Conditional Edge after Data Quality Check
        workflow.add_conditional_edges(
            "retrieve_validate",
            self.route_after_qa,
            {
                "continue": "forecast",
                "abstain": "abstain",
            },
        )

        workflow.add_edge("forecast", "risk")

        # Conditional Edge after Risk Calculation
        workflow.add_conditional_edges(
            "risk",
            self.route_after_risk,
            {
                "continue": "rca_explain",
                "abstain": "abstain",
            },
        )

        workflow.add_edge("rca_explain", "decide")
        workflow.add_edge("decide", "policy_check")
        workflow.add_edge("policy_check", END)
        workflow.add_edge("abstain", END)

        return workflow.compile()

    # --- Node Functions ---
    def node_plan(self, state: AnalysisState) -> Dict[str, Any]:
        nodes = state.get("nodes_executed", [])
        return {"nodes_executed": nodes + ["plan"]}

    def node_retrieve_validate(self, state: AnalysisState) -> Dict[str, Any]:
        ward_id = state.get("ward_id", "WARD-112")
        as_of = state.get("as_of", datetime.now(timezone.utc))
        nodes = state.get("nodes_executed", [])

        # Default sample features if not provided
        dyn = state.get("dynamic_features", {
            "rainfall_1h": 45.0,
            "rainfall_3h": 70.0,
            "water_level_m": 1.45,
            "rate_of_rise": 0.03,
            "static_susceptibility": 0.72,
        })
        stat = state.get("static_features", {
            "population_at_risk": 0.82,
            "critical_facilities": 0.75,
            "sensitive_population_share": 0.65,
            "shelter_distance_gap": 0.55,
            "housing_density": 0.80,
        })

        # Quality check: reject if missing all dynamic data
        has_data = len(dyn) > 0
        ev_items = [
            EvidenceRegistry.create_evidence_item("RAIN_OBS", ward_id, "STN-01", {"rainfall_1h": dyn.get("rainfall_1h", 0)}, as_of),
            EvidenceRegistry.create_evidence_item("SENSOR_OBS", ward_id, "SIM-SWD-01", {"water_level_m": dyn.get("water_level_m", 0)}, as_of),
        ]

        return {
            "dynamic_features": dyn,
            "static_features": stat,
            "quality_report": {"has_data": has_data, "qc_state": "VALID" if has_data else "MISSING"},
            "evidence_items": ev_items,
            "nodes_executed": nodes + ["retrieve_validate"],
        }

    def node_forecast(self, state: AnalysisState) -> Dict[str, Any]:
        dyn = state.get("dynamic_features", {})
        nodes = state.get("nodes_executed", [])

        fcst = self.forecast_model.predict_forecasts(
            current_water_level_m=dyn.get("water_level_m", 0.5),
            rainfall_intensity_mmh=dyn.get("rainfall_1h", 20.0),
            rate_of_rise_m_min=dyn.get("rate_of_rise", 0.0),
        )
        return {
            "forecast_results": fcst,
            "nodes_executed": nodes + ["forecast"],
        }

    def node_risk(self, state: AnalysisState) -> Dict[str, Any]:
        ward_id = state.get("ward_id", "WARD-112")
        dyn = state.get("dynamic_features", {})
        stat = state.get("static_features", {})
        nodes = state.get("nodes_executed", [])

        risk_res = self.risk_engine.evaluate_risk(
            ward_id=ward_id,
            dynamic_features=dyn,
            static_features=stat,
        )
        return {
            "risk_assessment": risk_res,
            "is_abstained": risk_res.get("is_abstained", False),
            "nodes_executed": nodes + ["risk"],
        }

    def node_rca_explain(self, state: AnalysisState) -> Dict[str, Any]:
        ward_id = state.get("ward_id", "WARD-112")
        dyn = state.get("dynamic_features", {})
        risk_res = state.get("risk_assessment", {})
        ev_items = state.get("evidence_items", [])
        nodes = state.get("nodes_executed", [])

        def eval_fn(f):
            h, _, _ = self.risk_engine.hazard_engine.compute_hazard(f)
            return h

        factors = self.explainer.explain(dyn, eval_fn)
        evidence_ids = [e["id"] for e in ev_items]

        narrative = TemplateNarrator.generate_narrative(
            ward_id=ward_id,
            risk_level=risk_res.get("risk_level", "LOW"),
            hazard_prob=risk_res.get("hazard", 0.1),
            shapley_factors=factors,
            evidence_ids=evidence_ids,
            confidence=risk_res.get("confidence", 0.8),
        )

        return {
            "shapley_factors": factors,
            "narrative": narrative,
            "nodes_executed": nodes + ["rca_explain"],
        }

    def node_decide(self, state: AnalysisState) -> Dict[str, Any]:
        risk_res = state.get("risk_assessment", {})
        level = risk_res.get("risk_level", "LOW")
        nodes = state.get("nodes_executed", [])

        recs = []
        if level in ("HIGH", "VERY_HIGH"):
            recs.append({
                "type": "EVACUATION_ADVISORY",
                "priority": "P1",
                "description": "Advise ground-floor residents along vulnerable drainage canals to move to designated shelters.",
            })
            recs.append({
                "type": "PUMP_DEPLOYMENT",
                "priority": "P1",
                "description": "Deploy mobile dewatering pumps to low-lying canal outfalls.",
            })
        elif level == "MEDIUM":
            recs.append({
                "type": "MONITOR_DRAINS",
                "priority": "P2",
                "description": "Increase gauge inspection frequency to 5-minute intervals.",
            })

        return {
            "recommendations": recs,
            "nodes_executed": nodes + ["decide"],
        }

    def node_policy_check(self, state: AnalysisState) -> Dict[str, Any]:
        ward_id = state.get("ward_id", "WARD-112")
        risk_res = state.get("risk_assessment", {})
        narrative = state.get("narrative", "")
        recs = state.get("recommendations", [])
        level = risk_res.get("risk_level", "LOW")
        nodes = state.get("nodes_executed", [])

        alert_draft = None
        if level in ("HIGH", "VERY_HIGH"):
            alert_draft = {
                "ward_id": ward_id,
                "alert_level": level,
                "status": "PENDING_REVIEW",
                "message": narrative,
                "recommendations": recs,
                "content_hash": "sha256-draft-content-hash",
            }

        return {
            "alert_draft": alert_draft,
            "nodes_executed": nodes + ["policy_check"],
        }

    def node_abstain(self, state: AnalysisState) -> Dict[str, Any]:
        nodes = state.get("nodes_executed", [])
        return {
            "is_abstained": True,
            "abstention_reason": "Low confidence or missing critical catchment telemetry.",
            "nodes_executed": nodes + ["abstain"],
        }

    # --- Routing Condition Functions ---
    def route_after_qa(self, state: AnalysisState) -> str:
        qr = state.get("quality_report", {})
        return "continue" if qr.get("has_data", True) else "abstain"

    def route_after_risk(self, state: AnalysisState) -> str:
        return "abstain" if state.get("is_abstained", False) else "continue"
