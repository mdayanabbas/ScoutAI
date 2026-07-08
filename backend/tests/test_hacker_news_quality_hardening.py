import pytest

from app.discovery.sources.hacker_news.adapter import HackerNewsDiscoveryAdapter
from app.discovery.sources.hacker_news.schemas import HackerNewsDiscoveryRequest
from app.schemas.discovery import RawStartupCandidate
from app.services.discovery_service import DiscoveryService
from app.utils.enums import DiscoveryDecision, DiscoveryRunStatus


def _hn_candidate(
    item_id: int,
    name: str,
    website_url: str | None,
    feed: str,
    classification: dict,
) -> RawStartupCandidate:
    return RawStartupCandidate(
        source_identifier=f"hn:{item_id}",
        name=name,
        website_url=website_url,
        description=f"{name} HN post",
        evidence=[
            {
                "evidence_type": "hiring_post" if feed == "jobs" else "launch_post",
                "source_url": f"https://news.ycombinator.com/item?id={item_id}",
            }
        ],
        raw_payload={
            "id": item_id,
            "feed": feed,
            "url_classification": classification,
        },
    )


@pytest.mark.asyncio
async def test_unrelated_github_repositories_are_not_duplicates(db_session, monkeypatch):
    async def discover(self, request):
        return [
            _hn_candidate(
                1,
                "Kastor",
                None,
                "show",
                {
                    "url_type": "github_repository",
                    "platform": "github",
                    "external_repository": "weirdguy/kastor",
                },
            ),
            _hn_candidate(
                2,
                "Rowboat",
                None,
                "show",
                {
                    "url_type": "github_repository",
                    "platform": "github",
                    "external_repository": "rowboatlabs/rowboat",
                },
            ),
        ]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)

    result = await DiscoveryService(db_session).run_hacker_news_discovery(
        HackerNewsDiscoveryRequest(limit=2)
    )

    assert result.run.status == DiscoveryRunStatus.SUCCESS
    assert result.run.candidates_deferred == 2
    assert result.run.candidates_rejected == 0


@pytest.mark.asyncio
async def test_hacker_news_job_with_first_party_domain_creates_company(
    db_session, monkeypatch
):
    async def discover(self, request):
        return [
            _hn_candidate(
                1,
                "9 Mothers",
                "https://9mothers.com/careers",
                "jobs",
                {
                    "url_type": "first_party",
                    "first_party_url": "https://9mothers.com/careers",
                    "is_first_party_company_domain": True,
                },
            )
        ]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)

    result = await DiscoveryService(db_session).run_hacker_news_discovery(
        HackerNewsDiscoveryRequest(limit=1)
    )

    assert result.run.status == DiscoveryRunStatus.SUCCESS
    assert result.run.companies_created == 1
    assert result.candidates[0].normalized_domain == "9mothers.com"


@pytest.mark.asyncio
async def test_platform_job_candidates_are_deferred(db_session, monkeypatch):
    async def discover(self, request):
        return [
            _hn_candidate(
                1,
                "Lago",
                None,
                "jobs",
                {
                    "url_type": "ashby_job",
                    "platform": "ashby",
                    "external_company_slug": "lago",
                },
            ),
            _hn_candidate(
                2,
                "Infracost",
                None,
                "jobs",
                {
                    "url_type": "yc_job",
                    "platform": "ycombinator",
                    "external_company_slug": "infracost",
                },
            ),
            _hn_candidate(
                3,
                "Supabase",
                None,
                "jobs",
                {
                    "url_type": "greenhouse_job",
                    "platform": "greenhouse",
                    "external_company_slug": "supabase",
                },
            ),
        ]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)

    result = await DiscoveryService(db_session).run_hacker_news_discovery(
        HackerNewsDiscoveryRequest(limit=3)
    )

    assert result.run.status == DiscoveryRunStatus.SUCCESS
    assert result.run.candidates_deferred == 3
    assert all(candidate.decision == DiscoveryDecision.DEFERRED for candidate in result.candidates)
    assert all(
        candidate.deferred_reason == "requires_company_domain_enrichment"
        for candidate in result.candidates
    )


@pytest.mark.asyncio
async def test_show_hn_first_party_url_is_deferred_for_qualification(
    db_session, monkeypatch
):
    async def discover(self, request):
        return [
            _hn_candidate(
                1,
                "Acme",
                "https://acme.ai",
                "show",
                {
                    "url_type": "first_party",
                    "first_party_url": "https://acme.ai",
                    "is_first_party_company_domain": True,
                },
            )
        ]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)

    result = await DiscoveryService(db_session).run_hacker_news_discovery(
        HackerNewsDiscoveryRequest(limit=1)
    )

    assert result.run.status == DiscoveryRunStatus.SUCCESS
    assert result.run.companies_created == 0
    assert result.run.candidates_deferred == 1
    assert result.candidates[0].deferred_reason == "requires_startup_qualification"


@pytest.mark.asyncio
async def test_deferred_plus_rejected_candidates_are_partial_success(
    db_session, monkeypatch
):
    async def discover(self, request):
        return [
            _hn_candidate(
                1,
                "Lago",
                None,
                "jobs",
                {
                    "url_type": "ashby_job",
                    "platform": "ashby",
                    "external_company_slug": "lago",
                },
            ),
            RawStartupCandidate(
                source_identifier="hn:2",
                name="Bad URL",
                website_url="not a domain",
                raw_payload={"id": 2, "feed": "jobs"},
            ),
        ]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)

    result = await DiscoveryService(db_session).run_hacker_news_discovery(
        HackerNewsDiscoveryRequest(limit=2)
    )

    assert result.run.status == DiscoveryRunStatus.PARTIAL_SUCCESS
    assert result.run.candidates_deferred == 1
    assert result.run.candidates_rejected == 1
