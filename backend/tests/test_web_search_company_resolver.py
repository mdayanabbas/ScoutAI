from dataclasses import dataclass

import pytest

from app.enrichment.company_identity_checker import HomepageMetadata
from app.enrichment.domain_validator import DomainValidationResult
from app.enrichment.resolvers.web_search_company_resolver import WebSearchCompanyResolver
from app.models.discovery_candidate import DiscoveryCandidate
from app.search.providers.base import WebSearchResponse, WebSearchResult
from app.search.providers.factory import create_web_search_provider
from app.search.providers.tavily import TavilySearchProvider
from app.utils.enums import DiscoveryCandidateStatus, DiscoveryDecision, DiscoverySource


@dataclass
class FakeProvider:
    responses: dict[str, tuple[WebSearchResult, ...]]
    name: str = "fake"

    async def search(self, query: str, *, count: int = 10):
        return WebSearchResponse(self.name, query, True, self.responses.get(query, ()), 200)


class FakeValidator:
    async def validate(self, value: str):
        domain = value.replace("https://", "").split("/", 1)[0]
        return DomainValidationResult(True, value, f"https://{domain}", domain, 200)


class Resolver(WebSearchCompanyResolver):
    async def _fetch_homepage_metadata(self, url: str):
        if "getlago" in url:
            return HomepageMetadata(url=url, title="Lago")
        return HomepageMetadata(url=url, title=url.replace("https://", "").split(".")[0].title())


def _candidate(name="Supabase", raw_payload=None):
    return DiscoveryCandidate(
        discovery_run_id="run",
        source=DiscoverySource.HACKER_NEWS,
        source_identifier=f"hn:{name}",
        raw_name=name,
        raw_description=f"{name} is hiring",
        normalized_name=name,
        normalized_description=f"{name} is hiring",
        status=DiscoveryCandidateStatus.NORMALIZED,
        decision=DiscoveryDecision.DEFERRED,
        deferred_reason="requires_company_domain_enrichment",
        raw_payload=raw_payload or {"title": f"{name} is hiring a Software Engineer"},
    )


def _resolver(provider):
    resolver = Resolver(provider=provider, validator=FakeValidator())
    resolver.enabled = True
    return resolver


def test_query_construction_supabase_includes_exact_name_and_context():
    resolver = _resolver(FakeProvider({}))
    candidate = _candidate(
        "Supabase",
        {
            "title": "Supabase is hiring a Software Engineer",
            "url_classification": {"platform": "ashby", "external_company_slug": "supabase"},
        },
    )

    queries = resolver.build_queries(candidate)

    assert any('"Supabase"' in query for query in queries)
    assert any("Ashby jobs official" in query for query in queries)
    assert len(queries) <= 2


def test_provider_selection_uses_tavily_when_configured(monkeypatch):
    class Settings:
        WEB_SEARCH_PROVIDER = "tavily"

    monkeypatch.setattr("app.search.providers.factory.get_settings", lambda: Settings())

    provider = create_web_search_provider()

    assert isinstance(provider, TavilySearchProvider)


def test_query_construction_lago_includes_yc_context():
    resolver = _resolver(FakeProvider({}))
    candidate = _candidate(
        "Lago",
        {
            "yc_batch": "S21",
            "url_classification": {"platform": "ycombinator", "external_company_slug": "lago"},
        },
    )

    queries = resolver.build_queries(candidate)

    assert any('"Lago"' in query and "YC S21" in query for query in queries)


def test_filtering_rejects_platforms_and_accepts_first_party_root():
    resolver = _resolver(FakeProvider({}))
    candidate = _candidate("Supabase")

    assert resolver.score_result(candidate, WebSearchResult("Supabase", "https://supabase.com"))
    assert resolver.score_result(candidate, WebSearchResult("Supabase", "https://linkedin.com/company/supabase")) is None
    assert resolver.score_result(candidate, WebSearchResult("Supabase", "https://www.ycombinator.com/companies/supabase")) is None
    assert resolver.score_result(candidate, WebSearchResult("Supabase", "https://jobs.ashbyhq.com/supabase")) is None
    assert resolver.score_result(candidate, WebSearchResult("Supabase", "https://crunchbase.com/organization/supabase")) is None
    assert resolver.score_result(candidate, WebSearchResult("Supabase raises", "https://techcrunch.com/supabase")) is None


@pytest.mark.asyncio
async def test_exact_name_root_homepage_wins_and_rank_one_does_not():
    candidate = _candidate("Supabase")
    resolver = _resolver(FakeProvider({}))
    resolver.max_queries = 3
    queries = resolver.build_queries(candidate)
    provider = FakeProvider(
        {
            queries[0]: (
                WebSearchResult("Supabase profile", "https://crunchbase.com/organization/supabase", rank=1),
                WebSearchResult("Supabase | The Postgres Development Platform", "https://supabase.com", "Supabase official", rank=2),
            ),
            queries[1]: (
                WebSearchResult("Supabase", "https://supabase.com", "Supabase official website", rank=1),
            ),
        }
    )
    resolver = _resolver(provider)

    result = await resolver.resolve(candidate)

    assert result.resolved
    assert result.proposed_domain == "supabase.com"


@pytest.mark.asyncio
async def test_lago_style_tavily_results_resolve():
    candidate = _candidate(
        "Lago",
        {
            "yc_batch": "S21",
            "url_classification": {"platform": "ycombinator", "external_company_slug": "lago"},
        },
    )
    queries = _resolver(FakeProvider({})).build_queries(candidate)
    provider = FakeProvider(
        {
            queries[0]: (
                WebSearchResult(
                    "Lago | Open-source billing platform",
                    "https://getlago.com",
                    "Lago official website",
                    rank=1,
                    source="tavily",
                    provider_score=0.92,
                ),
            ),
            queries[1]: (
                WebSearchResult(
                    "Lago",
                    "https://www.getlago.com",
                    "Lago YC S21 billing startup",
                    rank=1,
                    source="tavily",
                    provider_score=0.88,
                ),
            ),
        }
    )
    resolver = _resolver(provider)

    result = await resolver.resolve(candidate)

    assert result.resolved
    assert result.proposed_domain == "getlago.com"


def test_same_domain_results_consolidate_and_ambiguous_domains_remain_unresolved():
    resolver = _resolver(FakeProvider({}))
    candidate = _candidate("Lago")
    first = resolver.score_result(candidate, WebSearchResult("Lago", "https://www.getlago.com", "Lago official"), query="q1")
    second = resolver.score_result(candidate, WebSearchResult("Lago", "https://docs.getlago.com", "Lago docs"), query="q2")
    assert first and second

    selected, reason = resolver.select_domain(candidate, [first, second])
    assert selected
    assert selected.domain == "getlago.com"

    other = resolver.score_result(
        candidate,
        WebSearchResult("Lago", "https://lago.ai", "Lago official", rank=1),
        query="q1",
    )
    assert other
    selected, reason = resolver.select_domain(candidate, [first, other])
    assert selected is None
    assert reason == "ambiguous_search_company_domains"
