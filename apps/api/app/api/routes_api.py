from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.routing.planner import EvacuationRoutePlanner

router = APIRouter(prefix="/routes", tags=["routing"])
planner = EvacuationRoutePlanner()


class RouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin_node: str = "N_TNAGAR_CENTER"
    destination_node: str = "SH_TNAGAR"
    flood_penalty_overlay: Optional[dict[str, float]] = None

    @field_validator("flood_penalty_overlay")
    @classmethod
    def validate_overlay(cls, overlay: Optional[dict[str, float]]) -> Optional[dict[str, float]]:
        if overlay is None:
            return None
        for edge, risk in overlay.items():
            if edge.count(":") != 1 or not all(part.strip() for part in edge.split(":")):
                raise ValueError("Overlay edge keys must use 'origin:destination' format")
            if not 0.0 <= risk <= 1.0:
                raise ValueError("Illustrative edge risk must be between 0 and 1")
        return overlay


@router.post("")
def calculate_route(payload: RouteRequest):
    """Calculate a path in the prototype graph; this is not evacuation guidance."""
    # Convert overlay if provided
    overlay = {}
    if payload.flood_penalty_overlay:
        for k, v in payload.flood_penalty_overlay.items():
            if ":" in k:
                u, w = k.split(":")
                overlay[(u, w)] = v

    res = planner.plan_route(
        origin_node=payload.origin_node,
        destination_node=payload.destination_node,
        hazard_risk_overlay=overlay,
    )

    if res["status"] == "INVALID_NODES":
        raise HTTPException(status_code=400, detail=res["message"])

    return {
        **res,
        "is_simulated": True,
        "prototype_only": True,
        "network_basis": "SYNTHETIC_DEMONSTRATION_GRAPH",
        "safety_decision": "NOT_EVALUATED",
        "limitations": [
            "Road geometry, travel times, hazard values, and destination availability are illustrative fixtures.",
            "This result is not a safe-route determination and must not guide evacuation.",
        ],
    }
