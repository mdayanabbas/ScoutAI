import pytest

from app.enrichment.resolvers import YCombinatorCompanyResolver
from app.models.discovery_candidate import DiscoveryCandidate
from app.utils.enums import (
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoverySource,
)


class FakeYCResolver(YCombinatorCompanyResolver):
    def __init__(self, html: str | None = None, reason: str | None = None):
        super().__init__(
            base_url="https://www.ycombinator.com/companies",
            timeout_seconds=1,
            max_retries=0,
        )
        self.html = html
        self.reason = reason

    async def _fetch_profile(self, profile_url: str):
        return self.html, 200 if self.html else 404, self.reason


def _candidate(raw_payload: dict | None = None, deferred_reason: str | None = None):
    return DiscoveryCandidate(
        discovery_run_id="run-1",
        source=DiscoverySource.HACKER_NEWS,
        source_identifier="hn:1",
        raw_name="Infracost",
        raw_description="",
        normalized_name="Infracost",
        normalized_description="",
        status=DiscoveryCandidateStatus.NORMALIZED,
        decision=DiscoveryDecision.DEFERRED,
        deferred_reason=deferred_reason or "requires_company_domain_enrichment",
        raw_payload=raw_payload or {},
    )


def test_supports_yc_job_candidate_with_external_company_slug():
    candidate = _candidate(
        {
            "url_classification": {
                "platform": "ycombinator",
                "external_company_slug": "infracost",
            }
        }
    )
    resolver = YCombinatorCompanyResolver()

    assert resolver.supports(candidate) is True
    assert resolver.extract_company_slug(candidate) == "infracost"


def test_supports_yc_company_url_without_classification_metadata():
    candidate = _candidate(
        {"url": "https://www.ycombinator.com/companies/hazel-2/jobs/backend-engineer"}
    )
    resolver = YCombinatorCompanyResolver()

    assert resolver.supports(candidate) is True
    assert resolver.extract_company_slug(candidate) == "hazel-2"


def test_rejects_ashby_candidate():
    candidate = _candidate(
        {
            "url_classification": {
                "platform": "ashby",
                "external_company_slug": "lago",
            }
        }
    )
    resolver = YCombinatorCompanyResolver()

    assert resolver.supports(candidate) is False


def test_rejects_show_hn_candidate():
    candidate = _candidate(deferred_reason="requires_startup_qualification")
    resolver = YCombinatorCompanyResolver()

    assert resolver.supports(candidate) is False


def test_rejects_invalid_and_path_traversal_slugs():
    resolver = YCombinatorCompanyResolver()
    invalid = _candidate(
        {
            "url_classification": {
                "platform": "ycombinator",
                "external_company_slug": "bad/slug",
            }
        }
    )
    traversal = _candidate(
        {"url": "https://www.ycombinator.com/companies/%2e%2e/jobs/role"}
    )

    assert resolver.supports(invalid) is False
    assert resolver.supports(traversal) is False


@pytest.mark.asyncio
async def test_resolver_fetches_profile_and_parses_official_site():
    candidate = _candidate(
        {
            "url_classification": {
                "platform": "ycombinator",
                "external_company_slug": "infracost",
            }
        }
    )
    resolver = FakeYCResolver('<a href="https://www.infracost.io">Website</a>')

    result = await resolver.resolve(candidate)

    assert result.resolved is True
    assert result.company_slug == "infracost"
    assert result.profile_url == "https://www.ycombinator.com/companies/infracost"
    assert result.proposed_domain == "infracost.io"


@pytest.mark.asyncio
async def test_resolver_reports_profile_not_found():
    candidate = _candidate(
        {
            "url_classification": {
                "platform": "ycombinator",
                "external_company_slug": "missing",
            }
        }
    )
    resolver = FakeYCResolver(None, "yc_profile_not_found")

    result = await resolver.resolve(candidate)

    assert result.resolved is False
    assert result.reason == "yc_profile_not_found"
