from dataclasses import dataclass

import pytest

from app.jobs.enrichment.models import JobDetailExtractionResult, JobFieldValue
from app.jobs.enrichment.providers.ycombinator_client import YCombinatorJobFetchResult
from app.jobs.enrichment.providers.ycombinator_job_provider import (
    YCombinatorJobEnrichmentProvider,
)
from app.jobs.job_source_detector import JobSourceDetector

YC_URL = "https://www.ycombinator.com/companies/wildcard/jobs/ZSLVaaU-founding-engineer"


@dataclass
class FakeClient:
    result: YCombinatorJobFetchResult

    async def fetch(self, url: str) -> YCombinatorJobFetchResult:
        return self.result


class FakeParser:
    def parse(self, html: str, *, source_url: str, canonical_url: str):
        return JobDetailExtractionResult(
            success=True,
            provider="ycombinator_job_page",
            source_url=source_url,
            canonical_url=canonical_url,
            title=JobFieldValue("Founding Engineer", 0.98, "test"),
            field_confidence={"title": 0.98},
            evidence={"strategy": "test"},
            reason="valid_supported_source",
        )


@pytest.mark.asyncio
async def test_provider_fetches_and_parses_supported_yc_job():
    detection = JobSourceDetector().detect(YC_URL)
    provider = YCombinatorJobEnrichmentProvider(
        client=FakeClient(YCombinatorJobFetchResult(True, YC_URL, final_url=YC_URL, html="<h1>Founding Engineer</h1>", status_code=200, content_length=25)),
        parser=FakeParser(),
    )

    result = await provider.enrich(detection)

    assert result.success is True
    assert result.title.value == "Founding Engineer"
    assert result.evidence["http_status"] == 200
    assert result.evidence["content_length"] == 25


@pytest.mark.asyncio
async def test_provider_rejects_unsupported_source():
    detection = JobSourceDetector().detect("https://jobs.ashbyhq.com/acme")

    result = await YCombinatorJobEnrichmentProvider().enrich(detection)

    assert result.success is False
    assert result.reason == "unsupported_job_source"


@pytest.mark.asyncio
async def test_provider_returns_fetch_failure_reason():
    detection = JobSourceDetector().detect(YC_URL)
    provider = YCombinatorJobEnrichmentProvider(
        client=FakeClient(YCombinatorJobFetchResult(False, YC_URL, reason="yc_job_page_not_found", status_code=404)),
        parser=FakeParser(),
    )

    result = await provider.enrich(detection)

    assert result.success is False
    assert result.reason == "yc_job_page_not_found"
    assert result.evidence["http_status"] == 404
