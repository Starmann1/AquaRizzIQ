from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings
from geoalchemy2 import Geometry
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateIndex

settings = get_settings()


def setup_sqlite_spatial(dbapi_connection, connection_record):
    import re

    from shapely import wkb, wkt

    def as_ewkb(val):
        if val is None:
            return None
        if isinstance(val, bytes):
            try:
                wkb.loads(val)
                return val
            except Exception:
                val = val.decode("utf-8", errors="replace")
        value = str(val)
        srid_match = re.match(r"^SRID=(\d+);", value, re.IGNORECASE)
        srid = int(srid_match.group(1)) if srid_match else 32644
        wkt_value = value[srid_match.end():] if srid_match else value
        try:
            geom = wkt.loads(wkt_value)
            return wkb.dumps(geom, srid=srid)
        except Exception:
            return None

    def geom_from_text(val, *args):
        return val

    def dummy_one(*args):
        return 1

    for name in ["AsEWKB", "ST_AsEWKB"]:
        try:
            dbapi_connection.create_function(name, 1, as_ewkb)
        except Exception:
            pass

    for name in [
        "GeomFromText", "ST_GeomFromText", "GeomFromEWKB", "ST_GeomFromEWKB",
        "GeomFromEWKT", "ST_GeomFromEWKT",
    ]:
        try:
            dbapi_connection.create_function(name, -1, geom_from_text)
        except Exception:
            pass

    for func in [
        "RecoverGeometryColumn", "InitSpatialMetaData", "AddGeometryColumn",
        "CreateSpatialIndex", "CheckSpatialIndex", "DropSpatialIndex",
        "DiscardGeometryColumn", "DisableSpatialIndex",
    ]:
        try:
            dbapi_connection.create_function(func, -1, dummy_one)
        except Exception:
            pass


def setup_postgres_spatial(target_engine: Engine) -> bool:
    """Check/enable PostGIS extension, or register SQL compatibility functions for PostgreSQL."""
    has_postgis = False
    try:
        with target_engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            has_postgis = True
    except Exception:
        has_postgis = False

    target_engine._has_postgis = has_postgis

    if not has_postgis:
        with target_engine.begin() as connection:
            connection.execute(text("""
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
    return has_postgis


def create_database_engine(database_url: str, echo: bool = False) -> Engine:
    """Create the explicitly configured engine; never silently change backends."""
    if database_url.startswith("sqlite:"):
        sqlite_engine = create_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False},
        )
        event.listen(sqlite_engine, "connect", setup_sqlite_spatial)
        sqlite_engine._has_postgis = False
        return sqlite_engine
    if database_url.startswith("postgresql"):
        pg_engine = create_engine(
            database_url,
            echo=echo,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
        )
        pg_engine._has_postgis = False
        return pg_engine
    raise ValueError("DATABASE_URL must use an explicitly supported sqlite or postgresql scheme")


engine = create_database_engine(settings.database_url, echo=settings.db_echo)


@compiles(Geometry, "postgresql")
def compile_geometry(element, compiler, **kw):
    if not getattr(engine, "_has_postgis", False):
        return "BYTEA"
    return compiler.visit_geometry(element, **kw)


@compiles(CreateIndex, "postgresql")
def compile_create_index(element, compiler, **kw):
    if not getattr(engine, "_has_postgis", False):
        for col in element.element.columns:
            if isinstance(col.type, Geometry):
                return "SELECT 1"
    return compiler.visit_create_index(element, **kw)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass


def initialize_database_schema() -> None:
    """Create prototype tables and initialize spatial capabilities for PostgreSQL."""
    if engine.dialect.name == "postgresql":
        setup_postgres_spatial(engine)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
