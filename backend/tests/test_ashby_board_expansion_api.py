from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.jobs import get_ashby_board_expansion_service
from app.db.session import get_db
from app.jobs.expansion.models import AshbyBoardExpansionCandidate, AshbyBoardExpansionResult
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

    async def expand_job_board(self, job_id: str):
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
            title="GTM Team",
            normalized_title="gtm team",
            job_url="https://jobs.ashbyhq.com/api",
        )
    )


def _result(job_id):
    return AshbyBoardExpansionResult(
        parent_job_id=job_id,
        company_id=str(uuid4()),
        board_slug="api",
        status="succeeded",
        reason="ashby_board_expanded",
        postings_seen=1,
        postings_listed=1,
        postings_selected=1,
        jobs_created=1,
        parent_deactivated=True,
        created_job_ids=[str(uuid4())],
        candidates=[
            AshbyBoardExpansionCandidate(
                posting_id="ae",
                title="Account Executive",
                canonical_job_url="https://jobs.ashbyhq.com/api/ae",
                selected=True,
                job_id=str(uuid4()),
                action="created",
                status="succeeded",
            )
        ],
        attempt_id=str(uuid4()),
    )


@pytest.mark.asyncio
async def test_expand_ashby_board_api_returns_structured_result(app, db_session, expansion_api_client):
    job = _job(db_session)
    fake = FakeExpansionService(_result(job.id))
    app.dependency_overrides[get_ashby_board_expansion_service] = lambda: fake

    response = await expansion_api_client.post(f"/api/v1/jobs/{job.id}/expand-ashby-board")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "succeeded"
    assert data["candidates"][0]["title"] == "Account Executive"
    assert "description" not in str(data)
    assert fake.calls == [job.id]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_expand_ashby_board_api_missing_and_running(app, db_session, expansion_api_client):
    assert (await expansion_api_client.post("/api/v1/jobs/missing/expand-ashby-board")).status_code == 404

    job = _job(db_session)
    JobEnrichmentAttemptRepository(db_session).create_attempt(
        JobEnrichmentAttempt(
            job_id=job.id,
            provider="ashby_board_expansion",
            status="running",
            started_at=datetime.now(timezone.utc),
        )
    )
    conflict = await expansion_api_client.post(f"/api/v1/jobs/{job.id}/expand-ashby-board")
    assert conflict.status_code == 409
