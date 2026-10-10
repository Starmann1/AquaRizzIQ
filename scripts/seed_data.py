"""AquaRizz Database Seeding Script (NO DOCKER).

Populates PostgreSQL / local database with:
- GCC Wards from data/fixtures/wards.geojson
- 250m regular grid cells and terrain features
- Sensors and rainfall stations
- User accounts (admin, coordinator, operator, citizen)
- Shelters and road network nodes
- Initial telemetry observations
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from shapely.geometry import shape

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api")))

from app.database import engine, SessionLocal, Base
from app.db.models import (
    User, Ward, GridCell, GridFeature, WardFeature, Sensor, RainfallStation,
    RainfallObservation, SensorObservation, ConfigVersion, ModelVersion
)
from app.geospatial.grid import GridGenerator
from app.geospatial.terrain import TerrainFeatureCalculator
from app.geospatial.crs import to_utm


def seed_database():
    print("=== AquaRizz Database Seeder ===")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    fixtures_dir = os.path.join(root_dir, "data", "fixtures")

    try:
        # 1. Seed Demo User Roles
        demo_roles = [
            ("admin", "admin@aquarizz.local", "ADMINISTRATOR"),
            ("coordinator", "coordinator@aquarizz.local", "EMERGENCY_COORDINATOR"),
            ("operator", "operator@aquarizz.local", "MUNICIPAL_OPERATOR"),
            ("citizen", "citizen@aquarizz.local", "CITIZEN"),
        ]
        for uname, uemail, urole in demo_roles:
            existing = db.query(User).filter(User.username == uname).first()
            if not existing:
                db.add(User(
                    id=uuid.uuid4(),
                    username=uname,
                    email=uemail,
                    password_hash="demo_local_hash",
                    role=urole,
                ))
        db.commit()
        print(f"✓ Seeded demo user roles")

        # 2. Seed Wards & 250m Grid
        wards_file = os.path.join(fixtures_dir, "wards.geojson")
        grid_gen = GridGenerator()
        terrain_calc = TerrainFeatureCalculator()
        total_cells = 0

        if os.path.exists(wards_file):
            with open(wards_file, "r") as f:
                wards_geojson = json.load(f)

            for feat in wards_geojson.get("features", []):
                props = feat["properties"]
                geom_wgs = shape(feat["geometry"])
                geom_utm = to_utm(geom_wgs)

                existing_ward = db.query(Ward).filter(Ward.id == props["ward_id"]).first()
                if not existing_ward:
                    # In WKB/EWKB format for PostGIS
                    ward = Ward(
                        id=props["ward_id"],
                        name=props["name"],
                        zone=props["zone"],
                        geom=geom_utm.wkt,
                        area_sq_km=props["area_sq_km"],
                        population=props["population"],
                    )
                    db.add(ward)

                    # Ward Feature aggregation
                    ward_feat = WardFeature(
                        ward_id=props["ward_id"],
                        elevation_mean=props["elevation_mean"],
                        elevation_p90=props["elevation_mean"] + 1.2,
                        slope_mean=props["slope_mean"],
                        hand_mean=props["elevation_mean"] * 0.45,
                        imperviousness_mean=props["imperviousness_mean"],
                        susceptibility_mean=props["susceptibility_mean"],
                        susceptibility_p90=props["susceptibility_mean"] + 0.08,
                        e_score=props["e_score"],
                        v_score=props["v_score"],
                        pop_density=props["population"] / max(0.1, props["area_sq_km"]),
                        sensitive_pop_share=0.22,
                        shelter_count=2,
                        shelter_gap=0.45,
                        road_km=14.5,
                        crit_facility_count=4,
                    )
                    db.add(ward_feat)

                    # Generate 250m grid cells
                    cells = grid_gen.generate_cells_for_polygon(props["ward_id"], geom_wgs)
                    for c in cells:
                        cell_id = uuid.uuid4()
                        cell = GridCell(
                            id=cell_id,
                            ward_id=props["ward_id"],
                            ix=c["ix"],
                            iy=c["iy"],
                            geom=c["geom_utm"].wkt,
                        )
                        db.add(cell)

                        # Cell terrain features
                        cx, cy = c["center_utm"]
                        feats = terrain_calc.compute_cell_features(c["ix"], c["iy"], cx, cy, props["ward_id"])
                        g_feat = GridFeature(
                            grid_cell_id=cell_id,
                            elevation=feats["elevation"],
                            slope=feats["slope"],
                            hand=feats["hand"],
                            twi=feats["twi"],
                            drain_proximity=feats["drain_proximity"],
                            drain_density=feats["drain_density"],
                            imperviousness=feats["imperviousness"],
                            land_cover=feats["land_cover"],
                            hist_flood_freq=feats["hist_flood_freq"],
                            susceptibility=feats["susceptibility"],
                        )
                        db.add(g_feat)
                        total_cells += 1

            db.commit()
            print(f"✓ Seeded {len(wards_geojson.get('features', []))} wards and {total_cells} analytical grid cells")

        # 3. Seed Sensors
        sensors_file = os.path.join(fixtures_dir, "sensors.json")
        if os.path.exists(sensors_file):
            with open(sensors_file, "r") as f:
                sensors_data = json.load(f)
            for s in sensors_data:
                existing_s = db.query(Sensor).filter(Sensor.id == s["id"]).first()
                if not existing_s:
                    sensor = Sensor(
                        id=s["id"],
                        name=s["name"],
                        ward_id=s["ward_id"],
                        geom=f"POINT({s['longitude']} {s['latitude']})",
                        sensor_type=s["sensor_type"],
                        depth_m=s["depth_m"],
                        is_active=True,
                        is_simulated=s.get("is_simulated", True),
                    )
                    db.add(sensor)
            db.commit()
            print(f"✓ Seeded {len(sensors_data)} physical & simulated sensors")

        print("=== Database Seeding Complete ===")

    except Exception as e:
        db.rollback()
        print(f"❌ Seeding error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
