"""AquaRizz Exposure and Vulnerability Engines (P1-04).

Implements 4-factor percentile models for Exposure (E) and Vulnerability (V).
"""
from __future__ import annotations

import numpy as np
from typing import Dict, Any


class ExposureEngine:
    """Computes catchment Exposure score E in [0, 1].
    
    Formula: E = 0.40 * pop + 0.15 * bldg + 0.15 * roads + 0.30 * critical_facilities
    Or uses calibrated e_score from ward physical features.
    """

    def compute_exposure(self, ward_features: Dict[str, float]) -> float:
        # 1. Direct precomputed or calibrated exposure score
        if "e_score" in ward_features and ward_features["e_score"] is not None:
            return float(np.clip(ward_features["e_score"], 0.05, 0.95))
        if "exposure" in ward_features and ward_features["exposure"] is not None:
            return float(np.clip(ward_features["exposure"], 0.05, 0.95))

        # 2. Check if specific normalized risk factors are passed (e.g. in tests)
        pop = ward_features.get("population_at_risk")
        bldg = ward_features.get("buildings_at_risk")
        road = ward_features.get("roads_at_risk_km")
        crit = ward_features.get("critical_facilities")

        if any(v is not None for v in (pop, bldg, road, crit)):
            p = pop if pop is not None else 0.5
            b = bldg if bldg is not None else 0.5
            r = road if road is not None else 0.5
            c = crit if crit is not None else 0.5
            e_score = 0.40 * p + 0.15 * b + 0.15 * r + 0.30 * c
            return float(np.clip(e_score, 0.05, 0.95))

        # 3. Derive from physical catchment features if available
        if "pop_density" in ward_features:
            norm_pop = min(1.0, max(0.1, ward_features["pop_density"] / 30000.0))
            norm_road = min(1.0, max(0.1, ward_features.get("road_km", 20.0) / 40.0))
            norm_crit = min(1.0, max(0.1, ward_features.get("crit_facility_count", 5) / 12.0))
            norm_imp = min(1.0, max(0.1, ward_features.get("imperviousness_mean", 0.7)))
            e_score = 0.40 * norm_pop + 0.20 * norm_imp + 0.15 * norm_road + 0.25 * norm_crit
            return float(np.clip(e_score, 0.05, 0.95))

        return 0.5


class VulnerabilityEngine:
    """Computes catchment Vulnerability score V in [0, 1].
    
    Formula: V = 0.40 * sensitive_pop + 0.25 * shelter_gap + 0.20 * egress + 0.15 * density
    Or uses calibrated v_score from ward physical features.
    """

    def compute_vulnerability(self, ward_features: Dict[str, float]) -> float:
        # 1. Direct precomputed or calibrated vulnerability score
        if "v_score" in ward_features and ward_features["v_score"] is not None:
            return float(np.clip(ward_features["v_score"], 0.05, 0.95))
        if "vulnerability" in ward_features and ward_features["vulnerability"] is not None:
            return float(np.clip(ward_features["vulnerability"], 0.05, 0.95))

        # 2. Check if specific normalized risk factors are passed (e.g. in tests)
        sens = ward_features.get("sensitive_population_share") if "sensitive_population_share" in ward_features else ward_features.get("sensitive_pop_share")
        gap = ward_features.get("shelter_distance_gap") if "shelter_distance_gap" in ward_features else ward_features.get("shelter_gap")
        egress = ward_features.get("egress_restriction")
        dens = ward_features.get("housing_density")

        if any(v is not None for v in (sens, gap, egress, dens)):
            s = sens if sens is not None else 0.5
            g = gap if gap is not None else 0.5
            e = egress if egress is not None else 0.5
            d = dens if dens is not None else 0.5
            v_score = 0.40 * s + 0.25 * g + 0.20 * e + 0.15 * d
            return float(np.clip(v_score, 0.05, 0.95))

        # 3. Derive from physical catchment terrain & socioeconomic features
        if "elevation" in ward_features or "elevation_mean" in ward_features:
            elev = ward_features.get("elevation", ward_features.get("elevation_mean", 10.0))
            elev_vuln = min(1.0, max(0.1, 1.0 - elev / 20.0))
            sens_pop = min(1.0, max(0.1, ward_features.get("sensitive_pop_share", 0.20) / 0.35))
            shelter_gap = min(1.0, max(0.1, ward_features.get("shelter_gap", 0.30) / 0.50))
            suscept = min(1.0, max(0.1, ward_features.get("susceptibility_mean", 0.6)))
            v_score = 0.35 * elev_vuln + 0.25 * sens_pop + 0.20 * shelter_gap + 0.20 * suscept
            return float(np.clip(v_score, 0.05, 0.95))

        return 0.5
