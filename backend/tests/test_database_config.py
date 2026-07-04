from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, get_db


EXPECTED_LOCAL_DATABASE_URL = (
    "postgresql+psycopg://scoutai:scoutai@localhost:5433/scoutai"
)


def test_database_url_loaded_from_settings():
    settings = get_settings()
    assert settings.DATABASE_URL == EXPECTED_LOCAL_DATABASE_URL


def test_database_url_matches_current_settings():
    settings = get_settings()
    assert "localhost:5433" in settings.DATABASE_URL


def test_get_db_importable():
    assert callable(get_db)


def test_session_local_available():
    assert SessionLocal is not None


def test_base_metadata_exists():
    assert Base.metadata is not None
