import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.enrichment.domain_validator import DomainValidationResult
from app.enrichment.resolvers import YCCompanyResolutionResult
from app.models.discovery_candidate import DiscoveryCandidate
from app.models.discovery_run import DiscoveryRun
from app.services.company_domain_enrichment_service import (
    CompanyDomainEnrichmentService,
)
from app.api.v1.company_enrichment import get_company_domain_enrichment_service
from app.utils.enums import (
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoveryRunStatus,
    DiscoverySource,
)


class FakeValidator:
    async def validate(self, value: str):
        return DomainValidationResult(
            valid=True,
            requested_url=value,
            final_url="https://www.infracost.io",
            normalized_domain="infracost.io",
            status_code=200,
        )


class FakeYCResolver:
    def supports(self, candidate):
        classification = (candidate.raw_payload or {}).get("url_classification") or {}
        return classification.get("platform") == "ycombinator"

    def extract_company_slug(self, candidate):
        return ((candidate.raw_payload or {}).get("url_classification") or {}).get(
            "external_company_slug"
        )

    async def resolve(self, candidate):
        return YCCompanyResolutionResult(
            resolved=True,
            company_slug="infracost",
            profile_url="https://www.ycombinator.com/companies/infracost",
            proposed_website_url="https://www.infracost.io",
            proposed_domain="infracost.io",
            reason="clearly labelled profile website link",
            status_code=200,
            confidence=0.95,
        )


@pytest.fixture
async def company_enrichment_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_missing_candidate_returns_404(company_enrichment_api_client: AsyncClient):
    response = await company_enrichment_api_client.post(
        "/api/v1/discovery/candidates/missing/enrich-domain"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_run_enrichment_resolves_yc_candidate(app, db_session):
    run = DiscoveryRun(
        source=DiscoverySource.HACKER_NEWS,
        status=DiscoveryRunStatus.SUCCESS,
        candidates_found=1,
        candidates_normalized=1,
        companies_created=0,
        companies_matched=0,
        candidates_deferred=1,
        candidates_rejected=0,
        candidates_failed=0,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    db_session.add(
        DiscoveryCandidate(
            discovery_run_id=run.id,
            source=DiscoverySource.HACKER_NEWS,
            source_identifier="hn:yc",
            raw_name="Infracost",
            raw_description="Apply through YC",
            normalized_name="Infracost",
            normalized_description="Apply through YC",
            status=DiscoveryCandidateStatus.NORMALIZED,
            decision=DiscoveryDecision.DEFERRED,
            deferred_reason="requires_company_domain_enrichment",
            raw_payload={
                "url_classification": {
                    "platform": "ycombinator",
                    "external_company_slug": "infracost",
                }
            },
        )
    )
    db_session.commit()

    def override_get_db():
        yield db_session

    def override_service():
        return CompanyDomainEnrichmentService(
            db_session, validator=FakeValidator(), yc_resolver=FakeYCResolver()
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_company_domain_enrichment_service] = override_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/discovery/runs/{run.id}/enrich-domains")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["candidates_resolved"] == 1
    assert data["companies_created"] == 1
    assert data["results"][0]["decision"] == "created_company"
    assert data["results"][0]["resolved_domain"] == "infracost.io"
