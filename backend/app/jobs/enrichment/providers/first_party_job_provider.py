import logging

from app.jobs.enrichment.models import JobDetailExtractionResult
from app.jobs.enrichment.parsers.first_party_job_parser import FirstPartyJobParser
from app.jobs.enrichment.providers.first_party_job_client import FirstPartyJobClient
from app.jobs.source_detection import JobSourceDetectionResult
from app.models.job import Job
from app.utils.enums import JobSourceType

logger = logging.getLogger(__name__)

PROVIDER_NAME = "first_party_job_page"


class FirstPartyJobEnrichmentProvider:
    provider_name = PROVIDER_NAME

    def __init__(
        self,
        *,
        client: FirstPartyJobClient | None = None,
        parser: FirstPartyJobParser | None = None,
    ) -> None:
        self.client = client or FirstPartyJobClient()
        self.parser = parser or FirstPartyJobParser()

    async def enrich(
        self,
        detection: JobSourceDetectionResult,
        *,
        job: Job | None = None,
    ) -> JobDetailExtractionResult:
        if detection.source_type != JobSourceType.FIRST_PARTY_JOB_PAGE or not detection.canonical_url:
            return JobDetailExtractionResult(
                success=False,
                provider=self.provider_name,
                source_url=detection.original_url or "",
                canonical_url=detection.canonical_url or "",
                reason="unsupported_job_source",
            )
        company = getattr(job, "company", None)
        company_domain = getattr(company, "normalized_domain", None)
        if not company_domain:
            return JobDetailExtractionResult(
                success=False,
                provider=self.provider_name,
                source_url=detection.canonical_url,
                canonical_url=detection.canonical_url,
                reason="unresolved_company",
            )
        fetched = await self.client.fetch_job_page(
            detection.canonical_url,
            company_domain=company_domain,
        )
        if fetched.reason or not fetched.html:
            logger.info(
                "First-party page rejected",
                extra={"reason": fetched.reason, "status_code": fetched.status_code},
            )
            return JobDetailExtractionResult(
                success=False,
                provider=self.provider_name,
                source_url=detection.canonical_url,
                canonical_url=fetched.final_url or detection.canonical_url,
                reason=fetched.reason or "first_party_job_data_missing",
                evidence={
                    "requested_url": fetched.requested_url,
                    "final_url": fetched.final_url,
                    "response_status": fetched.status_code,
                    "response_size": fetched.response_size,
                    "redirect_count": fetched.redirect_count,
                    "robots_allowed": fetched.robots_allowed,
                    "warnings": fetched.warnings[:10],
                },
                warnings=fetched.warnings,
            )
        parsed = self.parser.parse(
            fetched.html,
            source_url=detection.canonical_url,
            canonical_url=fetched.final_url or detection.canonical_url,
            company_name=getattr(company, "name", None),
            company_domain=company_domain,
        )
        evidence = {
            **parsed.evidence,
            "requested_url": fetched.requested_url,
            "final_url": fetched.final_url,
            "response_status": fetched.status_code,
            "response_size": fetched.response_size,
            "redirect_count": fetched.redirect_count,
            "robots_allowed": fetched.robots_allowed,
            "content_type": fetched.content_type,
        }
        return JobDetailExtractionResult(
            **{
                **parsed.__dict__,
                "provider": self.provider_name,
                "source_url": detection.canonical_url,
                "canonical_url": fetched.final_url or detection.canonical_url,
                "evidence": evidence,
                "warnings": [*parsed.warnings, *fetched.warnings],
            }
        )

