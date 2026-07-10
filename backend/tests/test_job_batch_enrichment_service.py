from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models.company import Company
from app.models.job import Job
from app.models.job_enrichment_attempt import JobEnrichmentAttempt
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_enrichment_attempt_repository import (
    JobEnrichmentAttemptRepository,
)
from app.repositories.job_repository import JobRepository
from app.services.job_batch_enrichment_service import JobBatchEnrichmentService
from app.services.job_detail_enrichment_service import JobEnrichmentResult
from app.utils.enums import JobStatus

YC_URL = "https://www.ycombinator.com/companies/hazel-2/jobs/3epPWgu-full-stack-engineer-ts-sci"


class FakeDetailService:
    def __init__(self, db_session, statuses=None, fail_ids=None):
        self.db_session = db_session
        self.statuses = statuses or {}
        self.fail_ids = set(fail_ids or [])
        self.calls: list[str] = []

    async def enrich_job(self, job_id: str):
        self.calls.append(job_id)
        if job_id in self.fail_ids:
            raise RuntimeError("boom")
        status = self.statuses.get(job_id, "enriched")
        attempt = JobEnrichmentAttemptRepository(self.db_session).create_attempt(
            JobEnrichmentAttempt(
                job_id=job_id,
                provider="ycombinator_job_page",
                status="succeeded" if status == "enriched" else "partial",
                source_url=YC_URL,
                started_at=datetime.now(timezone.utc),
            )
        )
        if status == "enriched":
            JobRepository(self.db_session).update_enrichment_fields(
                job_id,
                {
                    "title": "Full Stack Engineer (TS/SCI)",
                    "normalized_title": "full stack engineer (ts/sci)",
                    "enrichment_status": "enriched",
                    "enrichment_confidence": 0.95,
                },
            )
        return JobEnrichmentResult(
            job_id=job_id,
            provider="ycombinator_job_page",
            status=status,
            reason="valid_supported_source" if status != "skipped" else "unsupported_provider_for_current_brick",
            updated_fields={"title": "Full Stack Engineer (TS/SCI)"} if status == "enriched" else {},
            warnings=[],
            attempt_id=attempt.id,
            enrichment_confidence=0.95,
        )


def _company(db_session):
    token = uuid4().hex[:8]
    return CompanyRepository(db_session).create_company(
        Company(
            name=f"Batch Co {token}",
            normalized_domain=f"batch-{token}.example",
            website_url=f"https://batch-{token}.example",
        )
    )


def _job(db_session, *, title="Open Roles", status="not_enriched", verified_at=None, job_url=YC_URL, created_at=None):
    company = _company(db_session)
    return JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            title=title,
            normalized_title=title.lower(),
            job_url=job_url,
            source_platform="hacker_news",
            status=JobStatus.ACTIVE,
            enrichment_status=status,
            last_verified_at=verified_at,
            created_at=created_at or datetime.now(timezone.utc),
        )
    )


def test_selection_defaults_include_expected_statuses_and_order(db_session):
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=10)
    never = _job(db_session, title="Never", status="not_enriched", created_at=old)
    partial = _job(db_session, title="Partial", status="partially_enriched", verified_at=old)
    unresolved = _job(db_session, title="Unresolved", status="unresolved", verified_at=old)
    _job(db_session, title="Enriched", status="enriched", verified_at=now)
    failed = _job(db_session, title="Failed", status="failed", verified_at=old)

    service = JobBatchEnrichmentService(db_session, detail_service=FakeDetailService(db_session))
    selected, missing = service.select_jobs(limit=10)
    selected_failed, _ = service.select_jobs(limit=10, include_failed=True)
    selected_force, _ = service.select_jobs(limit=2, force=True)

    assert [job.id for job in selected] == [never.id, partial.id, unresolved.id]
    assert failed.id in {job.id for job in selected_failed}
    assert len(selected_force) == 2
    assert missing == []


def test_explicit_job_ids_preserve_order_dedupe_and_report_missing(db_session):
    first = _job(db_session, title="First")
    second = _job(db_session, title="Second")
    missing_id = str(uuid4())

    selected, missing = JobBatchEnrichmentService(
        db_session, detail_service=FakeDetailService(db_session)
    ).select_jobs(limit=10, job_ids=[second.id, missing_id, first.id, second.id])

    assert [job.id for job in selected] == [second.id, first.id]
    assert missing == [missing_id]


@pytest.mark.asyncio
async def test_orchestration_continues_after_failure_and_counts_once(db_session):
    first = _job(db_session, title="First")
    failed = _job(db_session, title="Failed One")
    skipped = _job(db_session, title="Unsupported", job_url="https://jobs.example.com/acme")
    fake = FakeDetailService(db_session, fail_ids={failed.id}, statuses={skipped.id: "skipped"})

    result = await JobBatchEnrichmentService(db_session, detail_service=fake).enrich_jobs(
        limit=10,
        job_ids=[first.id, failed.id, skipped.id],
    )

    assert result.jobs_examined == 3
    assert result.jobs_enriched == 1
    assert result.jobs_failed == 1
    assert result.jobs_skipped == 1
    assert [item.job_id for item in result.results] == [first.id, failed.id, skipped.id]
    assert "description" not in result.results[0].fields_updated
    assert JobRepository(db_session).get_by_id(first.id).title == "Full Stack Engineer (TS/SCI)"


@pytest.mark.asyncio
async def test_running_attempt_is_skipped_before_detail_service(db_session):
    job = _job(db_session)
    JobEnrichmentAttemptRepository(db_session).create_attempt(
        JobEnrichmentAttempt(
            job_id=job.id,
            provider="ycombinator_job_page",
            status="running",
            started_at=datetime.now(timezone.utc),
        )
    )
    fake = FakeDetailService(db_session)

    result = await JobBatchEnrichmentService(db_session, detail_service=fake).enrich_jobs(
        limit=10,
        job_ids=[job.id],
    )

    assert result.jobs_skipped == 1
    assert result.results[0].reason == "enrichment_already_running"
    assert fake.calls == []


@pytest.mark.asyncio
async def test_idempotency_default_skips_enriched_and_force_reprocesses(db_session):
    job = _job(db_session)
    fake = FakeDetailService(db_session)
    service = JobBatchEnrichmentService(db_session, detail_service=fake)

    first = await service.enrich_jobs(limit=10)
    second = await service.enrich_jobs(limit=10)
    force = await service.enrich_jobs(limit=10, force=True)

    assert first.jobs_enriched == 1
    assert second.jobs_examined == 0
    assert force.jobs_enriched == 1
    assert JobEnrichmentAttemptRepository(db_session).count_by_job_id(job.id) == 2
    assert JobRepository(db_session).count_jobs() == 1


@pytest.mark.asyncio
async def test_delay_occurs_only_between_provider_backed_jobs(monkeypatch, db_session):
    first = _job(db_session, title="First")
    skipped = _job(db_session, title="Skipped", job_url="https://jobs.example.com/acme")
    second = _job(db_session, title="Second")
    sleeps: list[float] = []

    async def fake_sleep(value):
        sleeps.append(value)

    monkeypatch.setattr("app.services.job_batch_enrichment_service.asyncio.sleep", fake_sleep)
    await JobBatchEnrichmentService(
        db_session,
        detail_service=FakeDetailService(db_session, statuses={skipped.id: "skipped"}),
        delay_ms=25,
    ).enrich_jobs(limit=10, job_ids=[first.id, skipped.id, second.id])

    assert sleeps == [0.025]


@pytest.mark.asyncio
async def test_yc_and_ashby_jobs_process_in_one_batch(db_session):
    yc = _job(db_session, title="YC")
    ashby = _job(db_session, title="Ashby", job_url="https://jobs.ashbyhq.com/lago/backend")
    first_party = _job(db_session, title="First Party", job_url="https://batch.example/careers/backend")
    unsupported = _job(db_session, title="Unsupported", job_url="https://jobs.example.com/acme")
    fake = FakeDetailService(db_session, statuses={unsupported.id: "skipped"})

    result = await JobBatchEnrichmentService(db_session, detail_service=fake).enrich_jobs(
        limit=10,
        job_ids=[yc.id, ashby.id, first_party.id, unsupported.id],
    )

    assert [item.job_id for item in result.results] == [yc.id, ashby.id, first_party.id, unsupported.id]
    assert result.jobs_enriched == 3
    assert result.jobs_skipped == 1
    assert JobRepository(db_session).count_jobs() == 4
