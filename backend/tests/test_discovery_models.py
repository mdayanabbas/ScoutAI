import app.models  # noqa: F401
from app.db.base import Base
from app.models import DiscoveryCandidate, DiscoveryEvidence, DiscoveryRun


def test_discovery_models_import_correctly():
    assert DiscoveryRun
    assert DiscoveryCandidate
    assert DiscoveryEvidence


def test_alembic_metadata_contains_discovery_tables():
    assert "discovery_runs" in Base.metadata.tables
    assert "discovery_candidates" in Base.metadata.tables
    assert "discovery_evidence" in Base.metadata.tables
