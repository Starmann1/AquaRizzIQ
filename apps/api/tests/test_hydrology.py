import pytest
from app.hydrology.scs_cn import SCSCurveNumberModel
from app.hydrology.reservoir import LinearReservoirSensorModel
from app.hydrology.simulator import CatchmentSimulator


def test_scs_cn_monotonicity():
    """Verify that runoff depth increases monotonically with rainfall."""
    built_fraction = 0.80
    q1 = SCSCurveNumberModel.calculate_runoff_depth_mm(rainfall_depth_mm=10.0, built_fraction=built_fraction)
    q2 = SCSCurveNumberModel.calculate_runoff_depth_mm(rainfall_depth_mm=50.0, built_fraction=built_fraction)
    q3 = SCSCurveNumberModel.calculate_runoff_depth_mm(rainfall_depth_mm=100.0, built_fraction=built_fraction)

    assert q1 <= q2 <= q3
    assert q3 > 0.0


def test_scs_cn_built_fraction_impact():
    """Higher imperviousness produces higher runoff for same rainfall."""
    p = 60.0
    q_rural = SCSCurveNumberModel.calculate_runoff_depth_mm(rainfall_depth_mm=p, built_fraction=0.10)
    q_urban = SCSCurveNumberModel.calculate_runoff_depth_mm(rainfall_depth_mm=p, built_fraction=0.85)

    assert q_urban > q_rural


def test_reservoir_evolution():
    sensor = LinearReservoirSensorModel(
        sensor_id="SIM-TEST-01",
        depth_m=3.0,
        normal_level_m=0.20,
    )

    # 1. Zero rain -> level stays at baseflow
    h_dry = sensor.step(0.20, rainfall_intensity_mmh=0.0, time_hours=0.0, dt_minutes=5.0)
    assert pytest.approx(h_dry, abs=0.05) == 0.20

    # 2. Heavy rain -> level rises
    h_wet = sensor.step(0.20, rainfall_intensity_mmh=80.0, time_hours=0.0, dt_minutes=5.0)
    assert h_wet > 0.20


@pytest.mark.asyncio
async def test_catchment_simulator_determinism(db_session):
    """T15: Ensure simulator executes deterministically given fixed scenario."""
    timeline = [
        {"step": 0, "rainfall_intensity_mmh": 10.0, "phase": "LOW"},
        {"step": 1, "rainfall_intensity_mmh": 80.0, "phase": "SPIKE"},
    ]
    sim = CatchmentSimulator(db_session, scenario_timeline=timeline)

    res1 = sim.advance_step()
    assert res1["rainfall_intensity_mmh"] == 10.0

    res2 = sim.advance_step()
    assert res2["rainfall_intensity_mmh"] == 80.0
    assert res2["water_levels"]["SIM-SWD-W112-001"] > res1["water_levels"]["SIM-SWD-W112-001"]
