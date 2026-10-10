"""AquaRizz Hydrological Runoff Estimation via SCS Curve Number (P1-15).

Calculates surface runoff depth Q (mm) from rainfall depth P (mm) and built-up fraction.
Clearly labeled as a prototype hydrological proxy, NOT a calibrated 2D hydraulic model.
"""
from __future__ import annotations


class SCSCurveNumberModel:
    """Soil Conservation Service (SCS) Curve Number runoff model."""

    @staticmethod
    def calculate_curve_number(built_fraction: float) -> float:
        """Derive CN from impervious built-up fraction.
        
        Chennai urban soil base CN ~ 60 (Type B/C soils), rising to 98 in full built-up.
        Formula: CN = 60 + 38 * built_fraction
        """
        clamped_built = max(0.0, min(1.0, built_fraction))
        return 60.0 + 38.0 * clamped_built

    @classmethod
    def calculate_runoff_depth_mm(
        cls, rainfall_depth_mm: float, built_fraction: float
    ) -> float:
        """Calculate runoff depth Q (mm) for a given cumulative precipitation P (mm).
        
        Q = (P - Ia)^2 / (P - Ia + S) for P > Ia, else 0.0
        Where S = 25400/CN - 254 (in mm), and initial abstraction Ia = 0.2 * S.
        """
        if rainfall_depth_mm <= 0.0:
            return 0.0

        cn = cls.calculate_curve_number(built_fraction)
        s = (25400.0 / cn) - 254.0
        ia = 0.2 * s

        if rainfall_depth_mm <= ia:
            return 0.0

        p_minus_ia = rainfall_depth_mm - ia
        q = (p_minus_ia * p_minus_ia) / (p_minus_ia + s)
        return float(max(0.0, q))
