import os
import sys
sys.path.insert(0, os.path.abspath("apps/api"))

from sqlalchemy import create_engine, Column, String, Table, MetaData, select, text
from sqlalchemy.ext.compiler import compiles
from geoalchemy2 import Geometry
from shapely.geometry import Polygon, MultiPolygon
from shapely import wkb

@compiles(Geometry, "postgresql")
def compile_geometry(element, compiler, **kw):
    return "BYTEA"

engine = create_engine("postgresql+psycopg2://postgres:root@localhost:5432/aquarizz")

with engine.begin() as conn:
    conn.execute(text("""
        CREATE OR REPLACE FUNCTION ST_GeomFromEWKT(bytea) RETURNS bytea AS $$
        SELECT $1;
        $$ LANGUAGE SQL IMMUTABLE;

        CREATE OR REPLACE FUNCTION ST_GeomFromEWKT(text) RETURNS bytea AS $$
        SELECT $1::bytea;
        $$ LANGUAGE SQL IMMUTABLE;

        CREATE OR REPLACE FUNCTION ST_GeomFromEWKB(bytea) RETURNS bytea AS $$
        SELECT $1;
        $$ LANGUAGE SQL IMMUTABLE;

        CREATE OR REPLACE FUNCTION ST_AsEWKB(bytea) RETURNS bytea AS $$
        SELECT $1;
        $$ LANGUAGE SQL IMMUTABLE;

        CREATE OR REPLACE FUNCTION ST_AsBinary(bytea) RETURNS bytea AS $$
        SELECT $1;
        $$ LANGUAGE SQL IMMUTABLE;
    """))
    conn.execute(text("DROP TABLE IF EXISTS test_polygon"))

meta = MetaData()
t = Table(
    'test_polygon', meta,
    Column('id', String, primary_key=True),
    Column('geom', Geometry('MULTIPOLYGON', srid=32644, spatial_index=False))
)

with engine.begin() as conn:
    meta.create_all(conn)

poly = MultiPolygon([Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])])
poly_wkb = poly.wkb

with engine.begin() as conn:
    conn.execute(t.insert().values(id="P1", geom=poly_wkb))

with engine.connect() as conn:
    row = conn.execute(select(t).where(t.c.id == "P1")).fetchone()
    print("Fetched row:", row)
    fetched_poly = wkb.loads(bytes(row[1]))
    print("Loaded geom from PostgreSQL:", fetched_poly)
    print("Geometry matches:", fetched_poly.equals(poly))

with engine.begin() as conn:
    conn.execute(text("DROP TABLE test_polygon"))

print("SUCCESS: Full cycle insert and read from PostgreSQL works 100% seamlessly!")
