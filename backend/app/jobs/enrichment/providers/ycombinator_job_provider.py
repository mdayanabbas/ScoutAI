import logging

from app.jobs.enrichment.models import JobDetailExtractionResult
from app.jobs.enrichment.parsers.ycombinator_job_parser import YCombinatorJobParser
from app.jobs.enrichment.providers.ycombinator_client import YCombinatorJobClient
from app.jobs.source_detection import JobSourceDetectionResult
from app.utils.enums import JobSourceType

logger = logging.getLogger(__name__)

PROVIDER_NAME = "ycombinator_job_page"


class YCombinatorJobEnrichmentProvider:
    provider_name = PROVIDER_NAME

    def __init__(
        self,
        *,
        client: YCombinatorJobClient | None = None,
        parser: YCombinatorJobParser | None = None,
    ) -> None:
        self.client = client or YCombinatorJobClient()
        self.parser = parser or YCombinatorJobParser()

    async def enrich(
        self, detection: JobSourceDetectionResult
    ) -> JobDetailExtractionResult:
        if detection.source_type != JobSourceType.YCOMBINATOR_JOB or not detection.canonical_url:
            return JobDetailExtractionResult(
                success=False,
                provider=self.provider_name,
                source_url=detection.original_url or "",
                canonical_url=detection.canonical_url or "",
                reason="unsupported_job_source",
            )
        fetched = await self.client.fetch(detection.canonical_url)
        if not fetched.success or fetched.html is None:
            logger.info(
                "YC page rejected",
                extra={"reason": fetched.reason, "status_code": fetched.status_code},
            )
            return JobDetailExtractionResult(
                success=False,
                provider=self.provider_name,
                source_url=detection.canonical_url,
                canonical_url=detection.canonical_url,
                reason=fetched.reason or "yc_job_page_fetch_failed",
                evidence={
                    "http_status": fetched.status_code,
                    "redirect_count": fetched.redirect_count,
                    "content_length": fetched.content_length,
                },
            )
        parsed = self.parser.parse(
            fetched.html,
            source_url=fetched.final_url or fetched.url,
            canonical_url=detection.canonical_url,
        )
        evidence = {
            **parsed.evidence,
            "http_status": fetched.status_code,
            "redirect_count": fetched.redirect_count,
            "content_length": fetched.content_length,
        }
        return JobDetailExtractionResult(
            **{
                **parsed.__dict__,
                "provider": self.provider_name,
                "source_url": fetched.final_url or fetched.url,
                "canonical_url": detection.canonical_url,
                "evidence": evidence,
            }
        )
