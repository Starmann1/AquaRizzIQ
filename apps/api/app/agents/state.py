"""AquaRizz Typed AnalysisState for LangGraph Pipeline (P1-11).

Defines the explicit shared state passed between the 6 canonical agents.
"""
from __future__ import annotations

from typing import TypedDict, Dict, Any, List, Optional
from datetime import datetime


class AnalysisState(TypedDict, total=False):
    """Shared state contract across all LangGraph assessment nodes."""

    # Context
    ward_id: str
    as_of: datetime

    # Inputs & QC (Data & Retrieval Agent)
    dynamic_features: Dict[str, float]
    static_features: Dict[str, float]
    quality_report: Dict[str, Any]
    evidence_items: List[Dict[str, Any]]

    # Forecasts (Forecasting Agent)
    forecast_results: Dict[str, Any]

    # Risk Assessment (Flood Risk Analysis Agent)
    risk_assessment: Dict[str, Any]

    # Explainability (RCA & Explanation Agent)
    shapley_factors: List[Dict[str, Any]]
    narrative: str

    # Decision & Policy (Decision & Recommendation Agent)
    recommendations: List[Dict[str, Any]]
    alert_draft: Optional[Dict[str, Any]]

    # Governance & Abstention State
    is_abstained: bool
    abstention_reason: Optional[str]

    # Audit & Execution Trail
    nodes_executed: List[str]
    execution_errors: List[str]
