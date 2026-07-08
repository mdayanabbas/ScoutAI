import pytest

from app.discovery.sources.hacker_news.adapter import HackerNewsDiscoveryAdapter
from app.discovery.sources.hacker_news.schemas import HackerNewsDiscoveryRequest
from app.schemas.discovery import DiscoveryEvidenceInput, RawStartupCandidate
from app.services.company_service import CompanyService
from app.services.discovery_service import DiscoveryService
from app.utils.enums import DiscoveryDecision, DiscoveryRunStatus


def _hn_candidate(item_id: int = 1) -> RawStartupCandidate:
    return RawStartupCandidate(
        source_identifier=f"hn:{item_id}",
        name="Acme AI",
        website_url="https://acme.ai",
        description="Show HN launch.",
        evidence=[
            DiscoveryEvidenceInput(
                evidence_type="launch_post",
                source_url=f"https://news.ycombinator.com/item?id={item_id}",
                title="Show HN: Acme AI",
                excerpt="Show HN launch.",
            )
        ],
        raw_payload={"id": item_id, "feed": "show"},
    )


@pytest.mark.asyncio
async def test_hacker_news_discovery_creates_company(db_session, monkeypatch):
    async def discover(self, request):
        self.fetched_item_count = 1
        return [_hn_candidate()]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)

    result = await DiscoveryService(db_session).run_hacker_news_discovery(
        HackerNewsDiscoveryRequest(feeds=["show"], limit=1)
    )

    assert result.run.status == DiscoveryRunStatus.SUCCESS
    assert result.run.companies_created == 1
    assert result.fetched_item_count == 1
    assert result.candidates[0].decision == DiscoveryDecision.CREATED_COMPANY
    assert result.candidates[0].evidence[0].source_url.endswith("id=1")


@pytest.mark.asyncio
async def test_hacker_news_discovery_matches_existing_company(db_session, monkeypatch):
    CompanyService(db_session).create_company(
        {"name": "Acme Existing", "website_url": "https://acme.ai"}
    )

    async def discover(self, request):
        return [_hn_candidate()]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)

    result = await DiscoveryService(db_session).run_hacker_news_discovery(
        HackerNewsDiscoveryRequest(feeds=["show"], limit=1)
    )

    assert result.run.companies_matched == 1
    assert result.candidates[0].decision == DiscoveryDecision.MATCHED_EXISTING_COMPANY


@pytest.mark.asyncio
async def test_repeated_hacker_news_runs_do_not_duplicate_companies(db_session, monkeypatch):
    async def discover(self, request):
        return [_hn_candidate()]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)
    service = DiscoveryService(db_session)

    first = await service.run_hacker_news_discovery(HackerNewsDiscoveryRequest(limit=1))
    second = await service.run_hacker_news_discovery(HackerNewsDiscoveryRequest(limit=1))

    assert first.run.companies_created == 1
    assert second.run.companies_matched == 1
    assert service.company_repository.count_companies() == 1


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
