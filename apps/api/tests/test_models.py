import pytest
from app.forecasting.m1_susceptibility import M1SusceptibilityModel
from app.forecasting.m2_water_level import M2WaterLevelForecastModel


def test_m1_susceptibility_predictions():
    m1 = M1SusceptibilityModel()

    # Low-lying high-impervious cell (high susceptibility)
    feats_high = {
        "elevation": 2.0,
        "slope": 0.3,
        "hand": 0.8,
        "twi": 11.5,
        "drain_proximity": 0.85,
        "imperviousness": 0.85,
        "hist_flood_freq": 0.75,
    }
    s_high = m1.predict_susceptibility(feats_high)

    # Elevated permeable cell (low susceptibility)
    feats_low = {
        "elevation": 12.0,
        "slope": 2.2,
        "hand": 6.5,
        "twi": 5.0,
        "drain_proximity": 0.15,
        "imperviousness": 0.30,
        "hist_flood_freq": 0.10,
    }
    s_low = m1.predict_susceptibility(feats_low)

    assert 0.0 < s_low < s_high < 1.0
    assert m1.validation_domain == "SYNTHETIC"
    assert m1.readiness_status == "PROTOTYPE"


def test_m2_water_level_forecast_intervals():
    m2 = M2WaterLevelForecastModel()

    res = m2.predict_forecasts(
        current_water_level_m=1.20,
        rainfall_intensity_mmh=60.0,
        forecast_rain_1h_mm=75.0,
        drain_depth_m=3.0,
        rate_of_rise_m_min=0.04,
    )

    preds = res["predictions"]
    assert "plus_15m" in preds
    assert "plus_30m" in preds
    assert "plus_60m" in preds
    assert "plus_120m" in preds

    p15 = preds["plus_15m"]
    p60 = preds["plus_60m"]

    # Quantile ordering: P10 <= P50 <= P90
    assert p15["p10"] <= p15["p50"] <= p15["p90"]
    assert p60["p10"] <= p60["p50"] <= p60["p90"]

    # Monotonic interval widening: spread at +60m > spread at +15m
    assert p60["interval_width"] > p15["interval_width"]
    assert res["validation_domain"] == "SYNTHETIC"
