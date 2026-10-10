"""AquaRizz Scenario Simulation Runner (P1-15, P2-04).

Drives deterministic rainfall and sensor water-level evolution through time
and submits observations via standard IngestionService interfaces.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.hydrology.reservoir import LinearReservoirSensorModel
from app.schemas.data import RainfallObservationCreate, SensorObservationCreate
from app.services.ingestion import IngestionService


class CatchmentSimulator:
    """Deterministic simulation engine for demonstration and testing."""

    def __init__(self, db: Session, scenario_timeline: List[Dict[str, Any]] | None = None):
        self.db = db
        self.ingestion = IngestionService(db)
        self.current_step = 0
        self.timeline = scenario_timeline or []
        
        # Initialize standard simulated sensors
        self.sensor_models = {
            "SIM-SWD-W112-001": LinearReservoirSensorModel("SIM-SWD-W112-001", depth_m=2.5, normal_level_m=0.20, dist_to_coast_km=4.5),
            "SIM-SWD-W113-001": LinearReservoirSensorModel("SIM-SWD-W113-001", depth_m=3.0, normal_level_m=0.30, dist_to_coast_km=5.2),
            "SIM-SWD-W117-001": LinearReservoirSensorModel("SIM-SWD-W117-001", depth_m=2.8, normal_level_m=0.25, dist_to_coast_km=3.8),
            "SIM-SWD-W118-001": LinearReservoirSensorModel("SIM-SWD-W118-001", depth_m=3.5, normal_level_m=0.40, dist_to_coast_km=3.2),
            "SIM-SWD-W142-001": LinearReservoirSensorModel("SIM-SWD-W142-001", depth_m=4.0, normal_level_m=0.50, dist_to_coast_km=1.2),
        }
        self.current_levels = {sid: m.normal_level_m for sid, m in self.sensor_models.items()}

    def advance_step(self, as_of: datetime | None = None) -> Dict[str, Any]:
        """Advance simulation by one scenario step and ingest observations."""
        if as_of is None:
            as_of = datetime.now(timezone.utc)

        if not self.timeline:
            rain_mmh = 45.0
            phase_name = "SIMULATED_STORM"
        else:
            step_idx = min(self.current_step, len(self.timeline) - 1)
            step_data = self.timeline[step_idx]
            rain_mmh = step_data.get("rainfall_intensity_mmh", 30.0)
            phase_name = step_data.get("phase", "UNKNOWN")

        # Ingest rainfall observations for stations
        rain_records = [
            RainfallObservationCreate(
                station_id="STN-W112",
                observed_at=as_of,
                rainfall_mm=round(rain_mmh, 1),
                accumulation_1h=round(rain_mmh * 0.8, 1),
                is_simulated=True,
            ),
            RainfallObservationCreate(
                station_id="STN-W117",
                observed_at=as_of,
                rainfall_mm=round(rain_mmh * 1.1, 1),
                accumulation_1h=round(rain_mmh * 0.9, 1),
                is_simulated=True,
            ),
        ]
        self.ingestion.ingest_rainfall_batch(rain_records)

        # Update water levels and ingest sensor observations
        water_records = []
        elapsed_hours = (self.current_step * 5.0) / 60.0

        for sid, model in self.sensor_models.items():
            curr_h = self.current_levels[sid]
            next_h = model.step(curr_h, rainfall_intensity_mmh=rain_mmh, time_hours=elapsed_hours, dt_minutes=5.0)
            self.current_levels[sid] = next_h

            water_records.append(
                SensorObservationCreate(
                    sensor_id=sid,
                    observed_at=as_of,
                    water_level_m=next_h,
                    is_simulated=True,
                )
            )

        self.ingestion.ingest_water_level_batch(water_records)
        self.current_step += 1

        return {
            "step": self.current_step - 1,
            "phase": phase_name,
            "rainfall_intensity_mmh": rain_mmh,
            "water_levels": self.current_levels.copy(),
            "timestamp": as_of.isoformat(),
        }
