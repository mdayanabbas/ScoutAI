from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.jobs.enrichment.models import JobDetailExtractionResult, JobFieldValue
from app.models.company import Company
from app.models.job import Job
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_enrichment_attempt_repository import (
    JobEnrichmentAttemptRepository,
)
from app.repositories.job_repository import JobRepository
from app.services.job_detail_enrichment_service import JobDetailEnrichmentService
from app.utils.enums import JobStatus

YC_URL = "https://www.ycombinator.com/companies/hazel-2/jobs/3epPWgu-full-stack-engineer-ts-sci"


class FakeProvider:
    def __init__(self, result: JobDetailExtractionResult | Exception):
        self.result = result

    async def enrich(self, detection, **kwargs):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _company(db_session):
    token = uuid4().hex[:8]
    return CompanyRepository(db_session).create_company(
        Company(
            name=f"YC Co {token}",
            normalized_domain=f"yc-{token}.example",
            website_url=f"https://yc-{token}.example",
        )
    )


def _job(db_session, *, title="Open Roles", description="Apply on YC", job_url=YC_URL):
    company = _company(db_session)
    return JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            title=title,
            normalized_title=title.lower(),
            description=description,
            job_url=job_url,
            source_platform="hacker_news",
            status=JobStatus.ACTIVE,
            first_seen_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )


def _parsed(title="Full Stack Engineer (TS/SCI)", *, success=True, reason="valid_supported_source"):
    return JobDetailExtractionResult(
        success=success,
        provider="ycombinator_job_page",
        source_url=YC_URL,
        canonical_url=YC_URL,
        title=JobFieldValue(title, 0.98, "h1"),
        description=JobFieldValue("About the role\n" + "Build systems. " * 30, 0.95, "main"),
        role_category=JobFieldValue("full_stack_engineer", 0.95, "classifier"),
        location=JobFieldValue("New York, NY / Remote", 0.95, "label"),
        remote_type=JobFieldValue("remote_worldwide", 0.9, "label"),
        employment_type=JobFieldValue("full_time", 0.95, "label"),
        salary_min=JobFieldValue(130000, 0.98, "label"),
        salary_max=JobFieldValue(250000, 0.98, "label"),
        salary_currency=JobFieldValue("USD", 0.98, "label"),
        salary_text=JobFieldValue("$130K - $250K", 0.95, "label"),
        required_skills=JobFieldValue(["TypeScript", "PostgreSQL"], 0.95, "label"),
        technologies=JobFieldValue(["TypeScript", "PostgreSQL"], 0.95, "label"),
        apply_url=JobFieldValue(YC_URL, 0.75, "canonical"),
        field_confidence={
            "title": 0.98,
            "description": 0.95,
            "role_category": 0.95,
            "location": 0.95,
            "employment_type": 0.95,
            "salary_min": 0.98,
        },
        evidence={"strategy": "test", "overall_confidence": 0.95},
        reason=reason,
    )


def _ashby_parsed(title="Backend Engineer", *, success=True, reason="exact_ashby_posting_match"):
    url = "https://jobs.ashbyhq.com/lago/backend"
    return JobDetailExtractionResult(
        success=success,
        provider="ashby_public_job_board",
        source_url=url,
        canonical_url=url,
        title=JobFieldValue(title, 1.0, "ashby_api_title"),
        description=JobFieldValue("Build billing systems. " * 20, 0.95, "ashby_description"),
        role_category=JobFieldValue("backend_engineer", 0.95, "classifier"),
        location=JobFieldValue("Remote", 0.94, "ashby_location"),
        remote_type=JobFieldValue("remote_worldwide", 0.95, "ashby_workplace_type"),
        employment_type=JobFieldValue("full_time", 0.95, "ashby_employment_type"),
        job_url=JobFieldValue(url, 0.98, "ashby_job_url"),
        apply_url=JobFieldValue(url, 0.9, "ashby_apply_url"),
        field_confidence={
            "title": 1.0,
            "description": 0.95,
            "role_category": 0.95,
            "location": 0.94,
            "employment_type": 0.95,
            "job_url": 0.98,
        },
        evidence={"strategy": "ashby_test", "overall_confidence": 0.96},
        reason=reason,
    )


def _first_party_parsed(title="Backend Engineer", *, success=True, reason="first_party_job_page_enriched"):
    url = "https://first-party.example/careers/backend-engineer"
    return JobDetailExtractionResult(
        success=success,
        provider="first_party_job_page",
        source_url=url,
        canonical_url=url,
        title=JobFieldValue(title, 1.0, "jobposting_title"),
        description=JobFieldValue("Build first-party systems. " * 20, 0.95, "jobposting_description"),
        role_category=JobFieldValue("backend_engineer", 0.95, "classifier"),
        location=JobFieldValue("Remote", 0.9, "location"),
        remote_type=JobFieldValue("remote_worldwide", 0.9, "location"),
        employment_type=JobFieldValue("full_time", 0.95, "employment_type"),
        job_url=JobFieldValue(url, 0.95, "canonical_first_party_url"),
        field_confidence={
            "title": 1.0,
            "description": 0.95,
            "role_category": 0.95,
            "location": 0.9,
            "employment_type": 0.95,
        },
        evidence={"strategy": "first_party_test", "overall_confidence": 0.96},
        reason=reason,
    )


@pytest.mark.asyncio
async def test_service_enriches_yc_job_and_marks_attempt_succeeded(db_session):
    job = _job(db_session, title="Open Roles")
    original_company_id = job.company_id
    original_candidate_id = job.discovery_candidate_id
    original_first_seen_at = job.first_seen_at
    original_created_at = job.created_at

    result = await JobDetailEnrichmentService(
        db_session, yc_provider=FakeProvider(_parsed())
    ).enrich_job(job.id)

    updated = JobRepository(db_session).get_by_id(job.id)
    attempts = JobEnrichmentAttemptRepository(db_session).list_by_job_id(job.id)
    assert result.status == "enriched"
    assert updated.title == "Full Stack Engineer (TS/SCI)"
    assert updated.normalized_title == "full stack engineer (ts/sci)"
    assert updated.description.startswith("About the role")
    assert updated.role_category == "full_stack_engineer"
    assert updated.salary_min == 130000
    assert updated.required_skills_json == ["TypeScript", "PostgreSQL"]
    assert updated.company_id == original_company_id
    assert updated.discovery_candidate_id == original_candidate_id
    assert updated.first_seen_at == original_first_seen_at
    assert updated.created_at == original_created_at
    assert updated.last_verified_at is not None
    assert updated.enriched_at is not None
    assert attempts[0].status == "succeeded"
    assert attempts[0].field_confidence_json["title"] == 0.98
    assert "raw_html" not in (attempts[0].evidence_json or {})


@pytest.mark.asyncio
async def test_service_preserves_precise_title_when_slug_fallback_is_weak(db_session):
    job = _job(db_session, title="Staff Platform Engineer", description="Rich description " * 40)
    weak = _parsed("Full Stack Engineer Ts Sci")
    weak = JobDetailExtractionResult(**{**weak.__dict__, "title": JobFieldValue("Full Stack Engineer Ts Sci", 0.7, "url_slug")})

    await JobDetailEnrichmentService(db_session, yc_provider=FakeProvider(weak)).enrich_job(job.id)

    updated = JobRepository(db_session).get_by_id(job.id)
    assert updated.title == "Staff Platform Engineer"
    assert updated.description.startswith("Rich description")


@pytest.mark.asyncio
async def test_service_marks_partial_unresolved_failed_and_preserves_attempt_history(db_session):
    partial_job = _job(db_session, title="Hiring")
    partial = _parsed("Founding Engineer")
    partial = JobDetailExtractionResult(
        **{
            **partial.__dict__,
            "description": None,
            "employment_type": None,
            "location": None,
            "field_confidence": {"title": 0.98, "role_category": 0.95},
        }
    )
    partial_result = await JobDetailEnrichmentService(db_session, yc_provider=FakeProvider(partial)).enrich_job(partial_job.id)

    unresolved_job = _job(db_session, title="Open Roles")
    unresolved = JobDetailExtractionResult(
        success=False,
        provider="ycombinator_job_page",
        source_url=YC_URL,
        canonical_url=YC_URL,
        reason="yc_job_data_missing",
    )
    unresolved_result = await JobDetailEnrichmentService(db_session, yc_provider=FakeProvider(unresolved)).enrich_job(unresolved_job.id)

    failed_job = _job(db_session, title="Open Roles")
    failed_result = await JobDetailEnrichmentService(db_session, yc_provider=FakeProvider(RuntimeError("boom"))).enrich_job(failed_job.id)

    assert partial_result.status == "partially_enriched"
    assert unresolved_result.status == "unresolved"
    assert failed_result.status == "failed"
    assert JobEnrichmentAttemptRepository(db_session).list_by_job_id(partial_job.id)[0].status == "partial"
    assert JobEnrichmentAttemptRepository(db_session).list_by_job_id(unresolved_job.id)[0].status == "unresolved"
    assert JobEnrichmentAttemptRepository(db_session).list_by_job_id(failed_job.id)[0].status == "failed"

    await JobDetailEnrichmentService(db_session, yc_provider=FakeProvider(_parsed("Founding Engineer"))).enrich_job(partial_job.id)
    assert len(JobEnrichmentAttemptRepository(db_session).list_by_job_id(partial_job.id)) == 2


@pytest.mark.asyncio
async def test_service_skips_unsupported_jobs_without_marking_failed(db_session):
    job = _job(db_session, job_url="https://jobs.example.com/acme")

    result = await JobDetailEnrichmentService(db_session, yc_provider=FakeProvider(_parsed())).enrich_job(job.id)

    assert result.status == "skipped"
    assert result.reason == "unsupported_provider_for_current_brick"
    assert JobRepository(db_session).get_by_id(job.id).enrichment_status == "not_enriched"


@pytest.mark.asyncio
async def test_service_enriches_ashby_job_and_upgrades_board_url(db_session):
    job = _job(db_session, title="Open Roles", job_url="https://jobs.ashbyhq.com/lago")

    result = await JobDetailEnrichmentService(
        db_session,
        ashby_provider=FakeProvider(_ashby_parsed()),
    ).enrich_job(job.id)

    updated = JobRepository(db_session).get_by_id(job.id)
    attempts = JobEnrichmentAttemptRepository(db_session).list_by_job_id(job.id)
    assert result.status == "enriched"
    assert result.provider == "ashby_public_job_board"
    assert updated.title == "Backend Engineer"
    assert updated.job_url == "https://jobs.ashbyhq.com/lago/backend"
    assert attempts[0].provider == "ashby_public_job_board"
    assert attempts[0].status == "succeeded"


@pytest.mark.asyncio
async def test_service_marks_ashby_ambiguity_unresolved_and_leaves_job_unchanged(db_session):
    job = _job(db_session, title="GTM Team", job_url="https://jobs.ashbyhq.com/lago")
    unresolved = _ashby_parsed(success=False, reason="ambiguous_ashby_job_matches")

    result = await JobDetailEnrichmentService(
        db_session,
        ashby_provider=FakeProvider(unresolved),
    ).enrich_job(job.id)

    updated = JobRepository(db_session).get_by_id(job.id)
    attempts = JobEnrichmentAttemptRepository(db_session).list_by_job_id(job.id)
    assert result.status == "unresolved"
    assert updated.title == "GTM Team"
    assert updated.job_url == "https://jobs.ashbyhq.com/lago"
    assert attempts[0].status == "unresolved"


@pytest.mark.asyncio
async def test_service_enriches_first_party_job_and_preserves_provenance(db_session):
    token = uuid4().hex[:8]
    domain = f"first-party-{token}.example"
    company = CompanyRepository(db_session).create_company(
        Company(
            name=f"First Party {token}",
            normalized_domain=domain,
            website_url=f"https://{domain}",
        )
    )
    job = JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            title="Open Roles",
            normalized_title="open roles",
            description="We are hiring.",
            job_url=f"https://{domain}/careers/backend-engineer",
            source_platform="hacker_news",
            status=JobStatus.ACTIVE,
            first_seen_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )
    original_company_id = job.company_id
    original_candidate_id = job.discovery_candidate_id
    original_first_seen_at = job.first_seen_at

    result = await JobDetailEnrichmentService(
        db_session,
        first_party_provider=FakeProvider(_first_party_parsed()),
    ).enrich_job(job.id)

    updated = JobRepository(db_session).get_by_id(job.id)
    attempts = JobEnrichmentAttemptRepository(db_session).list_by_job_id(job.id)
    assert result.status == "enriched"
    assert result.provider == "first_party_job_page"
    assert updated.title == "Backend Engineer"
    assert updated.description.startswith("Build first-party")
    assert updated.company_id == original_company_id
    assert updated.discovery_candidate_id == original_candidate_id
    assert updated.first_seen_at == original_first_seen_at
    assert updated.last_verified_at is not None
    assert updated.enriched_at is not None
    assert attempts[0].provider == "first_party_job_page"
    assert "raw_html" not in str(attempts[0].evidence_json)


@pytest.mark.asyncio
async def test_service_first_party_listing_page_unresolved_leaves_job_unchanged(db_session):
    token = uuid4().hex[:8]
    domain = f"first-party-{token}.example"
    company = CompanyRepository(db_session).create_company(
        Company(
            name=f"First Party {token}",
            normalized_domain=domain,
            website_url=f"https://{domain}",
        )
    )
    job = JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            title="Open Roles",
            normalized_title="open roles",
            description="Short HN sentence.",
            job_url=f"https://{domain}/careers",
            source_platform="hacker_news",
            status=JobStatus.ACTIVE,
        )
    )
    unresolved = _first_party_parsed(success=False, reason="first_party_listing_page_requires_expansion")

    result = await JobDetailEnrichmentService(
        db_session,
        first_party_provider=FakeProvider(unresolved),
    ).enrich_job(job.id)

    updated = JobRepository(db_session).get_by_id(job.id)
    assert result.status == "unresolved"
    assert updated.title == "Open Roles"
    assert updated.description == "Short HN sentence."


@pytest.mark.asyncio
async def test_current_example_titles_are_replaced(db_session):
    examples = [
        ("Largest Government Contract", "Full Stack Engineer (TS/SCI)", "full_stack_engineer"),
        ("Open Roles", "Founding Account Executive", "sales"),
        ("Open Roles", "Founding Product Engineer", "product_engineer"),
        ("Open Roles", "Developer Advocate & Partnerships (DevRel)", "developer_advocate"),
        ("Open Roles", "Founding Engineer", "software_engineer"),
    ]

    for current, extracted, category in examples:
        job = _job(db_session, title=current)
        parsed = _parsed(extracted)
        parsed = JobDetailExtractionResult(
            **{**parsed.__dict__, "role_category": JobFieldValue(category, 0.95, "classifier")}
        )
        await JobDetailEnrichmentService(db_session, yc_provider=FakeProvider(parsed)).enrich_job(job.id)
        updated = JobRepository(db_session).get_by_id(job.id)
        assert updated.title == extracted
        assert updated.role_category == category
