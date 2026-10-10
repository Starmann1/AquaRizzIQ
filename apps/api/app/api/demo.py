import os
import yaml
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.hydrology.simulator import CatchmentSimulator

router = APIRouter(prefix="/demo", tags=["demo"])

# Global simulation runner
SCENARIO_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "configs", "scenarios", "demo-storm-01.yaml"
    )
)

_sim_instance: Optional[CatchmentSimulator] = None


def _get_simulator(db: Session) -> CatchmentSimulator:
    global _sim_instance
    if _sim_instance is None:
        timeline = []
        if os.path.exists(SCENARIO_PATH):
            with open(SCENARIO_PATH, "r") as f:
                data = yaml.safe_load(f)
                timeline = data.get("timeline", [])
        _sim_instance = CatchmentSimulator(db, scenario_timeline=timeline)
    else:
        _sim_instance.db = db
        _sim_instance.ingestion.db = db
    return _sim_instance


class DemoControlRequest(BaseModel):
    action: str = "step"  # "step", "reset", "advance_to_peak"


@router.post("/control")
def control_simulation(payload: DemoControlRequest, db: Session = Depends(get_db)):
    """Control the real-time catchment storm simulator."""
    global _sim_instance
    sim = _get_simulator(db)

    if payload.action == "reset":
        _sim_instance = None
        sim = _get_simulator(db)
        return {"status": "RESET", "step": 0, "phase": "NORMAL"}

    elif payload.action == "step":
        step_res = sim.advance_step()
        return {"status": "ADVANCED", **step_res}

    elif payload.action == "advance_to_peak":
        # Advance until threshold crossing / peak phase
        last_res = None
        for _ in range(3):
            last_res = sim.advance_step()
        return {"status": "PEAK_REACHED", **(last_res or {})}

    return {"status": "UNKNOWN_ACTION"}


@router.get("/state")
def get_simulation_state(db: Session = Depends(get_db)):
    """Retrieve current storm simulation step and telemetry gauges."""
    sim = _get_simulator(db)
    step_idx = max(0, sim.current_step - 1)
    phase_name = "NORMAL"
    if sim.timeline and step_idx < len(sim.timeline):
        phase_name = sim.timeline[step_idx].get("phase", "NORMAL")

    return {
        "scenario_id": "DEMO-STORM-01",
        "current_step": sim.current_step,
        "phase": phase_name,
        "water_levels": sim.current_levels,
        "is_simulated": True,
    }
