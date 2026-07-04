import os
from unittest.mock import patch

from app.core.config import Settings, get_settings


def test_settings_defaults_without_env_file():
    env = {
        "APP_NAME": "ScoutAI API",
        "APP_ENV": "local",
        "DEBUG": "false",
        "API_V1_PREFIX": "/api/v1",
        "BACKEND_CORS_ORIGINS": "http://localhost:3000,http://127.0.0.1:3000",
        "DATABASE_URL": "postgresql+psycopg://scoutai:scoutai@localhost:5433/scoutai",
        "REDIS_URL": "redis://localhost:6379/0",
        "LOG_LEVEL": "INFO",
    }
    with patch.dict(os.environ, env, clear=True):
        settings = Settings(_env_file=None)
        assert settings.APP_NAME == "ScoutAI API"
        assert settings.APP_ENV == "local"
        assert settings.DEBUG is False
        assert settings.API_V1_PREFIX == "/api/v1"
        assert settings.LOG_LEVEL == "INFO"


def test_settings_from_env():
    env = {
        "APP_NAME": "TestApp",
        "APP_ENV": "production",
        "DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env, clear=True):
        settings = Settings(_env_file=None)
        assert settings.APP_NAME == "TestApp"
        assert settings.APP_ENV == "production"
        assert settings.DEBUG is True
        assert settings.LOG_LEVEL == "DEBUG"


def test_settings_cors_origins_split():
    settings = get_settings()
    origins = settings.BACKEND_CORS_ORIGINS.split(",")
    assert "http://localhost:3000" in [o.strip() for o in origins]


def test_settings_loaded_from_env_file():
    settings = get_settings()
    assert settings.DEBUG is True
    assert settings.DATABASE_URL == (
        "postgresql+psycopg://scoutai:scoutai@localhost:5433/scoutai"
    )
