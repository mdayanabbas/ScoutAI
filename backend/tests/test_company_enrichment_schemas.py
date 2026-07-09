from app.schemas.company_enrichment import (
    CompanyEnrichmentAttemptRead,
    ManualCompanyDomainInput,
)


def test_manual_company_domain_input():
    data = ManualCompanyDomainInput(website_url="https://acme.ai")

    assert data.website_url == "https://acme.ai"


def test_attempt_read_maps_evidence_json():
    read = CompanyEnrichmentAttemptRead.model_validate(
        {
            "id": "attempt",
            "discovery_candidate_id": "candidate",
            "status": "resolved",
            "resolver": "business_email_domain",
            "evidence_json": {"source": "text"},
            "created_at": "2026-07-08T00:00:00Z",
        }
    )

    assert read.evidence == {"source": "text"}
