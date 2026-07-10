from dataclasses import dataclass, field

import pytest

from app.jobs.enrichment.providers.first_party_job_client import FirstPartyJobPageResponse
from app.jobs.enrichment.providers.first_party_job_provider import FirstPartyJobEnrichmentProvider
from app.jobs.job_source_detector import JobSourceDetector


@dataclass
class FakeCompany:
    name: str = "Example"
    normalized_domain: str = "example.com"


@dataclass
class FakeJob:
    company: FakeCompany | None = field(default_factory=FakeCompany)


class FakeClient:
    def __init__(self, response):
        self.response = response

    async def fetch_job_page(self, url: str, *, company_domain: str):
        return self.response


@pytest.mark.asyncio
async def test_provider_fetches_and_parses_first_party_job():
    detection = JobSourceDetector().detect("https://example.com/jobs/backend", company_domain="example.com")
    html = '<script type="application/ld+json">{"@type":"JobPosting","title":"Backend Engineer","hiringOrganization":{"name":"Example"}}</script>'
    provider = FirstPartyJobEnrichmentProvider(
        client=FakeClient(FirstPartyJobPageResponse("https://example.com/jobs/backend", final_url="https://example.com/jobs/backend", html=html, status_code=200, response_size=len(html), robots_allowed=True))
    )

    result = await provider.enrich(detection, job=FakeJob())

    assert result.success is True
    assert result.provider == "first_party_job_page"
    assert result.title.value == "Backend Engineer"
    assert result.evidence["response_status"] == 200


@pytest.mark.asyncio
async def test_provider_maps_client_failure_and_missing_company():
    detection = JobSourceDetector().detect("https://example.com/jobs/backend", company_domain="example.com")
    failure = FirstPartyJobEnrichmentProvider(
        client=FakeClient(FirstPartyJobPageResponse("https://example.com/jobs/backend", reason="first_party_robots_disallowed", robots_allowed=False))
    )

    assert (await failure.enrich(detection, job=FakeJob())).reason == "first_party_robots_disallowed"
    assert (await FirstPartyJobEnrichmentProvider().enrich(detection, job=FakeJob(company=None))).reason == "unresolved_company"
