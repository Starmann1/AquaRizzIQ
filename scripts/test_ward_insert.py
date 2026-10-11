import os
import sys
sys.path.insert(0, os.path.abspath("apps/api"))

from app.database import SessionLocal, initialize_database_schema
from app.db.models import Ward
from shapely.geometry import Polygon, MultiPolygon
from shapely import wkb
import datetime

initialize_database_schema()
db = SessionLocal()

# Test inserting a dummy ward
test_poly = MultiPolygon([Polygon([(390000, 1440000), (390000, 1441000), (391000, 1441000), (391000, 1440000), (390000, 1440000)])])

try:
    existing = db.query(Ward).filter(Ward.id == "TEST-001").first()
    if existing:
        db.delete(existing)
        db.commit()

    w = Ward(
        id="TEST-001",
        name="Test Ward 1",
        zone="TEST ZONE",
        geom=test_poly.wkb,
        area_sq_km=2.5,
        population=45000,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(w)
    db.commit()
    print("SUCCESS: Ward inserted into PostgreSQL successfully!")

    # Verify query
    queried = db.query(Ward).filter(Ward.id == "TEST-001").first()
    print(f"Queried ward from PG: id={queried.id}, name={queried.name}, zone={queried.zone}, pop={queried.population}")

    db.delete(queried)
    db.commit()
    print("SUCCESS: Ward query and cleanup verified!")
except Exception as e:
    db.rollback()
    print("ERROR:", e)
    import traceback
    traceback.print_exc()
finally:
    db.close()
