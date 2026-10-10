from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query
from app.forecasting.m2_water_level import M2WaterLevelForecastModel

router = APIRouter(prefix="/forecasts", tags=["forecasts"])
model = M2WaterLevelForecastModel()

DEFAULT_WARD_CONDITIONS = {
    "WARD-112": {"current_wl": 2.15, "rainfall_mmh": 65.0, "rate_of_rise": 0.04, "depth": 3.0},
    "WARD-113": {"current_wl": 1.95, "rainfall_mmh": 58.0, "rate_of_rise": 0.035, "depth": 3.0},
    "WARD-117": {"current_wl": 2.65, "rainfall_mmh": 82.0, "rate_of_rise": 0.055, "depth": 3.2},
    "WARD-118": {"current_wl": 2.45, "rainfall_mmh": 74.0, "rate_of_rise": 0.048, "depth": 3.2},
    "WARD-142": {"current_wl": 1.20, "rainfall_mmh": 32.0, "rate_of_rise": 0.012, "depth": 3.0},
}


@router.get("")
def get_forecasts(ward_id: Optional[str] = Query(None)):
    """Retrieve multi-horizon probabilistic water-level forecast for wards."""
    results = []
    targets = [ward_id] if ward_id and ward_id in DEFAULT_WARD_CONDITIONS else list(DEFAULT_WARD_CONDITIONS.keys())

    for wid in targets:
        cond = DEFAULT_WARD_CONDITIONS[wid]
        pred = model.predict_forecasts(
            current_water_level_m=cond["current_wl"],
            rainfall_intensity_mmh=cond["rainfall_mmh"],
            forecast_rain_1h_mm=cond["rainfall_mmh"] * 0.9,
            drain_depth_m=cond["depth"],
            rate_of_rise_m_min=cond["rate_of_rise"],
        )
        results.append({
            "ward_id": wid,
            "current_water_level_m": cond["current_wl"],
            "channel_depth_m": cond["depth"],
            "rate_of_rise_m_min": cond["rate_of_rise"],
            "danger_threshold_m": round(cond["depth"] * 0.85, 2),
            "forecast_horizons": pred.get("predictions", pred),
            "validation_domain": model.validation_domain,
            "model_version": model.version,
            "is_simulated": True,
        })

    if ward_id and results:
        return results[0]
    return results
