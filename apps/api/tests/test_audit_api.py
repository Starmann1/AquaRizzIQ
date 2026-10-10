import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_audit_api_list_and_verify(client):
    res = await client.get("/api/v1/audit")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Verify chain endpoint
    res_verify = await client.post("/api/v1/audit/verify")
    assert res_verify.status_code == 200
    verify_data = res_verify.json()
    assert "is_valid" in verify_data
    assert verify_data["is_valid"] is True


@pytest.mark.asyncio
async def test_forecast_api_endpoints(client):
    # All wards
    res = await client.get("/api/v1/forecasts")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Single ward
    res_single = await client.get("/api/v1/forecasts?ward_id=WARD-117")
    assert res_single.status_code == 200
    ward_forecast = res_single.json()
    assert ward_forecast["ward_id"] == "WARD-117"
    assert "forecast_horizons" in ward_forecast
    assert "plus_15m" in ward_forecast["forecast_horizons"]


@pytest.mark.asyncio
async def test_recommendations_api_endpoint(client):
    res = await client.get("/api/v1/recommendations")
    assert res.status_code == 200
    recs = res.json()
    assert isinstance(recs, list)
    assert len(recs) >= 1
    assert "recommendation_type" in recs[0]
    assert "priority" in recs[0]


@pytest.mark.asyncio
async def test_data_quality_api_endpoint(client):
    res = await client.get("/api/v1/data/quality")
    assert res.status_code == 200
    q = res.json()
    assert "status_distribution" in q
    assert "active_telemetry_sources" in q
    assert q["status_distribution"]["VALID"] >= 1
