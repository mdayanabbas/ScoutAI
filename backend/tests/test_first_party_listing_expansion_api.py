from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.jobs import get_first_party_listing_expansion_service
from app.db.session import get_db
from app.jobs.expansion.first_party_listing_models import (
    FirstPartyListingChild,
    FirstPartyListingExpansionResult,
)
from app.models.company import Company
from app.models.job import Job
from app.models.job_enrichment_attempt import JobEnrichmentAttempt
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_enrichment_attempt_repository import JobEnrichmentAttemptRepository
from app.repositories.job_repository import JobRepository


class FakeExpansionService:
    def __init__(self, result):
        self.result = result
        self.calls: list[str] = []

    async def expand_listing(self, job_id: str):
        self.calls.append(job_id)
        return self.result


@pytest.fixture
async def expansion_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _job(db_session):
    token = uuid4().hex[:8]
    company = CompanyRepository(db_session).create_company(
        Company(name=f"API Co {token}", normalized_domain=f"api-{token}.example", website_url=f"https://api-{token}.example")
    )
    return JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            title="Open Roles",
            normalized_title="open roles",
            job_url=f"https://api-{token}.example/careers",
        )
    )


def _result(job_id):
    return FirstPartyListingExpansionResult(
        parent_job_id=job_id,
        company_id=str(uuid4()),
        status="partial",
        reason="first_party_listing_expansion_partial",
        links_seen=2,
        candidates_selected=2,
        detail_pages_fetched=1,
        jobs_created=1,
        jobs_existing=0,
        jobs_failed=1,
        parent_deactivated=True,
        children=[
            FirstPartyListingChild(
                job_id=str(uuid4()),
                title="Backend Engineer",
                job_url="https://example.com/careers/backend-engineer",
                role_category="backend_engineer",
                location="Remote",
                remote_type="remote_worldwide",
                action="created",
            )
        ],
        warnings=["one_candidate_failed"],
        attempt_id=str(uuid4()),
    )


@pytest.mark.asyncio
async def test_expand_first_party_listing_api_returns_safe_summary(app, db_session, expansion_api_client):
    job = _job(db_session)
    fake = FakeExpansionService(_result(job.id))
    app.dependency_overrides[get_first_party_listing_expansion_service] = lambda: fake

    response = await expansion_api_client.post(f"/api/v1/jobs/{job.id}/expand-first-party-listing")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "partial"
    assert data["children"][0]["title"] == "Backend Engineer"
    assert "description" not in str(data)
    assert "evidence" not in str(data)
    assert fake.calls == [job.id]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_expand_first_party_listing_api_missing_running_and_body_forbidden(db_session, expansion_api_client):
    assert (await expansion_api_client.post("/api/v1/jobs/missing/expand-first-party-listing")).status_code == 404

    job = _job(db_session)
    JobEnrichmentAttemptRepository(db_session).create_attempt(
        JobEnrichmentAttempt(
            job_id=job.id,
            provider="first_party_listing_expansion",
            status="running",
            started_at=datetime.now(timezone.utc),
        )
    )
    conflict = await expansion_api_client.post(f"/api/v1/jobs/{job.id}/expand-first-party-listing")
    assert conflict.status_code == 409

    body_job = _job(db_session)
    arbitrary = await expansion_api_client.post(
        f"/api/v1/jobs/{body_job.id}/expand-first-party-listing",
        json={"url": "https://evil.example/jobs", "company_id": str(uuid4())},
    )
    assert arbitrary.status_code == 400
    assert arbitrary.json()["error"]["message"] == "This endpoint does not accept a request body"
    assert "evil.example" not in arbitrary.text

    empty_object = await expansion_api_client.post(
        f"/api/v1/jobs/{body_job.id}/expand-first-party-listing",
        json={},
    )
    assert empty_object.status_code == 400

    company_body = await expansion_api_client.post(
        f"/api/v1/jobs/{body_job.id}/expand-first-party-listing",
        json={"company_id": str(uuid4())},
    )
    assert company_body.status_code == 400
    assert "company_id" not in company_body.text
