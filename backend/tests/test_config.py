import os
from unittest.mock import patch

from app.core.config import Settings


def test_settings_defaults():
    settings = Settings()
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
        settings = Settings()
        assert settings.APP_NAME == "TestApp"
        assert settings.APP_ENV == "production"
        assert settings.DEBUG is True
        assert settings.LOG_LEVEL == "DEBUG"


def test_settings_cors_origins_split():
    settings = Settings()
    origins = settings.BACKEND_CORS_ORIGINS.split(",")
    assert "http://localhost:3000" in [o.strip() for o in origins]
