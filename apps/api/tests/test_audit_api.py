import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_audit_api_list_and_verify(client):
    res = await client.get("/api/v1/audit")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert isinstance(data, list)

    # Verify chain endpoint
    res_verify = await client.post("/api/v1/audit/verify")
    assert res_verify.status_code == 200
    verify_data = res_verify.json()
    assert verify_data["is_valid"] is True
    assert verify_data["records_checked"] == len(data)


@pytest.mark.asyncio
async def test_forecast_api_endpoints(client):
    res = await client.get("/api/v1/forecasts")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "INSUFFICIENT_EVIDENCE"
    assert data["forecast_horizons"] is None
    assert data["is_simulated"] is False

    # Single ward
    res_single = await client.get("/api/v1/forecasts?ward_id=WARD-117")
    assert res_single.status_code == 200
    ward_forecast = res_single.json()
    assert ward_forecast["ward_id"] == "WARD-117"
    assert ward_forecast["status"] == "INSUFFICIENT_EVIDENCE"
    assert ward_forecast["forecast_horizons"] is None


@pytest.mark.asyncio
async def test_recommendations_api_endpoint(client):
    res = await client.get("/api/v1/recommendations")
    assert res.status_code == 200
    recs = res.json()
    assert isinstance(recs, list)
    assert recs == []


@pytest.mark.asyncio
async def test_data_quality_api_endpoint(client):
    res = await client.get("/api/v1/data/quality")
    assert res.status_code == 200
    q = res.json()
    assert "status_distribution" in q
    assert "active_telemetry_sources" in q
    assert q["verified_live_source_available"] is False
    assert q["data_status"] in {"NO_DATA", "SIMULATED_ONLY", "MIXED", "STORED_UNVERIFIED"}
    assert sum(q["status_distribution"].values()) == q["active_sensor_count"]
