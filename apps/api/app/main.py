from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import get_settings
from app.database import engine, Base
from app.errors import AppError, app_error_handler
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
)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env.value == "development":
        Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

setup_cors(app)
app.add_middleware(RequestIdMiddleware)
app.add_exception_handler(AppError, app_error_handler)

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
