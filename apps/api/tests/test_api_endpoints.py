import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
from uuid import uuid4

from app.db.models import Assessment


@pytest.mark.asyncio
async def test_get_risk_overview(client: AsyncClient):
    resp = await client.get("/api/v1/risk")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    assert any(w["ward_id"] == "WARD-112" for w in data)
    assert all(w["risk_level"] == "INSUFFICIENT_EVIDENCE" for w in data)
    assert all(w["risk_score"] is None and w["is_abstained"] for w in data)
    assert all(w["abstention_reason"] for w in data)


@pytest.mark.asyncio
async def test_request_validation_uses_problem_details_and_request_id(client: AsyncClient):
    response = await client.post("/api/v1/demo/control", json={"action": "not-a-demo-action"})

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    problem = response.json()
    assert problem["title"] == "Request validation failed"
    assert problem["status"] == 422
    assert problem["request_id"]
    assert problem["errors"]


@pytest.mark.asyncio
async def test_http_exception_uses_problem_details(client: AsyncClient):
    response = await client.post("/api/v1/demo/control", json={"action": "set_step", "step": 99})

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["title"] == "Unprocessable Entity"
    assert response.json()["request_id"]


@pytest.mark.asyncio
async def test_get_zones(client: AsyncClient):
    resp = await client.get("/api/v1/zones")
    assert resp.status_code == 200
    geojson = resp.json()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) > 0
    assert len(geojson["features"]) == 200
    assert len(geojson["zone_features"]) == 15
    assert geojson["dataset_metadata"]["zone_source_id"] == "gcc-zones-2022"
    assert geojson["dataset_metadata"]["status"] in {
        "SOURCE_VERIFIED_BOUNDARY", "UNVERIFIED_FIXTURE"
    }


@pytest.mark.asyncio
async def test_trigger_assessment_and_explain(client: AsyncClient):
    post_resp = await client.post(
        "/api/v1/assessments",
        json={"ward_id": "WARD-112"},
    )
    assert post_resp.status_code == 202
    data = post_resp.json()
    assert data["status"] == "INSUFFICIENT_EVIDENCE"
    assert data["risk_level"] == "INSUFFICIENT_EVIDENCE"
    assert data["risk_score"] is None
    assert data["confidence"] is None
    assert data["is_abstained"] is True
    assert data["is_simulated"] is False
    assert data["decision_case_id"] is None
    assert "current rainfall" in data["reason"]


@pytest.mark.asyncio
async def test_forecasts_abstain_without_verified_observations(client: AsyncClient):
    response = await client.get("/api/v1/forecasts?ward_id=WARD-112")
    assert response.status_code == 200
    data = response.json()
    assert data["ward_id"] == "WARD-112"
    assert data["status"] == "INSUFFICIENT_EVIDENCE"
    assert data["forecast_horizons"] is None
    assert data["is_simulated"] is False


@pytest.mark.asyncio
async def test_historical_flood_layer_is_source_attributed_and_gcc_clipped(client: AsyncClient):
    response = await client.get("/api/v1/layers/historical-floods/2015")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1212
    assert data["dataset_metadata"]["status"] == "HISTORICAL_OBSERVATION"
    assert data["dataset_metadata"]["source_id"] == "chennai-2015-nrsc-inundation"
    assert data["dataset_metadata"]["feature_timestamp_available"] is False
    assert data["dataset_metadata"]["repair_count"] == 0


@pytest.mark.asyncio
async def test_rainfall_layer_exposes_empty_observation_coverage(client: AsyncClient):
    response = await client.get("/api/v1/layers/rainfall/2015")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert data["features"] == []
    assert data["dataset_metadata"]["status"] == "NO_VALID_OBSERVATIONS"
    assert data["dataset_metadata"]["valid_observation_count"] == 0
    assert data["dataset_metadata"]["missing_observation_count"] == 365


@pytest.mark.asyncio
async def test_tnsmart_rainfall_layer_is_source_attributed_and_single_station(client: AsyncClient):
    response = await client.get("/api/v1/layers/rainfall/tnsmart/2026-10-11")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 62
    nungambakkam = next(
        feature for feature in data["features"]
        if feature["properties"]["station_name"].casefold() == "chennai nungambakkam"
    )
    assert nungambakkam["geometry"]["coordinates"] == [80.25, 13.0667]
    assert nungambakkam["properties"]["rainfall_mm"] == 0.0
    assert nungambakkam["properties"]["observation_date"] == "2026-10-11"
    assert nungambakkam["properties"]["units"] == "mm"
    assert "datum is unspecified" in nungambakkam["properties"]["coordinate_note"].lower()
    assert data["dataset_metadata"]["station_count_chennai"] == 63
    assert data["dataset_metadata"]["station_count_inside_gcc"] == 62
    assert data["dataset_metadata"]["positive_rainfall_station_count"] == 6
    assert data["dataset_metadata"]["status"] == "SOURCE_RENDERED_DAILY_STATION_OBSERVATIONS"
    assert data["dataset_metadata"]["risk_input_eligible"] is False
    assert "not a live feed" in data["dataset_metadata"]["limitation"].lower()


@pytest.mark.asyncio
async def test_explanation_abstains_for_legacy_simulated_assessment(client, db_session):
    assessment_id = uuid4()
    db_session.add(
        Assessment(
            id=assessment_id,
            ward_id="WARD-112",
            assessed_at=datetime.now(timezone.utc),
            status="APPROVED",
            hazard=0.91,
            hazard_band="HIGH",
            exposure=0.82,
            vulnerability=0.75,
            impact=0.83,
            risk_score=0.88,
            risk_level="HIGH",
            confidence=0.96,
            is_simulated=True,
            input_snapshot={"rainfall_1h": 65.0, "water_level_m": 2.15},
        )
    )
    db_session.commit()

    response = await client.get(f"/api/v1/explanations/{assessment_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "INSUFFICIENT_EVIDENCE"
    assert data["is_abstained"] is True
    assert data["factors"] == []
    assert data["narrative"] is None
    assert data["evidence_ids"] == []
    assert data["confidence"] is None
    assert data["is_simulated"] is True
    assert "source-verified" in data["reason"]


@pytest.mark.asyncio
async def test_calculate_route_api(client: AsyncClient):
    resp = await client.post(
        "/api/v1/routes",
        json={
            "origin_node": "N_TNAGAR_CENTER",
            "destination_node": "SH_TNAGAR",
        },
    )
    assert resp.status_code == 200
    route_data = resp.json()
    assert route_data["status"] == "ROUTE_FOUND"
    assert "srs_score" in route_data
    assert route_data["is_simulated"] is True
    assert route_data["prototype_only"] is True
    assert route_data["safety_decision"] == "NOT_EVALUATED"


@pytest.mark.asyncio
async def test_route_api_rejects_out_of_range_hazard_overlay(client: AsyncClient):
    response = await client.post(
        "/api/v1/routes",
        json={"flood_penalty_overlay": {"N_TNAGAR_CENTER:N_USMAN_RD": 1.2}},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_route_api_rejects_malformed_hazard_overlay_key(client: AsyncClient):
    response = await client.post(
        "/api/v1/routes",
        json={"flood_penalty_overlay": {"N_TNAGAR_CENTER": 0.5}},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_quality_endpoint_exposes_all_quality_use_states(client: AsyncClient):
    response = await client.get("/api/v1/data/quality")
    assert response.status_code == 200
    data = response.json()
    policy = {row["state"]: row for row in data["quality_use_policy"]}
    assert set(policy) == {"VALID", "SUSPECT", "STALE", "MISSING", "CONFLICTING", "OUTLIER", "INVALID"}
    assert policy["VALID"]["critical_input"] == "ACCEPT"
    assert policy["SUSPECT"]["critical_input"] == "ABSTAIN"
    assert policy["INVALID"]["critical_input"] == "REJECT"


@pytest.mark.asyncio
async def test_demo_control_api(client: AsyncClient):
    from app.services.demo_scenario import reset_demo_scenario_service

    reset_demo_scenario_service()
    initial = await client.get("/api/v1/demo/state")
    assert initial.status_code == 200
    assert initial.json()["current_step"] == 0
    assert initial.json()["data_classification"] == "SIMULATED_SCENARIO"
    assert initial.json()["assessment"]["risk_score"] is not None
    assert initial.json()["assessment"]["confidence"] is None
    assert len(initial.json()["fixture_sha256"]) == 64
    assert initial.json()["assessment"]["fixture_sha256"] == initial.json()["fixture_sha256"]
    assert initial.json()["assessment"]["recommendations"][0]["scope"] == "SIMULATED_EXERCISE_ONLY"

    resp = await client.post(
        "/api/v1/demo/control",
        json={"action": "step"},
    )
    assert resp.status_code == 200
    step_data = resp.json()
    assert step_data["status"] == "ADVANCED"
    assert step_data["current_step"] == 1
    assert step_data["assessment"]["is_simulated"] is True
    assert step_data["assessment"]["status"] == "SIMULATED_SCENARIO_ONLY"
    assert step_data["assessment"]["risk_score"] > initial.json()["assessment"]["risk_score"]

    peak = await client.post(
        "/api/v1/demo/control",
        json={"action": "advance_to_peak"},
    )
    assert peak.status_code == 200
    assert peak.json()["current_step"] == 3
    assert peak.json()["assessment"]["summary"]["phase"] == "SIMULATED_HAZARD_PEAK"

    reset = await client.post(
        "/api/v1/demo/control",
        json={"action": "reset"},
    )
    assert reset.status_code == 200
    assert reset.json()["current_step"] == 0

    live_risk = await client.get("/api/v1/risk/WARD-117")
    assert live_risk.status_code == 200
    assert live_risk.json()["risk_level"] == "INSUFFICIENT_EVIDENCE"
    assert live_risk.json()["risk_score"] is None
