from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import Ward, Assessment, SensorObservation, RainfallObservation
from app.risk.engine import RiskEngine

router = APIRouter(prefix="/risk", tags=["risk"])
risk_engine = RiskEngine()

# Reference ward priors for demo
WARD_PROFILES = {
    "WARD-112": {
        "name": "T. Nagar",
        "zone": "Zone 10 - Kodambakkam",
        "static": {"population_at_risk": 0.82, "critical_facilities": 0.78, "sensitive_population_share": 0.65, "shelter_distance_gap": 0.55, "housing_density": 0.85},
        "dyn": {"rainfall_1h": 45.0, "rainfall_3h": 70.0, "water_level_m": 1.45, "rate_of_rise": 0.03, "static_susceptibility": 0.72},
        "sensor_depth": 2.5,
    },
    "WARD-113": {
        "name": "West Mambalam",
        "zone": "Zone 10 - Kodambakkam",
        "static": {"population_at_risk": 0.79, "critical_facilities": 0.70, "sensitive_population_share": 0.68, "shelter_distance_gap": 0.60, "housing_density": 0.82},
        "dyn": {"rainfall_1h": 40.0, "rainfall_3h": 65.0, "water_level_m": 1.60, "rate_of_rise": 0.04, "static_susceptibility": 0.76},
        "sensor_depth": 3.0,
    },
    "WARD-117": {
        "name": "Velachery North",
        "zone": "Zone 13 - Adyar",
        "static": {"population_at_risk": 0.88, "critical_facilities": 0.82, "sensitive_population_share": 0.71, "shelter_distance_gap": 0.65, "housing_density": 0.75},
        "dyn": {"rainfall_1h": 55.0, "rainfall_3h": 85.0, "water_level_m": 2.10, "rate_of_rise": 0.06, "static_susceptibility": 0.84},
        "sensor_depth": 2.8,
    },
    "WARD-118": {
        "name": "Velachery South",
        "zone": "Zone 13 - Adyar",
        "static": {"population_at_risk": 0.85, "critical_facilities": 0.75, "sensitive_population_share": 0.74, "shelter_distance_gap": 0.70, "housing_density": 0.70},
        "dyn": {"rainfall_1h": 50.0, "rainfall_3h": 80.0, "water_level_m": 1.90, "rate_of_rise": 0.05, "static_susceptibility": 0.89},
        "sensor_depth": 3.5,
    },
    "WARD-142": {
        "name": "Adyar East",
        "zone": "Zone 13 - Adyar",
        "static": {"population_at_risk": 0.70, "critical_facilities": 0.65, "sensitive_population_share": 0.52, "shelter_distance_gap": 0.40, "housing_density": 0.65},
        "dyn": {"rainfall_1h": 25.0, "rainfall_3h": 40.0, "water_level_m": 1.10, "rate_of_rise": 0.02, "static_susceptibility": 0.61},
        "sensor_depth": 4.0,
    },
}


@router.get("")
def get_all_ward_risks(db: Session = Depends(get_db)):
    """Retrieve risk assessments across all monitored GCC wards."""
    results = []
    for ward_id, prof in WARD_PROFILES.items():
        eval_res = risk_engine.evaluate_risk(
            ward_id=ward_id,
            dynamic_features=prof["dyn"],
            static_features=prof["static"],
            sensor_depth_m=prof["sensor_depth"],
        )
        eval_res["ward_name"] = prof["name"]
        eval_res["zone"] = prof["zone"]
        eval_res["is_simulated"] = True
        results.append(eval_res)
    return results


@router.get("/{ward_id}")
def get_ward_risk(ward_id: str, db: Session = Depends(get_db)):
    """Retrieve comprehensive risk profile for a specific ward."""
    prof = WARD_PROFILES.get(ward_id, WARD_PROFILES["WARD-112"])
    eval_res = risk_engine.evaluate_risk(
        ward_id=ward_id,
        dynamic_features=prof["dyn"],
        static_features=prof["static"],
        sensor_depth_m=prof["sensor_depth"],
    )
    eval_res["ward_name"] = prof["name"]
    eval_res["zone"] = prof["zone"]
    eval_res["is_simulated"] = True
    return eval_res
