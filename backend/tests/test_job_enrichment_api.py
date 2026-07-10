from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.jobs import get_job_detail_enrichment_service
from app.db.session import get_db
from app.models.company import Company
from app.models.job import Job
from app.models.job_enrichment_attempt import JobEnrichmentAttempt
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_enrichment_attempt_repository import (
    JobEnrichmentAttemptRepository,
)
from app.repositories.job_repository import JobRepository
from app.services.job_detail_enrichment_service import JobEnrichmentResult
from app.utils.enums import JobStatus

YC_URL = "https://www.ycombinator.com/companies/hazel-2/jobs/3epPWgu-full-stack-engineer-ts-sci"


class FakeEnrichmentService:
    def __init__(self, db_session, result: JobEnrichmentResult | Exception):
        self.db_session = db_session
        self.result = result

    async def enrich_job(self, job_id: str):
        if isinstance(self.result, Exception):
            raise self.result
        if self.result.status in {"enriched", "partially_enriched"}:
            job = JobRepository(self.db_session).get_by_id(job_id)
            JobRepository(self.db_session).update_enrichment_fields(
                job_id,
                {
                    "title": "Full Stack Engineer (TS/SCI)",
                    "normalized_title": "full stack engineer (ts/sci)",
                    "enrichment_status": self.result.status,
                    "enrichment_confidence": self.result.enrichment_confidence,
                },
            )
        return self.result


@pytest.fixture
async def job_enrichment_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _job(db_session, *, job_url=YC_URL, title="Open Roles"):
    company = CompanyRepository(db_session).create_company(
        Company(
            name=f"Jobs Co {title}",
            normalized_domain=f"{title.lower().replace(' ', '-')}.example",
            website_url="https://jobs.example",
        )
    )
    return JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            title=title,
            normalized_title=title.lower(),
            job_url=job_url,
            source_platform="hacker_news",
            status=JobStatus.ACTIVE,
            first_seen_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )


def _attempt(db_session, job_id, *, status="succeeded", created_at=None):
    return JobEnrichmentAttemptRepository(db_session).create_attempt(
        JobEnrichmentAttempt(
            job_id=job_id,
            provider="ycombinator_job_page",
            status=status,
            reason="test",
            source_url=YC_URL,
            extracted_data_json={"title": "Full Stack Engineer"},
            evidence_json={"canonical_url": YC_URL},
            field_confidence_json={"title": 0.98},
            started_at=created_at or datetime.now(timezone.utc),
            created_at=created_at or datetime.now(timezone.utc),
        )
    )


def _result(job, status="enriched", attempt_id=None):
    return JobEnrichmentResult(
        job_id=job.id,
        provider="ycombinator_job_page",
        status=status,
        reason="valid_supported_source",
        source_type="ycombinator_job",
        source_url=YC_URL,
        canonical_url=YC_URL,
        updated_fields={"title": "Full Stack Engineer (TS/SCI)"},
        preserved_fields={"description": "existing_description_richer_or_equal"},
        warnings=["salary_text_not_numeric"],
        enrichment_confidence=0.95,
        attempt_id=attempt_id,
    )


@pytest.mark.asyncio
async def test_post_enrichment_returns_updated_job_attempt_and_fields(app, db_session, job_enrichment_client):
    job = _job(db_session)
    attempt = _attempt(db_session, job.id)

    def override_service():
        return FakeEnrichmentService(db_session, _result(job, attempt_id=attempt.id))

    app.dependency_overrides[get_job_detail_enrichment_service] = override_service
    response = await job_enrichment_client.post(f"/api/v1/jobs/{job.id}/enrich")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "enriched"
    assert data["job"]["title"] == "Full Stack Engineer (TS/SCI)"
    assert data["attempt"]["id"] == attempt.id
    assert data["fields_updated"]["title"] == "Full Stack Engineer (TS/SCI)"
    assert data["fields_preserved"]["description"] == "existing_description_richer_or_equal"
    assert data["warnings"] == ["salary_text_not_numeric"]
    assert "raw_html" not in str(data)
    assert "Traceback" not in str(data)
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("status_value", ["partially_enriched", "unresolved", "skipped", "failed"])
async def test_post_enrichment_normal_outcomes_return_200(app, db_session, job_enrichment_client, status_value):
    job = _job(db_session, title=f"Open Roles {status_value}")
    attempt = _attempt(db_session, job.id, status="failed" if status_value == "failed" else "partial")

    def override_service():
        return FakeEnrichmentService(db_session, _result(job, status=status_value, attempt_id=attempt.id))

    app.dependency_overrides[get_job_detail_enrichment_service] = override_service
    response = await job_enrichment_client.post(f"/api/v1/jobs/{job.id}/enrich")

    assert response.status_code == 200
    assert response.json()["status"] == status_value
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_enrichment_missing_running_and_unexpected_errors(app, db_session, job_enrichment_client):
    missing = await job_enrichment_client.post("/api/v1/jobs/missing/enrich")
    assert missing.status_code == 404

    job = _job(db_session, title="Concurrent")
    _attempt(db_session, job.id, status="running")
    conflict = await job_enrichment_client.post(f"/api/v1/jobs/{job.id}/enrich")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["message"] == "Job enrichment is already running"

    other = _job(db_session, title="Unexpected")

    def override_service():
        return FakeEnrichmentService(db_session, RuntimeError("secret stack trace"))

    app.dependency_overrides[get_job_detail_enrichment_service] = override_service
    response = await job_enrichment_client.post(f"/api/v1/jobs/{other.id}/enrich")
    assert response.status_code == 500
    assert "secret stack trace" not in response.text
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_attempt_history_latest_and_pagination(job_enrichment_client, db_session):
    job = _job(db_session)
    old = _attempt(db_session, job.id, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    new = _attempt(db_session, job.id, created_at=datetime(2026, 1, 2, tzinfo=timezone.utc))

    response = await job_enrichment_client.get(f"/api/v1/jobs/{job.id}/enrichment-attempts?limit=1&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["limit"] == 1
    assert data["items"][0]["id"] == new.id
    assert data["items"][0]["extracted_data"] == {"title": "Full Stack Engineer"}
    assert "extracted_data_json" not in data["items"][0]

    latest = await job_enrichment_client.get(f"/api/v1/jobs/{job.id}/enrichment-attempts/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == new.id

    assert (await job_enrichment_client.get("/api/v1/jobs/missing/enrichment-attempts")).status_code == 404
    assert (await job_enrichment_client.get("/api/v1/jobs/missing/enrichment-attempts/latest")).status_code == 404

    empty_job = _job(db_session, title="No Attempts")
    assert (await job_enrichment_client.get(f"/api/v1/jobs/{empty_job.id}/enrichment-attempts/latest")).status_code == 404
    assert old.id != new.id


@pytest.mark.asyncio
async def test_attempt_history_limit_validation(job_enrichment_client, db_session):
    job = _job(db_session)
    response = await job_enrichment_client.get(f"/api/v1/jobs/{job.id}/enrichment-attempts?limit=101")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_source_detection_endpoint(job_enrichment_client, db_session):
    yc = _job(db_session, title="YC")
    first_party = _job(db_session, title="First Party", job_url="https://first-party.example/careers")
    invalid = _job(db_session, title="Invalid", job_url="javascript:alert(1)")

    yc_response = await job_enrichment_client.get(f"/api/v1/jobs/{yc.id}/source-detection")
    assert yc_response.status_code == 200
    assert yc_response.json()["source_type"] == "ycombinator_job"
    assert yc_response.json()["company_slug"] == "hazel-2"
    assert yc_response.json()["job_identifier"] == "3epPWgu"

    first_response = await job_enrichment_client.get(f"/api/v1/jobs/{first_party.id}/source-detection")
    assert first_response.status_code == 200
    assert first_response.json()["source_type"] == "first_party_job_page"

    invalid_response = await job_enrichment_client.get(f"/api/v1/jobs/{invalid.id}/source-detection")
    assert invalid_response.status_code == 200
    assert invalid_response.json()["source_type"] == "invalid"
