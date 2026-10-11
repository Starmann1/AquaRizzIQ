from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.config import get_settings
from app.database import engine, SessionLocal, initialize_database_schema
from app.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    request_validation_handler,
)
from app.middleware import RequestIdMiddleware, setup_cors

from app.api import (
    health,
    auth_routes,
    data,
    zones,
    risk,
    assessments,
    explanations,
    reviews,
    alerts,
    routes_api,
    demo,
    audit_api,
    forecast_api,
    recommendations_api,
    observed_layers,
)
from app.services.spatial_datasets import load_bundled_datasets

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env.value == "development":
        initialize_database_schema()
        with SessionLocal() as db:
            load_bundled_datasets(db)
    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

setup_cors(app)
app.add_middleware(RequestIdMiddleware)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_handler)

@app.get("/")
def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "online",
        "web_dashboard_url": "http://localhost:5173/",
        "api_docs_url": "http://127.0.0.1:8000/docs",
        "api_base": "http://127.0.0.1:8000/api/v1"
    }

@app.get("/api/v1")
@app.get("/api/v1/")
def api_v1_index():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "api_version": "v1",
        "status": "online",
        "docs_url": "http://127.0.0.1:8000/docs",
        "endpoints": {
            "health": "/api/v1/health",
            "zones": "/api/v1/zones",
            "risk": "/api/v1/risk",
            "forecasts": "/api/v1/forecasts",
            "explanations": "/api/v1/explanations",
            "recommendations": "/api/v1/recommendations",
            "assessments": "/api/v1/assessments",
            "audit": "/api/v1/audit"
        }
    }

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(data.router, prefix="/api/v1")
app.include_router(zones.router, prefix="/api/v1")
app.include_router(risk.router, prefix="/api/v1")
app.include_router(assessments.router, prefix="/api/v1")
app.include_router(explanations.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(routes_api.router, prefix="/api/v1")
app.include_router(demo.router, prefix="/api/v1")
app.include_router(audit_api.router, prefix="/api/v1")
app.include_router(forecast_api.router, prefix="/api/v1")
app.include_router(recommendations_api.router, prefix="/api/v1")
app.include_router(observed_layers.router, prefix="/api/v1")
