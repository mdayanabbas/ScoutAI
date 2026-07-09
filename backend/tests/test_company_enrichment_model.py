import app.models  # noqa: F401
from app.db.base import Base
from app.models import CompanyEnrichmentAttempt


def test_company_enrichment_attempt_model_imports():
    assert CompanyEnrichmentAttempt


def test_metadata_contains_company_enrichment_attempts():
    assert "company_enrichment_attempts" in Base.metadata.tables
