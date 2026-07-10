from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.jobs import get_job_batch_enrichment_service
from app.db.session import get_db
from app.services.job_batch_enrichment_service import (
    JobBatchEnrichmentItem,
    JobBatchEnrichmentResult,
)


class FakeBatchService:
    def __init__(self, result: JobBatchEnrichmentResult):
        self.result = result
        self.calls: list[dict] = []

    async def enrich_jobs(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


@pytest.fixture
async def batch_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _result(*items: JobBatchEnrichmentItem):
    now = datetime.now(timezone.utc)
    statuses = [item.status for item in items]
    return JobBatchEnrichmentResult(
        jobs_examined=sum(1 for item in items if item.status != "missing"),
        jobs_enriched=statuses.count("enriched"),
        jobs_partially_enriched=statuses.count("partially_enriched"),
        jobs_unresolved=statuses.count("unresolved"),
        jobs_failed=statuses.count("failed"),
        jobs_skipped=statuses.count("skipped"),
        jobs_missing=statuses.count("missing"),
        started_at=now,
        finished_at=now,
        duration_ms=3,
        results=list(items),
    )


@pytest.mark.asyncio
async def test_batch_api_valid_request_returns_200(app, batch_api_client):
    fake = FakeBatchService(
        _result(
            JobBatchEnrichmentItem(
                job_id=str(uuid4()),
                company_name="YC Co",
                previous_title="Open Roles",
                current_title="Full Stack Engineer",
                provider="ycombinator_job_page",
                status="enriched",
                fields_updated={"title": "Full Stack Engineer"},
                warnings=[],
                attempt_id=str(uuid4()),
                enrichment_confidence=0.95,
            ),
            JobBatchEnrichmentItem(job_id=str(uuid4()), status="failed", reason="yc_job_page_timeout"),
        )
    )
    app.dependency_overrides[get_job_batch_enrichment_service] = lambda: fake

    response = await batch_api_client.post(
        "/api/v1/jobs/enrichment/batch",
        json={"limit": 2, "include_failed": True, "force": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["jobs_examined"] == 2
    assert data["jobs_enriched"] == 1
    assert data["jobs_failed"] == 1
    assert data["results"][0]["fields_updated"]["title"] == "Full Stack Engineer"
    assert "description" not in data["results"][0]
    assert fake.calls[0]["limit"] == 2
    assert fake.calls[0]["include_failed"] is True
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_batch_api_without_body_uses_defaults(app, batch_api_client):
    fake = FakeBatchService(_result())
    app.dependency_overrides[get_job_batch_enrichment_service] = lambda: fake

    response = await batch_api_client.post("/api/v1/jobs/enrichment/batch")

    assert response.status_code == 200
    assert fake.calls[0]["limit"] == 10
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_batch_api_validates_limits_ids_and_extra_fields(batch_api_client):
    too_large = await batch_api_client.post("/api/v1/jobs/enrichment/batch", json={"limit": 999})
    invalid_limit = await batch_api_client.post("/api/v1/jobs/enrichment/batch", json={"limit": 0})
    empty_ids = await batch_api_client.post("/api/v1/jobs/enrichment/batch", json={"job_ids": []})
    invalid_id = await batch_api_client.post("/api/v1/jobs/enrichment/batch", json={"job_ids": ["not-a-uuid"]})
    arbitrary_provider = await batch_api_client.post(
        "/api/v1/jobs/enrichment/batch",
        json={"provider": "ashby"},
    )
    arbitrary_url = await batch_api_client.post(
        "/api/v1/jobs/enrichment/batch",
        json={"source_url": "https://example.com/job"},
    )

    assert too_large.status_code == 422
    assert invalid_limit.status_code == 422
    assert empty_ids.status_code == 422
    assert invalid_id.status_code == 422
    assert arbitrary_provider.status_code == 422
    assert arbitrary_url.status_code == 422


@pytest.mark.asyncio
async def test_batch_api_dedupes_ids_and_partial_failures_still_return_200(app, batch_api_client):
    first = str(uuid4())
    fake = FakeBatchService(
        _result(
            JobBatchEnrichmentItem(job_id=first, status="enriched"),
            JobBatchEnrichmentItem(job_id=str(uuid4()), status="missing", reason="job_not_found"),
            JobBatchEnrichmentItem(job_id=str(uuid4()), status="skipped", reason="unsupported_job_source"),
        )
    )
    app.dependency_overrides[get_job_batch_enrichment_service] = lambda: fake

    response = await batch_api_client.post(
        "/api/v1/jobs/enrichment/batch",
        json={"job_ids": [first, first], "limit": 10},
    )

    assert response.status_code == 200
    assert response.json()["jobs_missing"] == 1
    assert response.json()["jobs_skipped"] == 1
    assert fake.calls[0]["job_ids"] == [first, first]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_batch_route_is_not_captured_as_job_id(batch_api_client):
    response = await batch_api_client.post("/api/v1/jobs/enrichment/batch", json={"provider": "nope"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
