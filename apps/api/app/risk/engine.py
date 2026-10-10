"""AquaRizz Core Risk Engine (P1-04, ADR-004).

Integrates:
- Hazard H = sigmoid((z - b) / T)
- Exposure E and Vulnerability V
- Impact I = 0.6 * E + 0.4 * V
- Matrix-Gated Risk Level
- Deterministic Safety Floors F1-F3
- Confidence Metric C in [0, 1]
"""
from __future__ import annotations

import numpy as np
from typing import Dict, Any, Tuple
from app.risk.hazard import HazardEngine
from app.risk.exposure import ExposureEngine, VulnerabilityEngine
from app.risk.safety_floors import SafetyFloorEvaluator

LEVEL_RANKS = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "VERY_HIGH": 3}
RANK_TO_LEVEL = {0: "LOW", 1: "MEDIUM", 2: "HIGH", 3: "VERY_HIGH"}


class RiskEngine:
    """Evaluates multi-factor flood risk and assigns governance levels."""

    def __init__(self):
        self.hazard_engine = HazardEngine()
        self.exposure_engine = ExposureEngine()
        self.vulnerability_engine = VulnerabilityEngine()
        self.safety_floors = SafetyFloorEvaluator()

    def evaluate_risk(
        self,
        ward_id: str,
        dynamic_features: Dict[str, float],
        static_features: Dict[str, float],
        sensor_depth_m: float = 3.0,
        rate_of_rise_m_min: float = 0.0,
        quality_score: float = 1.0,
    ) -> Dict[str, Any]:
        """Execute complete risk evaluation for a ward.
        
        Returns:
            Dict containing hazard, exposure, vulnerability, impact, risk_score,
            risk_level, active_floor, confidence, and provenance metrics.
        """
        # 1. Compute Hazard
        h_prob, h_band, h_contributions = self.hazard_engine.compute_hazard(dynamic_features)

        # 2. Compute Exposure & Vulnerability
        e_score = self.exposure_engine.compute_exposure(static_features)
        v_score = self.vulnerability_engine.compute_vulnerability(static_features)

        # 3. Compute Impact
        impact = 0.60 * e_score + 0.40 * v_score

        # 4. Continuous Risk Score R in [0, 1]
        # Formula: R = H * (0.4 + 0.6 * Impact)
        risk_score = float(np.clip(h_prob * (0.40 + 0.60 * impact), 0.001, 0.999))

        # 5. Matrix Gating
        # Hazard band defines allowable range; impact selects base vs upgraded level
        if h_band == "LOW":
            base_level = "LOW"
        elif h_band == "MEDIUM":
            base_level = "MEDIUM" if impact < 0.65 else "HIGH"
        elif h_band == "HIGH":
            base_level = "HIGH" if impact < 0.60 else "VERY_HIGH"
        else:
            base_level = "VERY_HIGH"

        # 6. Safety Floors Override
        water_level_m = dynamic_features.get("water_level_m", 0.0)
        rainfall_mmh = dynamic_features.get("rainfall_1h", 0.0)
        floor_level, floor_reason = self.safety_floors.evaluate_floors(
            water_level_m=water_level_m,
            channel_depth_m=sensor_depth_m,
            rate_of_rise_m_min=rate_of_rise_m_min,
            rainfall_intensity_mmh=rainfall_mmh,
        )

        final_level = base_level
        if floor_level is not None:
            if LEVEL_RANKS[floor_level] > LEVEL_RANKS[base_level]:
                final_level = floor_level

        # 7. Confidence Score C
        confidence = float(np.clip(quality_score * (0.95 if dynamic_features else 0.4), 0.1, 1.0))
        is_abstained = confidence < 0.20

        return {
            "ward_id": ward_id,
            "hazard": round(h_prob, 4),
            "hazard_band": h_band,
            "exposure": round(e_score, 4),
            "vulnerability": round(v_score, 4),
            "impact": round(impact, 4),
            "risk_score": round(risk_score, 4),
            "risk_level": "ABSTAINED" if is_abstained else final_level,
            "safety_floor_triggered": floor_reason,
            "confidence": round(confidence, 3),
            "is_abstained": is_abstained,
            "feature_contributions": h_contributions,
        }
