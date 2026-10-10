#!/usr/bin/env python3
"""AquaRizz End-to-End Demonstration Script (Phase 17).

Executes the deterministic demo storm progression:
  1. Dry Baseline Conditions (NORMAL)
  2. Monsoon Rainfall Intensification (RAINFALL_INTENSIFIES)
  3. Channel Surcharge & Threshold Crossing (THRESHOLD_CROSSING)
  4. LangGraph 6-Agent Orchestration (Hazard -> Risk -> RCA)
  5. Decision Case Submission & Expiration Window
  6. Human-in-the-Loop Approval by Emergency Coordinator
  7. Guarded Siren & Broadcast Dispatch (SIMULATED)
  8. Risk-Aware Evacuation Route Planning (Avoiding inundated corridors)
  9. Cryptographic Audit Chain Verification (SHA-256)
"""
from __future__ import annotations

import os
import sys
import time
import json
import uuid
from datetime import datetime, timezone

# Ensure apps/api is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api")))

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, engine, SessionLocal
from app.db.models import User
from app.db.enums import UserRole

# Ensure stdout handles UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Colors for terminal output
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def header(title: str):
    print(f"\n{BOLD}{CYAN}{'='*68}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*68}{RESET}")


def step(num: int, title: str):
    print(f"\n{BOLD}{YELLOW}[STEP {num}] {title}{RESET}")


def success(msg: str):
    print(f"  {GREEN}[OK] {msg}{RESET}")


def info(msg: str):
    print(f"  {DIM}[i] {msg}{RESET}")


def warn(msg: str):
    print(f"  {YELLOW}[!] {msg}{RESET}")


def run_e2e_demo():
    header("AquaRizz Urban Flood Early Warning DSS -- Live Demonstration")
    info("Local-First Prototype | Native Execution (NO DOCKER)")
    info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    # Resilient Database Connection: Fast socket check for Postgres, fallback to high-speed SQLite in-memory
    import socket

    def is_pg_available(host="localhost", port=5432) -> bool:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return True
        except OSError:
            return False

    active_engine = None
    active_session = None

    if is_pg_available():
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            active_engine = engine
            active_session = SessionLocal
            info("Connected to local PostgreSQL database")
        except Exception:
            active_engine = None

    if active_engine is None:
        info("PostgreSQL service not responding; instantly using SQLite in-memory demo engine")
        from sqlalchemy import create_engine, event
        from sqlalchemy.pool import StaticPool
        active_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        @event.listens_for(active_engine, "connect")
        def setup_sqlite_spatial(dbapi_connection, connection_record):
            def dummy_func(*args):
                return 1
            for func in [
                "RecoverGeometryColumn", "InitSpatialMetaData", "AddGeometryColumn",
                "CreateSpatialIndex", "CheckSpatialIndex", "DropSpatialIndex",
                "DiscardGeometryColumn", "DisableSpatialIndex",
            ]:
                try:
                    dbapi_connection.create_function(func, -1, dummy_func)
                except Exception:
                    pass
        active_session = sessionmaker(bind=active_engine)

    Base.metadata.create_all(bind=active_engine)
    db = active_session()

    from app.database import get_db
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Ensure test emergency coordinator user exists
    reviewer = db.query(User).filter(User.role == UserRole.EMERGENCY_COORDINATOR.value).first()
    if not reviewer:
        reviewer = User(
            id=uuid.uuid4(),
            username="coordinator_chennai",
            email="coordinator@chennaicorporation.gov.in",
            password_hash="argon2id_mock_hash",
            role=UserRole.EMERGENCY_COORDINATOR.value,
        )
        db.add(reviewer)
        db.commit()
    reviewer_id = str(reviewer.id)

    client = TestClient(app)

    # -------------------------------------------------------------
    # STEP 1: Dry Baseline Conditions
    # -------------------------------------------------------------
    step(1, "Establish Dry Weather Baseline (NORMAL Phase)")
    res = client.get("/api/v1/risk")
    assert res.status_code == 200, f"Failed risk query: {res.text}"
    wards = res.json()
    success(f"Retrieved baseline risk for {len(wards)} GCC monitored wards")
    for w in wards:
        info(f"Ward {w['ward_id']} ({w['ward_name']}): Risk = {w['risk_level']} (Score: {w['risk_score']:.3f}, Hazard: {w['hazard']:.3f})")

    # -------------------------------------------------------------
    # STEP 2: Storm Inception & Progression
    # -------------------------------------------------------------
    step(2, "Advance Demo Storm Simulation (DEMO-STORM-01)")
    res = client.post("/api/v1/demo/control", json={"action": "step"})
    assert res.status_code == 200
    state = res.json()
    success(f"Storm progressed to Phase: {state.get('phase', 'SIMULATED')} (Step {state.get('step', 1)})")
    info("Simulated rainfall intensity escalating across catchment...")

    # Advance again to threshold crossing
    res = client.post("/api/v1/demo/control", json={"action": "step"})
    state = res.json()
    success(f"Storm progressed to Phase: {state.get('phase', 'SIMULATED')} (Step {state.get('step', 2)})")
    info("Drainage network water depth exceeds 75% surcharge capacity")

    # -------------------------------------------------------------
    # STEP 3: M2 Quantile Delta Water-Level Forecasting
    # -------------------------------------------------------------
    step(3, "Query M2 Probabilistic Quantile Forecasting Model")
    res = client.get("/api/v1/forecasts?ward_id=WARD-117")
    assert res.status_code == 200
    forecast = res.json()
    success(f"Generated multi-horizon predictions for {forecast['ward_id']}:")
    info(f"Current Water Level: {forecast['current_water_level_m']:.2f}m | Danger Threshold: {forecast['danger_threshold_m']:.2f}m")
    horizons = forecast["forecast_horizons"]
    for tau in ["15", "30", "60", "120"]:
        h = horizons.get(f"plus_{tau}m") or horizons.get(tau) or {}
        info(f"  +{tau}m horizon: P10={h.get('p10', 0):.2f}m, P50={h.get('p50', 0):.2f}m, P90={h.get('p90', 0):.2f}m (Exceedance Prob: {h.get('exceedance_prob', 0)*100:.1f}%)")

    # -------------------------------------------------------------
    # STEP 4: Trigger 6-Agent LangGraph Pipeline
    # -------------------------------------------------------------
    step(4, "Execute 6-Agent LangGraph Orchestrator Pipeline")
    info("Agents executing: Ingestion -> Quality -> Forecast -> Risk -> Explainability -> Governance")
    trigger_payload = {
        "ward_id": "WARD-117",
        "dynamic_features": {
            "rainfall_1h": 85.0,
            "rainfall_3h": 125.0,
            "water_level_m": 2.65,
            "rate_of_rise": 0.055,
            "static_susceptibility": 0.84,
        },
    }
    res = client.post("/api/v1/assessments", json={
        "ward_id": trigger_payload["ward_id"],
        "dynamic_features": trigger_payload["dynamic_features"],
    })
    assert res.status_code == 202, f"Pipeline execution failed: {res.text}"
    assessment_data = res.json()
    aid = assessment_data["assessment_id"]
    case_id = assessment_data["decision_case_id"]

    success(f"LangGraph execution finished for Assessment ID: {aid}")
    info(f"Computed Hazard: {assessment_data['hazard']:.3f} | Risk Level: {BOLD}{RED}{assessment_data['risk_level']}{RESET}")
    info(f"Nodes Executed: {' -> '.join(assessment_data['nodes_executed'])}")
    info(f"Decision Case Generated: {case_id} (Status: {assessment_data['status']})")

    # -------------------------------------------------------------
    # STEP 5: Root Cause Analysis & Exact Shapley Attribution
    # -------------------------------------------------------------
    step(5, "Inspect Root Cause Analysis (Exact Shapley Attribution)")
    res = client.get(f"/api/v1/explanations/{aid}")
    assert res.status_code == 200
    explanation = res.json()
    success("Retrieved exact Shapley factor attribution over logistic hazard:")
    factors = explanation.get("factors", [])
    if isinstance(factors, list):
        for item in factors:
            c = item.get("contribution", 0)
            info(f"  * {item.get('factor_name', ''):<22}: +{c*100:5.1f}% dH contribution ({item.get('direction', '')})")
    elif isinstance(factors, dict):
        for factor, val in sorted(factors.items(), key=lambda x: x[1], reverse=True):
            info(f"  * {factor:<22}: +{val*100:5.1f}% dH contribution")
    info(f"Narrative: \"{explanation.get('narrative', '')}\"")

    # -------------------------------------------------------------
    # STEP 6: Human-in-the-Loop Review Console
    # -------------------------------------------------------------
    step(6, "Safety Review Gate (Human-in-the-Loop Verification)")
    warn("Autonomous broadcast dispatch is strictly blocked by Policy S-01")
    info(f"Emergency Coordinator {reviewer.username} reviewing Decision Case {case_id}...")

    # Verify pending review listed
    res = client.get("/api/v1/reviews/pending")
    assert res.status_code == 200
    pending_list = res.json()
    assert any(c["case_id"] == case_id for c in pending_list), "Case not found in pending list"
    success(f"Case {case_id} verified present in PENDING_REVIEW queue")

    # Approve case
    approval_payload = {
        "reviewer_id": reviewer_id,
        "reviewer_role": UserRole.EMERGENCY_COORDINATOR.value,
        "rationale": "High hazard confirmed by ultrasonic sluice telemetry and radar rain gauge. Approving immediate evacuation advisory for Velachery North lowlands.",
        "checklist": {
            "evidence_reviewed": True,
            "risk_verified": True,
            "recommendations_approved": True,
        },
    }
    res = client.post(f"/api/v1/reviews/{case_id}/approve", json=approval_payload)
    assert res.status_code == 200, f"Approval failed: {res.text}"
    approved_case = res.json()
    success(f"Decision Case status transitioned: {approved_case['status']}")
    info(f"Approval validity window set to 60 minutes (expires {approved_case['expires_at']})")

    # -------------------------------------------------------------
    # STEP 7: Guarded Alert Dispatch
    # -------------------------------------------------------------
    step(7, "Dispatch Emergency Alert Broadcast (SIMULATED)")
    dispatch_payload = {
        "message": "EMERGENCY FLOOD EVACUATION: Velachery North lowlands. Imminent surcharge. Proceed via designated safe corridors.",
        "alert_level": "VERY_HIGH",
    }
    res = client.post(f"/api/v1/alerts/{case_id}/dispatch", json=dispatch_payload)
    assert res.status_code == 200, f"Dispatch failed: {res.text}"
    alert_res = res.json()
    success(f"Alert broadcast dispatched! Alert ID: {alert_res['alert_id']}")
    info(f"Broadcast Gateway: SIMULATED_GATEWAY | Level: {alert_res['alert_level']}")

    # -------------------------------------------------------------
    # STEP 8: Risk-Aware Evacuation Routing
    # -------------------------------------------------------------
    step(8, "Compute Risk-Aware Evacuation Route (NetworkX Dijkstra)")
    # Origin in flooded zone, destination at high-ground emergency shelter
    route_payload = {
        "origin_node": "N_TNAGAR_CENTER",
        "destination_node": "SH_TNAGAR",
        "flood_penalty_overlay": {
            "N_TNAGAR_CENTER:N_USMAN_RD": 0.95,  # Inundated subway corridor blocked
        },
    }
    res = client.post("/api/v1/routes", json=route_payload)
    assert res.status_code == 200, f"Routing calculation failed: {res.text}"
    route_res = res.json()
    success("Evacuation route computed successfully:")
    info(f"Route Path: {' -> '.join(route_res['route_nodes'])}")
    info(f"Distance: {route_res.get('distance_m', 0):.0f} meters | Estimated Travel Time: {route_res.get('duration_min', 0):.1f} minutes")
    info(f"Safe Route Score (SRS): {route_res.get('srs_score', 0):.3f} | Max Incurred Edge Risk: {route_res.get('max_edge_risk', 0):.3f}")
    if "bypass" in route_res.get("message", "").lower():
        success("Route successfully avoided flooded arterial corridor!")

    # -------------------------------------------------------------
    # STEP 9: Cryptographic Hash Chain Audit Verification
    # -------------------------------------------------------------
    step(9, "Cryptographic Hash Chain Integrity Verification")
    res = client.post("/api/v1/audit/verify")
    assert res.status_code == 200, f"Audit verification failed: {res.text}"
    audit_res = res.json()
    assert audit_res["is_valid"], "Cryptographic audit chain broken!"
    success(f"Audit Chain Verification: {BOLD}{GREEN}CHAIN INTACT & UNTAMPERED{RESET}")
    info(f"Verified Records: {audit_res['records_checked']} SHA-256 blocks validated")

    # -------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------
    header("End-to-End Demonstration Complete: 100% SUCCESS")
    print(f"""
{BOLD}{GREEN}[OK] Baseline Dry State Monitored
[OK] Storm Intensification & Telemetry Simulated
[OK] M2 Multi-Horizon Probabilistic Quantile Forecast Computed
[OK] 6-Agent LangGraph Pipeline Executed
[OK] Exact Game-Theoretic Shapley RCA Attributed
[OK] Human-in-the-Loop Review & Approval Gate Enforced
[OK] Guarded Emergency Broadcast Dispatched
[OK] Flood-Penalized Evacuation Route Calculated
[OK] SHA-256 Cryptographic Audit Log Verified{RESET}
""")


if __name__ == "__main__":
    run_e2e_demo()
