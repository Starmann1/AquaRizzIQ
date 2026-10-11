from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.demo_scenario import DemoScenarioService, get_demo_scenario_service


router = APIRouter(prefix="/demo", tags=["demo"])


class DemoControlRequest(BaseModel):
    action: Literal["step", "reset", "advance_to_peak", "set_step"]
    step: int | None = Field(default=None, ge=0)


@router.post("/control")
def control_simulation(payload: DemoControlRequest):
    """Control the deterministic, explicitly simulated demonstration scenario."""
    service = get_demo_scenario_service()
    try:
        result = service.control(payload.action, payload.step)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@router.get("/state")
def get_simulation_state():
    """Return the current scenario frame and its prototype-only calculations."""
    return get_demo_scenario_service().state()
