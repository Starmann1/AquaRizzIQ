import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_db, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool
from sqlalchemy import event

@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    @event.listens_for(eng, "connect")
    def setup_sqlite_spatial(dbapi_connection, connection_record):
        def dummy_func(*args):
            return 1
        for func in [
            "RecoverGeometryColumn",
            "InitSpatialMetaData",
            "AddGeometryColumn",
            "CreateSpatialIndex",
            "CheckSpatialIndex",
            "DropSpatialIndex",
            "DiscardGeometryColumn",
            "DisableSpatialIndex",
        ]:
            try:
                dbapi_connection.create_function(func, -1, dummy_func)
            except Exception:
                pass
                
    return eng

@pytest.fixture(scope="session")
def tables(engine):
    Base.metadata.create_all(engine)
    yield
    try:
        Base.metadata.drop_all(engine)
    except Exception:
        pass

@pytest.fixture
def db_session(engine, tables):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
async def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
