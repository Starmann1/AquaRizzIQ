import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_risk_overview(client: AsyncClient):
    resp = await client.get("/api/v1/risk")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    assert any(w["ward_id"] == "WARD-112" for w in data)


@pytest.mark.asyncio
async def test_get_zones(client: AsyncClient):
    resp = await client.get("/api/v1/zones")
    assert resp.status_code == 200
    geojson = resp.json()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) > 0


@pytest.mark.asyncio
async def test_trigger_assessment_and_explain(client: AsyncClient):
    post_resp = await client.post(
        "/api/v1/assessments",
        json={"ward_id": "WARD-112"},
    )
    assert post_resp.status_code == 202
    data = post_resp.json()
    assert "assessment_id" in data
    assert data["status"] in ("PENDING_REVIEW", "ABSTAINED")

    # Get explanation
    aid = data["assessment_id"]
    exp_resp = await client.get(f"/api/v1/explanations/{aid}")
    assert exp_resp.status_code == 200
    exp_data = exp_resp.json()
    assert exp_data["method"] == "EXACT_SHAPLEY_COALITIONS"
    assert len(exp_data["factors"]) > 0


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


@pytest.mark.asyncio
async def test_demo_control_api(client: AsyncClient):
    resp = await client.post(
        "/api/v1/demo/control",
        json={"action": "step"},
    )
    assert resp.status_code == 200
    step_data = resp.json()
    assert step_data["status"] == "ADVANCED"
    assert "water_levels" in step_data
