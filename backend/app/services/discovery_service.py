from dataclasses import dataclass
import logging
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.discovery.adapters.base import StartupSourceAdapter
from app.discovery.adapters.manual import ManualDiscoveryAdapter
from app.discovery.identity import (
    get_candidate_url_classification,
    get_hacker_news_feed,
)
from app.discovery.normalizer import CandidateNormalizationError, normalize_candidate
from app.discovery.sources.hacker_news.adapter import HackerNewsDiscoveryAdapter
from app.discovery.sources.hacker_news.schemas import (
    HackerNewsDiscoveryRequest,
    HackerNewsDiscoveryResponse,
)
from app.discovery.url_classifier import CandidateUrlType, build_candidate_identity
from app.discovery.validator import validate_candidate
from app.models.discovery_candidate import DiscoveryCandidate
from app.models.discovery_evidence import DiscoveryEvidence
from app.models.discovery_run import DiscoveryRun
from app.repositories.company_repository import CompanyRepository
from app.repositories.discovery_candidate_repository import DiscoveryCandidateRepository
from app.repositories.discovery_evidence_repository import DiscoveryEvidenceRepository
from app.repositories.discovery_run_repository import DiscoveryRunRepository
from app.schemas.discovery import (
    DiscoveryRunResult,
    ManualDiscoveryRequest,
    RawStartupCandidate,
)
from app.services.company_service import CompanyService
from app.utils.enums import (
    CompanySource,
    CompanyStage,
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoveryRunStatus,
    DiscoverySource,
)

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryCounters:
    candidates_found: int = 0
    candidates_normalized: int = 0
    companies_created: int = 0
    companies_matched: int = 0
    candidates_deferred: int = 0
    candidates_rejected: int = 0
    candidates_failed: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "candidates_found": self.candidates_found,
            "candidates_normalized": self.candidates_normalized,
            "companies_created": self.companies_created,
            "companies_matched": self.companies_matched,
            "candidates_deferred": self.candidates_deferred,
            "candidates_rejected": self.candidates_rejected,
            "candidates_failed": self.candidates_failed,
        }


class DiscoveryService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.run_repository = DiscoveryRunRepository(session)
        self.candidate_repository = DiscoveryCandidateRepository(session)
        self.evidence_repository = DiscoveryEvidenceRepository(session)
        self.company_repository = CompanyRepository(session)
        self.company_service = CompanyService(session)

    async def run_manual_discovery(
        self, request: ManualDiscoveryRequest
    ) -> DiscoveryRunResult:
        return await self.run_discovery(
            adapter=ManualDiscoveryAdapter(),
            request=request,
            source=DiscoverySource.MANUAL,
            company_source=CompanySource.MANUAL,
            metadata=request.metadata,
        )

    async def run_hacker_news_discovery(
        self, request: HackerNewsDiscoveryRequest
    ) -> HackerNewsDiscoveryResponse:
        adapter = HackerNewsDiscoveryAdapter()
        metadata = {
            **(request.metadata or {}),
            "requested_feeds": request.feeds,
            "limit": request.limit,
            "lookback_days": request.lookback_days,
            "minimum_score": request.minimum_score,
            "include_items_without_website": request.include_items_without_website,
        }
        result = await self.run_discovery(
            adapter=adapter,
            request=request,
            source=DiscoverySource.HACKER_NEWS,
            company_source=CompanySource.HACKER_NEWS,
            metadata=metadata,
        )
        run = self.run_repository.get_by_id(result.run.id)
        if run is not None:
            updated_metadata = dict(run.metadata_json or {})
            updated_metadata.update(
                {
                    "fetched_item_count": adapter.fetched_item_count,
                    "skipped_item_count": adapter.skipped_item_count,
                }
            )
            self.run_repository.update(run, {"metadata_json": updated_metadata})
            result = self._result_for_run(run.id)
        return HackerNewsDiscoveryResponse(
            run=result.run,
            candidates=result.candidates,
            fetched_item_count=adapter.fetched_item_count,
            skipped_item_count=adapter.skipped_item_count,
        )

    async def run_discovery(
        self,
        adapter: StartupSourceAdapter,
        request: object,
        source: DiscoverySource,
        company_source: CompanySource,
        metadata: dict[str, Any] | None = None,
    ) -> DiscoveryRunResult:
        run = self.run_repository.create_run(
            DiscoveryRun(
                source=source,
                status=DiscoveryRunStatus.PENDING,
                metadata_json=metadata,
                candidates_found=0,
                candidates_normalized=0,
                companies_created=0,
                companies_matched=0,
                candidates_deferred=0,
                candidates_rejected=0,
                candidates_failed=0,
            )
        )
        counters = DiscoveryCounters()
        run = self.run_repository.mark_running(run)
        seen_keys: set[str] = set()
        logger.info(
            "Discovery run started",
            extra={"run_id": run.id, "source": source.value},
        )

        try:
            raw_candidates = await adapter.discover(request)
        except Exception as exc:
            logger.info(
                "Discovery run failed during adapter retrieval",
                extra={
                    "run_id": run.id,
                    "source": source.value,
                    "error": exc.__class__.__name__,
                },
            )
            run = self.run_repository.mark_failed(run, str(exc), counters.as_dict())
            return self._result_for_run(run.id)

        for raw_candidate in raw_candidates:
            counters.candidates_found += 1
            candidate = self._create_raw_candidate(run.id, source, raw_candidate)
            self._persist_evidence(candidate.id, raw_candidate)
            try:
                normalized = normalize_candidate(raw_candidate)
                candidate = self.candidate_repository.update_candidate(
                    candidate,
                    {
                        "normalized_name": normalized.name,
                        "normalized_website_url": normalized.website_url,
                        "normalized_domain": normalized.normalized_domain,
                        "normalized_description": normalized.description,
                        "normalized_country": normalized.country,
                        "source_identifier": normalized.source_identifier,
                        "status": DiscoveryCandidateStatus.NORMALIZED,
                    },
                )
                counters.candidates_normalized += 1

                validation = validate_candidate(raw_candidate, normalized)
                if not validation.valid:
                    self._reject_candidate(candidate, validation.reason or "invalid")
                    counters.candidates_rejected += 1
                    continue

                duplicate_key = build_candidate_identity(
                    source.value,
                    normalized.source_identifier,
                    normalized.normalized_domain,
                    raw_candidate.raw_payload,
                )
                if duplicate_key in seen_keys:
                    self._reject_candidate(
                        candidate,
                        "duplicate_candidate_in_run",
                        status=DiscoveryCandidateStatus.DUPLICATE,
                    )
                    counters.candidates_rejected += 1
                    continue
                seen_keys.add(duplicate_key)

                if source != DiscoverySource.HACKER_NEWS and not normalized.normalized_domain:
                    self._reject_candidate(candidate, "missing_normalized_domain")
                    counters.candidates_rejected += 1
                    continue

                defer_reason = self._deferred_reason_for_candidate(
                    source, raw_candidate, normalized.normalized_domain
                )
                if defer_reason is not None:
                    self._defer_candidate(candidate, defer_reason)
                    counters.candidates_deferred += 1
                    continue

                existing_company = self.company_repository.get_by_domain(
                    normalized.normalized_domain
                )
                if existing_company is not None:
                    self.candidate_repository.update_candidate(
                        candidate,
                        {
                            "status": DiscoveryCandidateStatus.INGESTED,
                            "decision": DiscoveryDecision.MATCHED_EXISTING_COMPANY,
                            "matched_company_id": existing_company.id,
                        },
                    )
                    counters.companies_matched += 1
                else:
                    company = self.company_service.create_company(
                        {
                            "name": normalized.name,
                            "website_url": normalized.website_url,
                            "normalized_domain": normalized.normalized_domain,
                            "description": normalized.description,
                            "country": normalized.country,
                            "source": company_source,
                            "stage": CompanyStage.UNKNOWN,
                            "is_active": True,
                        }
                    )
                    self.candidate_repository.update_candidate(
                        candidate,
                        {
                            "status": DiscoveryCandidateStatus.INGESTED,
                            "decision": DiscoveryDecision.CREATED_COMPANY,
                            "matched_company_id": company.id,
                        },
                    )
                    counters.companies_created += 1
            except Exception as exc:
                self._mark_candidate_failed(candidate, exc)
                counters.candidates_failed += 1
                logger.info(
                    "Discovery candidate failed",
                    extra={
                        "run_id": run.id,
                        "source": source.value,
                        "source_identifier": raw_candidate.source_identifier,
                        "error": exc.__class__.__name__,
                    },
                )

        run = self._finish_run(run, counters)
        logger.info(
            "Discovery run completed",
            extra={
                "run_id": run.id,
                "source": source.value,
                **counters.as_dict(),
                "status": run.status.value,
            },
        )
        return self._result_for_run(run.id)

    def list_runs(
        self,
        offset: int = 0,
        limit: int = 50,
        source: DiscoverySource | None = None,
        status: DiscoveryRunStatus | None = None,
    ) -> list[DiscoveryRun]:
        return self.run_repository.list_runs(
            offset=offset, limit=limit, source=source, status=status
        )

    def count_runs(
        self,
        source: DiscoverySource | None = None,
        status: DiscoveryRunStatus | None = None,
    ) -> int:
        return self.run_repository.count_runs(source=source, status=status)

    def get_run_result(self, run_id: str) -> DiscoveryRunResult:
        if self.run_repository.get_by_id(run_id) is None:
            raise NotFoundError("Discovery run not found")
        return self._result_for_run(run_id)

    def get_candidate(self, candidate_id: str) -> DiscoveryCandidate:
        candidate = self.candidate_repository.get_by_id(candidate_id)
        if candidate is None:
            raise NotFoundError("Discovery candidate not found")
        return candidate

    def _create_raw_candidate(
        self,
        run_id: str,
        source: DiscoverySource,
        raw_candidate: RawStartupCandidate,
    ) -> DiscoveryCandidate:
        try:
            return self.candidate_repository.create_candidate(
                DiscoveryCandidate(
                    discovery_run_id=run_id,
                    source=source,
                    source_identifier=raw_candidate.source_identifier.strip(),
                    raw_name=raw_candidate.name,
                    raw_website_url=raw_candidate.website_url,
                    raw_description=raw_candidate.description,
                    raw_country=raw_candidate.country,
                    status=DiscoveryCandidateStatus.DISCOVERED,
                    raw_payload=raw_candidate.raw_payload,
                )
            )
        except IntegrityError:
            self.session.rollback()
            existing = self.candidate_repository.get_by_source_identifier(
                run_id,
                source,
                raw_candidate.source_identifier.strip(),
            )
            if existing is None:
                raise
            return existing

    def _reject_candidate(
        self,
        candidate: DiscoveryCandidate,
        reason: str,
        status: DiscoveryCandidateStatus = DiscoveryCandidateStatus.REJECTED,
    ) -> None:
        self.candidate_repository.update_candidate(
            candidate,
            {
                "status": status,
                "decision": DiscoveryDecision.REJECTED,
                "rejection_reason": reason,
            },
        )

    def _defer_candidate(
        self,
        candidate: DiscoveryCandidate,
        reason: str,
    ) -> None:
        self.candidate_repository.update_candidate(
            candidate,
            {
                "status": DiscoveryCandidateStatus.NORMALIZED,
                "decision": DiscoveryDecision.DEFERRED,
                "deferred_reason": reason,
            },
        )

    def _mark_candidate_failed(
        self, candidate: DiscoveryCandidate, exc: Exception
    ) -> None:
        if isinstance(exc, CandidateNormalizationError):
            message = str(exc)
        else:
            message = str(exc) or exc.__class__.__name__
        self.candidate_repository.update_candidate(
            candidate,
            {
                "status": DiscoveryCandidateStatus.FAILED,
                "decision": DiscoveryDecision.FAILED,
                "error_message": message,
            },
        )

    def _persist_evidence(
        self, candidate_id: str, raw_candidate: RawStartupCandidate
    ) -> None:
        items = [
            DiscoveryEvidence(
                discovery_candidate_id=candidate_id,
                evidence_type=evidence.evidence_type,
                source_url=evidence.source_url,
                title=evidence.title,
                excerpt=evidence.excerpt,
                published_at=evidence.published_at,
                metadata_json=evidence.metadata,
            )
            for evidence in raw_candidate.evidence
        ]
        if items:
            self.evidence_repository.create_many(items)

    def _finish_run(
        self, run: DiscoveryRun, counters: DiscoveryCounters
    ) -> DiscoveryRun:
        successes = (
            counters.companies_created
            + counters.companies_matched
            + counters.candidates_deferred
        )
        problems = counters.candidates_rejected + counters.candidates_failed
        if counters.candidates_found == 0 or successes == 0:
            return self.run_repository.mark_failed(
                run,
                "No candidates were successfully processed",
                counters.as_dict(),
            )
        if problems:
            return self.run_repository.mark_partial_success(run, counters.as_dict())
        return self.run_repository.mark_success(run, counters.as_dict())

    def _result_for_run(self, run_id: str) -> DiscoveryRunResult:
        run = self.run_repository.get_by_id(run_id)
        if run is None:
            raise NotFoundError("Discovery run not found")
        candidates = self.candidate_repository.list_by_run(run_id, limit=1000)
        return DiscoveryRunResult(run=run, candidates=candidates)

    def _deferred_reason_for_candidate(
        self,
        source: DiscoverySource,
        raw_candidate: RawStartupCandidate,
        normalized_domain: str | None,
    ) -> str | None:
        if source != DiscoverySource.HACKER_NEWS:
            return None

        feed = get_hacker_news_feed(raw_candidate)
        classification = get_candidate_url_classification(raw_candidate)
        url_type = classification.get("url_type")

        if feed == "show":
            return "requires_startup_qualification"

        if normalized_domain and not classification:
            return None

        if url_type != CandidateUrlType.FIRST_PARTY.value or not normalized_domain:
            return "requires_company_domain_enrichment"

        return None
