import sqlite3

from app.config import Settings
from shapely import get_srid, wkb

from app.database import create_database_engine, setup_sqlite_spatial


def test_sqlite_spatial_shim_converts_ewkt_to_valid_ewkb():
    connection = sqlite3.connect(":memory:")
    setup_sqlite_spatial(connection, None)

    value = connection.execute("SELECT AsEWKB(?)", ("SRID=32644;POINT (80.25 13.0667)",)).fetchone()[0]
    geometry = wkb.loads(value)

    assert geometry.geom_type == "Point"
    assert geometry.x == 80.25
    assert geometry.y == 13.0667
    assert get_srid(geometry) == 32644


def test_sqlite_spatial_shim_returns_null_for_unparseable_geometry():
    connection = sqlite3.connect(":memory:")
    setup_sqlite_spatial(connection, None)

    value = connection.execute("SELECT AsEWKB(?)", ("not a geometry",)).fetchone()[0]

    assert value is None


def test_database_engine_honors_explicit_sqlite_url():
    engine = create_database_engine("sqlite:///:memory:")

    assert engine.url.database == ":memory:"
    assert engine.dialect.name == "sqlite"
    engine.dispose()


def test_local_default_database_is_sqlite_without_service(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite:///./aquarizz.db"
    engine = create_database_engine(settings.database_url)
    assert engine.dialect.name == "sqlite"
    engine.dispose()


def test_database_engine_rejects_implicit_or_unknown_backends():
    try:
        create_database_engine("mysql://user:pass@localhost/db")
    except ValueError as exc:
        assert "DATABASE_URL" in str(exc)
    else:
        raise AssertionError("Unsupported database backend should fail fast")
