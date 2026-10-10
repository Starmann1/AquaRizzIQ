"""AquaRizz Data Quality Service (P1-02).

Evaluates telemetry readings and returns explicit DataQualityState flags:
VALID, SUSPECT, STALE, MISSING, CONFLICTING, OUTLIER, INVALID.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from app.db.enums import DataQualityState


class DataQualityEvaluator:
    """Deterministic quality control evaluator for rainfall and water-level telemetry."""

    def __init__(
        self,
        freshness_window_minutes: int = 15,
        stale_threshold_minutes: int = 30,
        max_water_level_m: float = 5.0,
        min_water_level_m: float = 0.0,
        max_rate_of_rise_m_min: float = 0.20,
    ):
        self.freshness_window_min = freshness_window_minutes
        self.stale_threshold_min = stale_threshold_minutes
        self.max_water_level_m = max_water_level_m
        self.min_water_level_m = min_water_level_m
        self.max_rate_of_rise = max_rate_of_rise_m_min

    def evaluate_water_level(
        self,
        current_level_m: float,
        observed_at: datetime,
        as_of_time: Optional[datetime] = None,
        previous_level_m: Optional[float] = None,
        previous_observed_at: Optional[datetime] = None,
        neighbor_levels: Optional[List[float]] = None,
    ) -> Tuple[DataQualityState, str]:
        """Classify a water-level sensor observation.
        
        Returns:
            Tuple of (DataQualityState, reason_description)
        """
        if as_of_time is None:
            as_of_time = datetime.now(timezone.utc)

        # 1. Physical Bounds Check (OUTLIER)
        if current_level_m < self.min_water_level_m or current_level_m > self.max_water_level_m:
            return (
                DataQualityState.OUTLIER,
                f"Reading {current_level_m}m outside physical bounds [{self.min_water_level_m}, {self.max_water_level_m}]m",
            )

        # 2. Freshness Check (STALE / MISSING)
        age_minutes = (as_of_time - observed_at).total_seconds() / 60.0
        if age_minutes < 0:
            return DataQualityState.INVALID, "Observation timestamp is in the future"

        if age_minutes > self.stale_threshold_min:
            return (
                DataQualityState.STALE,
                f"Reading age ({age_minutes:.1f}m) exceeds staleness limit ({self.stale_threshold_min}m)",
            )

        # 3. Dynamic Rate-of-Rise Check (SUSPECT)
        if previous_level_m is not None and previous_observed_at is not None:
            delta_time_min = (observed_at - previous_observed_at).total_seconds() / 60.0
            if delta_time_min > 0:
                rate_of_rise = (current_level_m - previous_level_m) / delta_time_min
                if rate_of_rise > self.max_rate_of_rise:
                    return (
                        DataQualityState.SUSPECT,
                        f"Rate of rise ({rate_of_rise:.3f} m/min) exceeds limit ({self.max_rate_of_rise} m/min)",
                    )

        # 4. Neighbor Agreement Check (CONFLICTING)
        if neighbor_levels and len(neighbor_levels) >= 2:
            avg_neighbor = sum(neighbor_levels) / len(neighbor_levels)
            if abs(current_level_m - avg_neighbor) > 1.5:  # >= 1.5m discrepancy
                return (
                    DataQualityState.CONFLICTING,
                    f"Sensor reading {current_level_m}m conflicts with neighbor average ({avg_neighbor:.2f}m)",
                )

        # Passes all gates
        return DataQualityState.VALID, "Passed all QC gates"

    def evaluate_rainfall(
        self,
        rainfall_mm: float,
        observed_at: datetime,
        as_of_time: Optional[datetime] = None,
    ) -> Tuple[DataQualityState, str]:
        """Classify a rainfall gauge observation."""
        if as_of_time is None:
            as_of_time = datetime.now(timezone.utc)

        if rainfall_mm < 0.0 or rainfall_mm > 300.0:  # Max 300mm/hr cloudburst limit
            return (
                DataQualityState.OUTLIER,
                f"Rainfall {rainfall_mm}mm outside physical bounds [0, 300]mm",
            )

        age_minutes = (as_of_time - observed_at).total_seconds() / 60.0
        if age_minutes < 0:
            return DataQualityState.INVALID, "Observation timestamp is in the future"

        if age_minutes > 60.0:  # Rainfall gauge stale after 1h
            return (
                DataQualityState.STALE,
                f"Rainfall reading age ({age_minutes:.1f}m) exceeds gauge limit (60m)",
            )

        return DataQualityState.VALID, "Passed all rainfall QC gates"
