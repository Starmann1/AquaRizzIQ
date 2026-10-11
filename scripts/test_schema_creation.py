import os
import sys

sys.path.insert(0, os.path.abspath("apps/api"))

from sqlalchemy import text
from app.database import create_database_engine, Base
from app.db import models  # noqa: F401
from geoalchemy2 import Geometry
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateIndex

# Configure spatial compatibility
@compiles(Geometry, "postgresql")
def compile_geometry(element, compiler, **kw):
    return "BYTEA"

@compiles(CreateIndex, "postgresql")
def compile_create_index(element, compiler, **kw):
    for col in element.element.columns:
        if isinstance(col.type, Geometry):
            return "SELECT 1"
    return compiler.visit_create_index(element, **kw)

db_url = "postgresql+psycopg2://postgres:root@localhost:5432/aquarizz"
engine = create_database_engine(db_url, echo=False)

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

print("Attempting Base.metadata.create_all on PostgreSQL...")
try:
    Base.metadata.create_all(bind=engine)
    print("SUCCESS: All tables created successfully in PostgreSQL!")
    
    with engine.connect() as conn:
        res = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [r[0] for r in res.fetchall()]
        print(f"Created {len(tables)} tables: {', '.join(sorted(tables))}")
except Exception as e:
    print("FAILED with error:", e)
    import traceback
    traceback.print_exc()
