import pytest

from app.discovery.sources.hacker_news.adapter import HackerNewsDiscoveryAdapter
from app.discovery.sources.hacker_news.schemas import (
    HackerNewsDiscoveryRequest,
    HackerNewsItem,
)
from app.schemas.discovery import RawStartupCandidate
from app.services.company_service import CompanyService
from app.services.discovery_service import DiscoveryService
from app.utils.enums import (
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoveryRunStatus,
)


def _hn_job_candidate(item_id: int = 123) -> RawStartupCandidate:
    candidate = HackerNewsDiscoveryAdapter()._to_candidate(
        HackerNewsItem(
            id=item_id,
            type="job",
            by="acmefounder",
            time=1_700_000_000,
            title="Acme AI is hiring backend engineers",
            url="https://acme.ai/careers",
            text="Acme AI is hiring backend engineers",
            score=3,
            descendants=0,
        ),
        "jobs",
    )
    assert candidate is not None
    return candidate


def _hn_show_candidate(item_id: int = 456) -> RawStartupCandidate:
    candidate = HackerNewsDiscoveryAdapter()._to_candidate(
        HackerNewsItem(
            id=item_id,
            type="story",
            by="builder",
            time=1_700_000_000,
            title="Show HN: Acme AI - workflow automation",
            url="https://acme.ai",
            text="Acme AI workflow automation for operators",
            score=10,
            descendants=4,
        ),
        "show",
    )
    assert candidate is not None
    return candidate


def _hn_ashby_job_candidate(item_id: int = 789) -> RawStartupCandidate:
    candidate = HackerNewsDiscoveryAdapter()._to_candidate(
        HackerNewsItem(
            id=item_id,
            type="job",
            by="lagohiring",
            time=1_700_000_000,
            title="Lago is hiring",
            url="https://jobs.ashbyhq.com/lago",
            text="Lago is hiring engineers",
            score=2,
            descendants=0,
        ),
        "jobs",
    )
    assert candidate is not None
    return candidate


@pytest.mark.asyncio
async def test_hacker_news_discovery_creates_company(db_session, monkeypatch):
    async def discover(self, request):
        self.fetched_item_count = 1
        return [_hn_job_candidate()]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)

    result = await DiscoveryService(db_session).run_hacker_news_discovery(
        HackerNewsDiscoveryRequest(feeds=["jobs"], limit=1)
    )

    assert result.run.status == DiscoveryRunStatus.SUCCESS
    assert result.run.candidates_rejected == 0
    assert result.run.companies_created == 1
    assert result.fetched_item_count == 1
    assert result.candidates[0].status == DiscoveryCandidateStatus.INGESTED
    assert result.candidates[0].decision == DiscoveryDecision.CREATED_COMPANY
    assert result.candidates[0].matched_company_id is not None
    assert result.candidates[0].evidence[0].source_url.endswith("id=123")


@pytest.mark.asyncio
async def test_hacker_news_discovery_matches_existing_company(db_session, monkeypatch):
    CompanyService(db_session).create_company(
        {"name": "Acme Existing", "website_url": "https://acme.ai"}
    )

    async def discover(self, request):
        return [_hn_job_candidate()]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)

    result = await DiscoveryService(db_session).run_hacker_news_discovery(
        HackerNewsDiscoveryRequest(feeds=["jobs"], limit=1)
    )

    assert result.run.companies_created == 0
    assert result.run.companies_matched == 1
    assert result.run.candidates_rejected == 0
    assert result.candidates[0].decision == DiscoveryDecision.MATCHED_EXISTING_COMPANY


@pytest.mark.asyncio
async def test_repeated_hacker_news_runs_do_not_duplicate_companies(db_session, monkeypatch):
    async def discover(self, request):
        return [_hn_job_candidate()]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)
    service = DiscoveryService(db_session)

    first = await service.run_hacker_news_discovery(HackerNewsDiscoveryRequest(limit=1))
    second = await service.run_hacker_news_discovery(HackerNewsDiscoveryRequest(limit=1))

    assert first.run.companies_created == 1
    assert first.run.companies_matched == 0
    assert second.run.companies_created == 0
    assert second.run.companies_matched == 1
    assert service.company_repository.count_companies() == 1


@pytest.mark.asyncio
async def test_hacker_news_show_candidate_with_first_party_url_is_deferred(
    db_session, monkeypatch
):
    async def discover(self, request):
        return [_hn_show_candidate()]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)

    result = await DiscoveryService(db_session).run_hacker_news_discovery(
        HackerNewsDiscoveryRequest(feeds=["show"], limit=1)
    )

    assert result.run.status == DiscoveryRunStatus.SUCCESS
    assert result.run.companies_created == 0
    assert result.run.candidates_deferred == 1
    assert result.run.candidates_rejected == 0
    assert result.candidates[0].decision == DiscoveryDecision.DEFERRED
    assert result.candidates[0].deferred_reason == "requires_startup_qualification"


@pytest.mark.asyncio
async def test_hacker_news_platform_job_candidate_is_deferred(
    db_session, monkeypatch
):
    async def discover(self, request):
        return [_hn_ashby_job_candidate()]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)

    result = await DiscoveryService(db_session).run_hacker_news_discovery(
        HackerNewsDiscoveryRequest(feeds=["jobs"], limit=1)
    )

    assert result.run.status == DiscoveryRunStatus.SUCCESS
    assert result.run.companies_created == 0
    assert result.run.candidates_deferred == 1
    assert result.run.candidates_rejected == 0
    assert result.candidates[0].decision == DiscoveryDecision.DEFERRED
    assert result.candidates[0].deferred_reason == "requires_company_domain_enrichment"


@pytest.mark.asyncio
async def test_complete_hacker_news_adapter_failure_marks_run_failed(db_session, monkeypatch):
    async def discover(self, request):
        raise RuntimeError("hn unavailable")

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)

    result = await DiscoveryService(db_session).run_hacker_news_discovery(
        HackerNewsDiscoveryRequest(limit=1)
    )

    assert result.run.status == DiscoveryRunStatus.FAILED
    assert result.run.error_message == "hn unavailable"
