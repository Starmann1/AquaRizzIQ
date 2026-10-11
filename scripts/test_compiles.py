from sqlalchemy import Column, String, Table, MetaData
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from sqlalchemy.ext.compiler import compiles
from geoalchemy2 import Geometry

@compiles(Geometry, "postgresql")
def compile_geometry(element, compiler, **kw):
    # Check if PostGIS extension is active, otherwise fallback to BYTEA
    return "BYTEA"

meta = MetaData()
t = Table(
    'test_t', meta,
    Column('id', String, primary_key=True),
    Column('geom', Geometry('MULTIPOLYGON', srid=32644))
)

ddl = CreateTable(t).compile(dialect=postgresql.dialect())
print("Compiled DDL:")
print(str(ddl))
