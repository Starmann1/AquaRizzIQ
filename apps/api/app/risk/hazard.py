"""AquaRizz Hazard Function (ADR-003, P1-04).

Calibrated logistic sigmoid hazard model:
  z = b0 + sum(w_k * ramp(x_k, lo_k, hi_k))
  H = sigmoid((z - b) / T)
"""
from __future__ import annotations

import math
import numpy as np
from typing import Dict, Any, Tuple


def ramp(x: float, lo: float, hi: float) -> float:
    """Normalize feature x to [0.0, 1.0] across range [lo, hi]. Clamped."""
    if hi <= lo:
        return 0.0
    return float(np.clip((x - lo) / (hi - lo), 0.0, 1.0))


class HazardEngine:
    """Evaluates physical flood hazard probability H in [0, 1]."""

    def __init__(
        self,
        b0: float = -3.5,
        b: float = 0.0,
        temperature: float = 1.0,
        cut_low: float = 0.10,
        cut_medium: float = 0.40,
        cut_high: float = 0.70,
    ):
        self.b0 = b0
        self.b = b
        self.T = max(0.01, temperature)
        self.cut_low = cut_low
        self.cut_medium = cut_medium
        self.cut_high = cut_high

        # Default factor weights & normalization spans
        self.weights = {
            "rainfall_1h": (1.6, 0.0, 75.0),
            "rainfall_3h": (1.2, 0.0, 150.0),
            "water_level_m": (2.2, 0.0, 2.5),
            "rate_of_rise": (1.4, 0.0, 1.0),
            "static_susceptibility": (1.0, 0.0, 1.0),
        }

    def compute_hazard(self, feature_values: Dict[str, float]) -> Tuple[float, str, Dict[str, float]]:
        """Calculate hazard probability H and hazard band.
        
        Returns:
            Tuple of (H_probability, hazard_band_name, feature_contributions)
        """
        z = self.b0
        contributions = {}

        for feat_name, (w, lo, hi) in self.weights.items():
            val = feature_values.get(feat_name, 0.0)
            norm_val = ramp(val, lo, hi)
            term = w * norm_val
            z += term
            contributions[feat_name] = round(term, 4)

        # Sigmoid activation
        scaled_z = (z - self.b) / self.T
        h_prob = 1.0 / (1.0 + math.exp(-scaled_z))
        h_prob = float(np.clip(h_prob, 0.001, 0.999))

        # Band classification
        if h_prob < self.cut_low:
            band = "LOW"
        elif h_prob < self.cut_medium:
            band = "MEDIUM"
        elif h_prob < self.cut_high:
            band = "HIGH"
        else:
            band = "VERY_HIGH"

        return round(h_prob, 4), band, contributions
