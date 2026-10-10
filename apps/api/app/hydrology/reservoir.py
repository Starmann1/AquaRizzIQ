"""AquaRizz Reservoir Routing & Water-Level Evolution Proxy (P1-15).

Models catchment drainage channel water-level dynamics h(t+1):
  h(t+1) = clip(h(t) + dt * (inflow - outflow), 0, max_depth)
"""
from __future__ import annotations

import math
import numpy as np


class LinearReservoirSensorModel:
    """Simulates water-level evolution in a stormwater drainage node or canal gauge."""

    def __init__(
        self,
        sensor_id: str,
        depth_m: float = 3.0,
        normal_level_m: float = 0.25,
        alpha_inflow: float = 0.035,
        beta_outflow: float = 0.045,
        blockage_ratio: float = 0.15,
        dist_to_coast_km: float = 4.0,
    ):
        self.sensor_id = sensor_id
        self.depth_m = depth_m
        self.normal_level_m = normal_level_m
        self.alpha = alpha_inflow
        self.beta = beta_outflow
        self.blockage = blockage_ratio
        self.dist_to_coast = dist_to_coast_km

    def step(
        self,
        current_water_level_m: float,
        rainfall_intensity_mmh: float,
        time_hours: float,
        dt_minutes: float = 1.0,
        injected_fault: str | None = None,
    ) -> float:
        """Advance water level by dt minutes given current rain and tidal conditions.
        
        Args:
            current_water_level_m: Current depth reading (m)
            rainfall_intensity_mmh: Effective rain intensity (mm/h)
            time_hours: Simulation elapsed time in hours (for semidiurnal tide calculation)
            dt_minutes: Timestep in minutes
            injected_fault: Optional fault scenario ('SPIKE', 'STUCK', 'DROPOUT')
        """
        # Handle fault injection
        if injected_fault == "STUCK":
            return current_water_level_m
        if injected_fault == "SPIKE":
            return float(min(self.depth_m * 1.1, current_water_level_m + 0.9))

        # Tidal backwater reduction factor for coastal drains (< 6km from Bay of Bengal)
        # Semidiurnal tide: period ~ 12.42 hours
        tide_factor = 1.0
        if self.dist_to_coast < 6.0:
            coast_attenuation = max(0.0, 1.0 - (self.dist_to_coast / 6.0))
            tide_sin = math.sin(2.0 * math.pi * time_hours / 12.42)
            tide_factor = max(0.4, 1.0 - 0.35 * coast_attenuation * max(0.0, tide_sin))

        # Inflow: proportional to rainfall intensity
        inflow_rate_m_min = (rainfall_intensity_mmh / 60.0) * self.alpha

        # Outflow: gravity discharge throttled by drain blockage and tidal backwater
        effective_head = max(0.0, current_water_level_m - self.normal_level_m)
        outflow_rate_m_min = (
            self.beta * effective_head * (1.0 - self.blockage) * tide_factor
        )

        # Update water level
        delta_h = (inflow_rate_m_min - outflow_rate_m_min) * dt_minutes
        new_level = current_water_level_m + delta_h

        # Physical clamping between minimum baseflow and surcharge overtopping limit (1.15 * depth)
        clamped_level = float(np.clip(new_level, self.normal_level_m * 0.8, self.depth_m * 1.15))
        return round(clamped_level, 3)
