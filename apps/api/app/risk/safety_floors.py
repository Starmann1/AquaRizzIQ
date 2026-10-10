"""AquaRizz Safety Floors (F1, F2, F3) (P1-04, ADR-004).

Deterministic physical triggers that override statistical hazard/risk bands.
"""
from __future__ import annotations

from typing import Dict, Any, Tuple, Optional


class SafetyFloorEvaluator:
    """Evaluates deterministic physical safety floors."""

    def __init__(
        self,
        f1_fill_thresh: float = 0.85,
        f2_fill_thresh: float = 0.60,
        f2_rise_thresh: float = 0.50,  # cm/min = 0.005 m/min
        f3_rain_thresh: float = 100.0, # mm/h
    ):
        self.f1_fill = f1_fill_thresh
        self.f2_fill = f2_fill_thresh
        self.f2_rise = f2_rise_thresh
        self.f3_rain = f3_rain_thresh

    def evaluate_floors(
        self,
        water_level_m: float,
        channel_depth_m: float,
        rate_of_rise_m_min: float,
        rainfall_intensity_mmh: float,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Check safety floors F1-F3.
        
        Returns:
            Tuple of (overridden_floor_level, trigger_reason) or (None, None)
        """
        fill_ratio = water_level_m / max(0.1, channel_depth_m)
        rate_of_rise_cm_min = rate_of_rise_m_min * 100.0

        # F1: Channel fill >= 85% -> HIGH floor
        if fill_ratio >= self.f1_fill:
            return "HIGH", f"F1: Sensor capacity fill ({fill_ratio:.1%}) >= {self.f1_fill:.0%}"

        # F2: Channel fill >= 60% AND rising fast >= 0.5 cm/min -> MEDIUM floor
        if fill_ratio >= self.f2_fill and rate_of_rise_cm_min >= self.f2_rise:
            return (
                "MEDIUM",
                f"F2: Sensor fill ({fill_ratio:.1%}) >= {self.f2_fill:.0%} with rapid rise ({rate_of_rise_cm_min:.2f} cm/min)",
            )

        # F3: Rainfall intensity >= 100 mm/h -> MEDIUM floor
        if rainfall_intensity_mmh >= self.f3_rain:
            return (
                "MEDIUM",
                f"F3: Cloudburst rain intensity ({rainfall_intensity_mmh:.1f} mm/h) >= {self.f3_rain:.0f} mm/h",
            )

        return None, None
