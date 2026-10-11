from sqlalchemy import Column, String, Table, MetaData
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from geoalchemy2 import Geometry

meta = MetaData()
t = Table(
    'test_t', meta,
    Column('id', String, primary_key=True),
    Column('geom', Geometry('MULTIPOLYGON', srid=32644, use_typmod=False, spatial_index=False))
)

ddl = CreateTable(t).compile(dialect=postgresql.dialect())
print(str(ddl))
