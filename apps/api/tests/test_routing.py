import pytest
from app.routing.planner import EvacuationRoutePlanner


def test_evacuation_routing_clear_conditions():
    planner = EvacuationRoutePlanner()
    # Route from Panagal Park (T. Nagar Center) to T. Nagar Relief Hall
    result = planner.plan_route(
        origin_node="N_TNAGAR_CENTER",
        destination_node="SH_TNAGAR",
    )

    assert result["status"] == "ROUTE_FOUND"
    assert result["route_nodes"] == ["N_TNAGAR_CENTER", "SH_TNAGAR"]
    assert result["distance_m"] == 450.0
    assert result["duration_s"] > 0.0
    assert result["srs_score"] > 60.0
    assert result["is_simulated"] is True
    assert result["safety_decision"] == "NOT_EVALUATED"


def test_evacuation_routing_blocked_road_avoidance():
    planner = EvacuationRoutePlanner()

    # Apply flood risk penalty >= 0.90 to Usman Road Subway
    hazard_overlay = {
        ("N_TNAGAR_CENTER", "N_USMAN_RD"): 0.95,  # Road flooded and blocked
    }

    # Route from T. Nagar Center to Mambalam Relief Camp
    # Must divert via alternative path or find valid route
    res_diverted = planner.plan_route(
        origin_node="N_TNAGAR_CENTER",
        destination_node="SH_MAMBALAM",
        hazard_risk_overlay=hazard_overlay,
    )

    # Usman road edge must NOT be in route
    if res_diverted["status"] == "ROUTE_FOUND":
        nodes = res_diverted["route_nodes"]
        for i in range(len(nodes) - 1):
            edge = (nodes[i], nodes[i + 1])
            assert edge != ("N_TNAGAR_CENTER", "N_USMAN_RD")


def test_no_safe_route_fallback():
    planner = EvacuationRoutePlanner()

    # Block all egress edges from N_TNAGAR_CENTER
    hazard_overlay = {
        ("N_TNAGAR_CENTER", "SH_TNAGAR"): 0.95,
        ("N_TNAGAR_CENTER", "N_USMAN_RD"): 0.95,
        ("N_TNAGAR_CENTER", "N_ANNA_SALAI"): 0.95,
    }

    res_blocked = planner.plan_route(
        origin_node="N_TNAGAR_CENTER",
        destination_node="SH_TNAGAR",
        hazard_risk_overlay=hazard_overlay,
    )

    assert res_blocked["status"] == "NO_PATH_FOUND"
    assert "synthetic demonstration graph" in res_blocked["message"]
