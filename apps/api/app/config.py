"""Application configuration via pydantic-settings."""
from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LLMMode(str, Enum):
    OFF = "off"
    TEMPLATE = "template"
    LLM = "llm"


class Settings(BaseSettings):
    """AquaRizz application settings.
    
    Loaded from environment variables and .env file.
    """
    # Application
    app_env: AppEnv = AppEnv.DEVELOPMENT
    app_name: str = "AquaRizz"
    app_version: str = "0.1.0"
    debug: bool = True
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    # SQLite keeps the local prototype runnable without a database service.
    # PostgreSQL remains an explicit DATABASE_URL override for later deployment.
    database_url: str = "sqlite:///./aquarizz.db"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    
    # Auth
    # Authentication fails closed until a deployment-specific signing key is configured.
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60
    
    # LLM
    llm_mode: LLMMode = LLMMode.TEMPLATE
    llm_provider_url: Optional[str] = None
    llm_model_name: Optional[str] = None
    llm_api_key: Optional[str] = None
    
    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Simulation
    allow_live_dispatch: bool = False
    sim_clock_speed: float = 1.0
    
    # Paths
    config_dir: str = "configs"
    models_dir: str = "models"
    data_dir: str = "data"
    
    # Ignore unrelated .env entries such as PYTHONPATH; only declared settings
    # are application configuration.
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
