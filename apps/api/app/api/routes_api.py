import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.routing.planner import EvacuationRoutePlanner

router = APIRouter(prefix="/routes", tags=["routing"])
planner = EvacuationRoutePlanner()


class RouteRequest(BaseModel):
    origin_node: str = "N_TNAGAR_CENTER"
    destination_node: str = "SH_TNAGAR"
    flood_penalty_overlay: Optional[Dict[str, float]] = None


@router.post("")
def calculate_route(payload: RouteRequest):
    """Compute risk-penalized evacuation route to nearest safe shelter."""
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

    return res
