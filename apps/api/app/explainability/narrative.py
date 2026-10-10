"""AquaRizz Template Narrative Explainer (P1-10, ADR-005).

Generates grounded operator explanation briefings without external LLM calls.
Fully deterministic, cites exact evidence items, and complies with verifiers V1-V6.
"""
from __future__ import annotations

from typing import Dict, Any, List


class TemplateNarrator:
    """Generates deterministic briefings based on exact Shapley attributions."""

    @staticmethod
    def generate_narrative(
        ward_id: str,
        risk_level: str,
        hazard_prob: float,
        shapley_factors: List[Dict[str, Any]],
        evidence_ids: List[str],
        confidence: float,
    ) -> str:
        """Compose human-readable explanation narrative."""
        if not shapley_factors:
            return f"Ward {ward_id} assessed at {risk_level} risk (Hazard: {hazard_prob:.2f})."

        top_factor = shapley_factors[0]
        factor_name = top_factor["factor_name"].replace("_", " ").title()
        contrib = top_factor["contribution"]
        observed = top_factor.get("observed_value", 0.0)

        narrative = (
            f"Ward {ward_id} assessed at {risk_level} risk with {confidence:.0%} confidence. "
            f"Physical hazard probability is {hazard_prob:.2f}. "
            f"Primary risk driver is {factor_name} ({observed}) contributing +{contrib:.2f} to hazard. "
        )

        if len(shapley_factors) > 1:
            second_factor = shapley_factors[1]
            f2_name = second_factor["factor_name"].replace("_", " ").title()
            f2_contrib = second_factor["contribution"]
            narrative += f"Secondary driver is {f2_name} contributing +{f2_contrib:.2f}. "

        if evidence_ids:
            citations = ", ".join(evidence_ids[:3])
            narrative += f"Ground telemetry validated via {citations}."

        return narrative
