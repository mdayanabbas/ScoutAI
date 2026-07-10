from dataclasses import dataclass

import pytest

from app.jobs.enrichment.providers.ashby_job_provider import AshbyJobEnrichmentProvider
from app.jobs.enrichment.providers.ashby_models import (
    AshbyPublicJobBoardResponse,
    AshbyPublicJobPosting,
)
from app.jobs.job_source_detector import JobSourceDetector


@dataclass
class FakeJob:
    title: str
    description: str | None = None
    job_url: str | None = "https://jobs.ashbyhq.com/lago"
    source_platform: str | None = "hacker_news"
    role_category: str | None = None
    location: str | None = None


class FakeClient:
    def __init__(self, jobs=None, reason=None):
        self.jobs = jobs or []
        self.reason = reason

    async def list_published_jobs(self, board_slug: str, *, include_compensation: bool = True):
        return AshbyPublicJobBoardResponse(board_slug=board_slug, jobs=self.jobs, status_code=200, response_size=100, reason=self.reason)


def _posting(id: str, title: str, *, listed=True, job_url=None, apply_url=None):
    return AshbyPublicJobPosting(
        id=id,
        title=title,
        is_listed=listed,
        job_url=job_url or f"https://jobs.ashbyhq.com/lago/{id}",
        apply_url=apply_url,
        description_plain=f"{title} role using Python and PostgreSQL.",
        employment_type="FullTime",
    )


@pytest.mark.asyncio
async def test_exact_posting_id_match_enriches():
    detection = JobSourceDetector().detect("https://jobs.ashbyhq.com/lago/backend")
    provider = AshbyJobEnrichmentProvider(client=FakeClient([_posting("backend", "Backend Engineer")]))

    result = await provider.enrich(detection)

    assert result.success is True
    assert result.reason == "exact_ashby_posting_match"
    assert result.title.value == "Backend Engineer"


@pytest.mark.asyncio
async def test_exact_identifier_does_not_fall_back_to_title():
    detection = JobSourceDetector().detect("https://jobs.ashbyhq.com/lago/missing")
    provider = AshbyJobEnrichmentProvider(client=FakeClient([_posting("backend", "Backend Engineer")]))

    result = await provider.enrich(detection, job=FakeJob("Backend Engineer"))

    assert result.success is False
    assert result.reason == "ashby_posting_not_found"


@pytest.mark.asyncio
async def test_board_level_single_posting_selects_automatically():
    detection = JobSourceDetector().detect("https://jobs.ashbyhq.com/lago")
    provider = AshbyJobEnrichmentProvider(client=FakeClient([_posting("backend", "Backend Engineer")]))

    result = await provider.enrich(detection, job=FakeJob("Open Roles"))

    assert result.success is True
    assert result.reason == "unique_ashby_board_match"


@pytest.mark.asyncio
async def test_board_level_specific_title_selects_not_first_array_item():
    detection = JobSourceDetector().detect("https://jobs.ashbyhq.com/lago")
    provider = AshbyJobEnrichmentProvider(
        client=FakeClient([_posting("sales", "Account Executive"), _posting("backend", "Backend Engineer")])
    )

    result = await provider.enrich(detection, job=FakeJob("Backend Engineer"))

    assert result.success is True
    assert result.title.value == "Backend Engineer"


@pytest.mark.asyncio
async def test_generic_board_title_remains_unresolved_with_multiple_postings():
    detection = JobSourceDetector().detect("https://jobs.ashbyhq.com/lago")
    provider = AshbyJobEnrichmentProvider(
        client=FakeClient([_posting("sales", "Account Executive"), _posting("marketing", "Growth Marketing Lead")])
    )

    result = await provider.enrich(detection, job=FakeJob("GTM Team"))

    assert result.success is False
    assert result.reason == "ambiguous_ashby_job_matches"


@pytest.mark.asyncio
async def test_unlisted_postings_are_ignored_and_provider_failures_are_returned():
    detection = JobSourceDetector().detect("https://jobs.ashbyhq.com/lago")
    ignored = AshbyJobEnrichmentProvider(client=FakeClient([_posting("hidden", "Hidden Engineer", listed=False)]))
    failed = AshbyJobEnrichmentProvider(client=FakeClient(reason="ashby_rate_limited"))

    assert (await ignored.enrich(detection, job=FakeJob("Hidden Engineer"))).reason == "ashby_no_published_jobs"
    assert (await failed.enrich(detection, job=FakeJob("Hidden Engineer"))).reason == "ashby_rate_limited"

