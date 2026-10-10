"""AquaRizz Exposure and Vulnerability Engines (P1-04).

Implements 4-factor percentile models for Exposure (E) and Vulnerability (V).
"""
from __future__ import annotations

import numpy as np
from typing import Dict, Any


class ExposureEngine:
    """Computes catchment Exposure score E in [0, 1].
    
    Formula: E = 0.40 * pop + 0.15 * bldg + 0.15 * roads + 0.30 * critical_facilities
    """

    def compute_exposure(self, ward_features: Dict[str, float]) -> float:
        pop = ward_features.get("population_at_risk", 0.5)
        bldg = ward_features.get("buildings_at_risk", 0.5)
        road = ward_features.get("roads_at_risk_km", 0.5)
        crit = ward_features.get("critical_facilities", 0.5)

        e_score = 0.40 * pop + 0.15 * bldg + 0.15 * road + 0.30 * crit
        return float(np.clip(e_score, 0.05, 0.95))


class VulnerabilityEngine:
    """Computes catchment Vulnerability score V in [0, 1].
    
    Formula: V = 0.40 * sensitive_pop + 0.25 * shelter_gap + 0.20 * egress + 0.15 * density
    """

    def compute_vulnerability(self, ward_features: Dict[str, float]) -> float:
        sens = ward_features.get("sensitive_population_share", 0.5)
        gap = ward_features.get("shelter_distance_gap", 0.5)
        egress = ward_features.get("egress_restriction", 0.5)
        dens = ward_features.get("housing_density", 0.5)

        v_score = 0.40 * sens + 0.25 * gap + 0.20 * egress + 0.15 * dens
        return float(np.clip(v_score, 0.05, 0.95))
