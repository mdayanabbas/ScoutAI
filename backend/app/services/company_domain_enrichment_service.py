import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError, ValidationAppError
from app.enrichment.domain_extractor import (
    collect_candidate_domain_proposals,
    is_allowed_company_domain,
    normalize_domain_proposal,
)
from app.enrichment.domain_validator import DomainValidator, DomainValidationResult
from app.enrichment.proposal_ranker import (
    rank_domain_proposals,
    select_resolvable_proposal,
)
from app.enrichment.resolvers import (
    AshbyCompanyResolutionResult,
    AshbyJobBoardResolver,
    AshbyJobBoardResult,
    WebSearchCompanyResolver,
    YCCompanyResolutionResult,
    YCombinatorCompanyResolver,
)
from app.models.company_enrichment_attempt import CompanyEnrichmentAttempt
from app.models.discovery_candidate import DiscoveryCandidate
from app.models.discovery_evidence import DiscoveryEvidence
from app.repositories.company_enrichment_attempt_repository import (
    CompanyEnrichmentAttemptRepository,
)
from app.repositories.company_repository import CompanyRepository
from app.repositories.discovery_candidate_repository import DiscoveryCandidateRepository
from app.repositories.discovery_evidence_repository import DiscoveryEvidenceRepository
from app.repositories.discovery_run_repository import DiscoveryRunRepository
from app.schemas.company_enrichment import (
    CandidateEnrichmentResult,
    RunEnrichmentResult,
)
from app.services.company_service import CompanyService
from app.utils.enums import (
    CompanyEnrichmentDecision,
    CompanyEnrichmentResolver,
    CompanyEnrichmentStatus,
    CompanySource,
    CompanyStage,
    DiscoveryCandidateStatus,
    DiscoveryDecision,
)
from app.utils.urls import normalize_url

logger = logging.getLogger(__name__)


class CompanyDomainEnrichmentService:
    def __init__(
        self,
        session: Session,
        validator: DomainValidator | None = None,
        yc_resolver: YCombinatorCompanyResolver | None = None,
        ashby_resolver: AshbyJobBoardResolver | None = None,
        web_search_resolver: WebSearchCompanyResolver | None = None,
    ) -> None:
        self.session = session
        self.candidate_repository = DiscoveryCandidateRepository(session)
        self.run_repository = DiscoveryRunRepository(session)
        self.attempt_repository = CompanyEnrichmentAttemptRepository(session)
        self.evidence_repository = DiscoveryEvidenceRepository(session)
        self.company_repository = CompanyRepository(session)
        self.company_service = CompanyService(session)
        self.validator = validator or DomainValidator()
        self.yc_resolver = yc_resolver or YCombinatorCompanyResolver()
        self.ashby_resolver = ashby_resolver or AshbyJobBoardResolver()
        self._web_search_query_cache: dict[str, Any] = {}
        self.web_search_resolver = web_search_resolver or WebSearchCompanyResolver(
            validator=self.validator,
            query_cache=self._web_search_query_cache,
        )
        self._yc_resolution_cache: dict[str, YCCompanyResolutionResult] = {}
        self._ashby_board_cache: dict[str, AshbyJobBoardResult] = {}

    async def enrich_candidate(self, candidate_id: str) -> CandidateEnrichmentResult:
        candidate = self._require_candidate(candidate_id)
        if candidate.status == DiscoveryCandidateStatus.INGESTED and candidate.matched_company_id:
            return self._result(
                candidate,
                CompanyEnrichmentDecision.MATCHED_EXISTING_COMPANY,
                candidate.normalized_domain,
                "Candidate already ingested",
            )
        self._require_auto_eligible(candidate)
        attempt = self._create_attempt(
            candidate, CompanyEnrichmentResolver.OTHER, "automatic enrichment"
        )
        return await self._run_attempt(candidate, attempt)

    async def manually_resolve_candidate(
        self, candidate_id: str, website_url: str
    ) -> CandidateEnrichmentResult:
        candidate = self._require_candidate(candidate_id)
        domain = normalize_domain_proposal(website_url)
        if not domain or not is_allowed_company_domain(domain):
            raise ValidationAppError("Invalid company website URL")
        attempt = self._create_attempt(
            candidate,
            CompanyEnrichmentResolver.MANUAL,
            "manual domain resolution",
            website_url=website_url,
            domain=domain,
            confidence=1.0,
        )
        self.attempt_repository.mark_running(attempt)
        validation = await self.validator.validate(website_url)
        if not validation.valid or not validation.normalized_domain:
            attempt = self.attempt_repository.mark_unresolved(
                attempt, validation.reason or "invalid_website_url", validation.__dict__
            )
            return self._result(
                candidate,
                CompanyEnrichmentDecision.UNRESOLVED,
                None,
                attempt.reason or "Unable to validate website",
            )
        return self._resolve_candidate_with_domain(
            candidate,
            attempt,
            validation,
            CompanyEnrichmentResolver.MANUAL,
            1.0,
            {"manual_input": website_url, "validation": validation.__dict__},
        )

    async def enrich_discovery_run(
        self, run_id: str, limit: int | None = None
    ) -> RunEnrichmentResult:
        if self.run_repository.get_by_id(run_id) is None:
            raise NotFoundError("Discovery run not found")
        settings = get_settings()
        max_limit = min(limit or settings.COMPANY_ENRICHMENT_MAX_CANDIDATES_PER_RUN, settings.COMPANY_ENRICHMENT_MAX_CANDIDATES_PER_RUN)
        candidates = [
            candidate
            for candidate in self.candidate_repository.list_by_run(
                run_id, limit=max_limit * 2
            )
            if self._is_auto_eligible(candidate)
        ][:max_limit]

        results: list[CandidateEnrichmentResult] = []
        for candidate in candidates:
            try:
                results.append(await self.enrich_candidate(candidate.id))
            except Exception as exc:
                self.session.rollback()
                logger.info(
                    "Candidate enrichment failed",
                    extra={"candidate_id": candidate.id, "error": exc.__class__.__name__},
                )
                results.append(
                    self._result(
                        candidate,
                        CompanyEnrichmentDecision.FAILED,
                        None,
                        _safe_error_message(exc),
                    )
                )

        return RunEnrichmentResult(
            discovery_run_id=run_id,
            candidates_examined=len(candidates),
            candidates_resolved=sum(
                1
                for result in results
                if result.decision
                in {
                    CompanyEnrichmentDecision.CREATED_COMPANY,
                    CompanyEnrichmentDecision.MATCHED_EXISTING_COMPANY,
                }
            ),
            companies_created=sum(
                1 for result in results if result.decision == CompanyEnrichmentDecision.CREATED_COMPANY
            ),
            companies_matched=sum(
                1
                for result in results
                if result.decision == CompanyEnrichmentDecision.MATCHED_EXISTING_COMPANY
            ),
            candidates_unresolved=sum(
                1 for result in results if result.decision == CompanyEnrichmentDecision.UNRESOLVED
            ),
            candidates_failed=sum(
                1 for result in results if result.decision == CompanyEnrichmentDecision.FAILED
            ),
            results=results,
        )

    def list_attempts(self, candidate_id: str) -> list[CompanyEnrichmentAttempt]:
        self._require_candidate(candidate_id)
        return self.attempt_repository.list_by_candidate(candidate_id)

    async def _run_attempt(
        self, candidate: DiscoveryCandidate, attempt: CompanyEnrichmentAttempt
    ) -> CandidateEnrichmentResult:
        self.attempt_repository.mark_running(attempt)
        proposals = collect_candidate_domain_proposals(candidate)
        ranked = rank_domain_proposals(proposals)
        selected, unresolved_reason = select_resolvable_proposal(ranked)
        evidence = {
            "proposals": [proposal.__dict__ for proposal in proposals],
            "ranked": [
                {
                    "domain": item.proposal.domain,
                    "source": item.proposal.source,
                    "resolver": item.proposal.resolver,
                    "confidence": item.confidence,
                    "reason": item.reason,
                }
                for item in ranked
            ],
        }
        if selected is None:
            fallback_result: CandidateEnrichmentResult | None = None
            yc_result = await self._try_ycombinator_profile_resolution(
                candidate, attempt, evidence
            )
            if yc_result is not None and yc_result.decision in {
                CompanyEnrichmentDecision.CREATED_COMPANY,
                CompanyEnrichmentDecision.MATCHED_EXISTING_COMPANY,
            }:
                return yc_result
            fallback_result = yc_result or fallback_result
            ashby_result = await self._try_ashby_resolution(
                candidate, attempt, evidence
            )
            if ashby_result is not None and ashby_result.decision in {
                CompanyEnrichmentDecision.CREATED_COMPANY,
                CompanyEnrichmentDecision.MATCHED_EXISTING_COMPANY,
            }:
                return ashby_result
            fallback_result = ashby_result or fallback_result
            web_search_result = await self._try_web_search_resolution(
                candidate, attempt, evidence
            )
            if web_search_result is not None:
                return web_search_result
            if fallback_result is not None:
                return fallback_result
            attempt = self.attempt_repository.mark_unresolved(
                attempt, unresolved_reason or "no_domain_proposals", evidence
            )
            return self._result(
                candidate,
                CompanyEnrichmentDecision.UNRESOLVED,
                None,
                attempt.reason or "No trustworthy domain proposal",
            )

        self.attempt_repository.update(
            attempt,
            {
                "resolver": CompanyEnrichmentResolver(selected.proposal.resolver),
                "proposed_website_url": selected.proposal.value,
                "proposed_domain": selected.proposal.domain,
                "confidence": selected.confidence,
                "reason": selected.reason,
                "evidence_json": evidence,
            },
        )
        validation = await self.validator.validate(selected.proposal.value)
        if not validation.valid or not validation.normalized_domain:
            attempt = self.attempt_repository.mark_unresolved(
                attempt, validation.reason or "unreachable_website", evidence
            )
            return self._result(
                candidate,
                CompanyEnrichmentDecision.UNRESOLVED,
                None,
                attempt.reason or "Unable to validate website",
            )
        return self._resolve_candidate_with_domain(
            candidate,
            attempt,
            validation,
            CompanyEnrichmentResolver(selected.proposal.resolver),
            selected.confidence,
            {**evidence, "validation": validation.__dict__},
        )

    async def _try_ycombinator_profile_resolution(
        self,
        candidate: DiscoveryCandidate,
        attempt: CompanyEnrichmentAttempt,
        base_evidence: dict[str, Any],
    ) -> CandidateEnrichmentResult | None:
        if not self.yc_resolver.supports(candidate):
            return None
        slug = self.yc_resolver.extract_company_slug(candidate)
        if not slug:
            return None

        logger.info(
            "YC resolver selected",
            extra={"candidate_id": candidate.id, "company_slug": slug},
        )
        result = self._yc_resolution_cache.get(slug)
        if result is None:
            result = await self.yc_resolver.resolve(candidate)
            self._yc_resolution_cache[slug] = result

        evidence = {
            **base_evidence,
            "yc_profile": {
                "company_slug": result.company_slug or slug,
                "profile_url": result.profile_url,
                "proposed_website_url": result.proposed_website_url,
                "proposed_domain": result.proposed_domain,
                "status_code": result.status_code,
                "reason": result.reason,
                "metadata": {
                    "company_name": result.company_name,
                    "description": result.description,
                    "location": result.location,
                    "batch": result.batch,
                },
                "parser_evidence": result.evidence,
            },
        }
        self.attempt_repository.update(
            attempt,
            {
                "resolver": CompanyEnrichmentResolver.YCOMBINATOR_PROFILE,
                "proposed_website_url": result.proposed_website_url,
                "proposed_domain": result.proposed_domain,
                "confidence": result.confidence,
                "reason": result.reason,
                "evidence_json": evidence,
            },
        )
        if not result.resolved or not result.proposed_website_url:
            reason = result.reason or "yc_official_website_missing"
            attempt = self.attempt_repository.mark_unresolved(attempt, reason, evidence)
            logger.info(
                "YC candidate remained unresolved",
                extra={"candidate_id": candidate.id, "reason": reason},
            )
            return self._result(
                candidate,
                CompanyEnrichmentDecision.UNRESOLVED,
                None,
                reason,
            )

        validation = await self.validator.validate(result.proposed_website_url)
        evidence["yc_profile"]["validation"] = validation.__dict__
        if not validation.valid or not validation.normalized_domain:
            reason = _yc_validation_reason(validation.reason)
            attempt = self.attempt_repository.mark_unresolved(attempt, reason, evidence)
            logger.info(
                "YC profile website rejected",
                extra={
                    "candidate_id": candidate.id,
                    "reason": reason,
                    "validation_reason": validation.reason,
                },
            )
            return self._result(
                candidate,
                CompanyEnrichmentDecision.UNRESOLVED,
                None,
                reason,
            )

        logger.info(
            "YC official domain proposed",
            extra={
                "candidate_id": candidate.id,
                "domain": validation.normalized_domain,
            },
        )
        return self._resolve_candidate_with_domain(
            candidate,
            attempt,
            validation,
            CompanyEnrichmentResolver.YCOMBINATOR_PROFILE,
            result.confidence or 0.95,
            evidence,
        )

    async def _try_ashby_resolution(
        self,
        candidate: DiscoveryCandidate,
        attempt: CompanyEnrichmentAttempt,
        base_evidence: dict[str, Any],
    ) -> CandidateEnrichmentResult | None:
        if not self.ashby_resolver.supports(candidate):
            return None
        slug = self.ashby_resolver.extract_board_slug(candidate)
        if not slug:
            classification = (candidate.raw_payload or {}).get(
                "url_classification"
            ) or {}
            reason = (
                "ashby_board_slug_invalid"
                if classification.get("external_company_slug")
                else "ashby_board_slug_missing"
            )
            evidence = {**base_evidence, "ashby_job_board": {"reason": reason}}
            self.attempt_repository.update(
                attempt,
                {
                    "resolver": CompanyEnrichmentResolver.ASHBY_PUBLIC_JOB_BOARD,
                    "reason": reason,
                    "evidence_json": evidence,
                },
            )
            self.attempt_repository.mark_unresolved(attempt, reason, evidence)
            return self._result(
                candidate, CompanyEnrichmentDecision.UNRESOLVED, None, reason
            )

        logger.info(
            "Ashby resolver selected",
            extra={"candidate_id": candidate.id, "board_slug": slug},
        )
        board = self._ashby_board_cache.get(slug.lower())
        if board is None:
            board = await self.ashby_resolver.fetch_job_board(slug)
            self._ashby_board_cache[slug.lower()] = board
        result = await self.ashby_resolver.resolve(candidate, board_result=board)
        evidence = {
            **base_evidence,
            "ashby_job_board": {
                "board_slug": result.board_slug,
                "posting_id": result.posting_id,
                "status_code": result.status_code,
                "proposed_website_url": result.proposed_website_url,
                "proposed_domain": result.proposed_domain,
                "reason": result.reason,
                **result.evidence,
            },
        }
        self.attempt_repository.update(
            attempt,
            {
                "resolver": CompanyEnrichmentResolver.ASHBY_PUBLIC_JOB_BOARD,
                "proposed_website_url": result.proposed_website_url,
                "proposed_domain": result.proposed_domain,
                "confidence": result.confidence,
                "reason": result.reason,
                "evidence_json": evidence,
            },
        )
        if result.matched_job is not None:
            self._persist_ashby_evidence(candidate, result)

        if not result.resolved or not result.proposed_website_url:
            reason = result.reason or "ashby_company_domain_missing"
            self.attempt_repository.mark_unresolved(attempt, reason, evidence)
            logger.info(
                "Ashby candidate remained unresolved",
                extra={"candidate_id": candidate.id, "reason": reason},
            )
            return self._result(
                candidate, CompanyEnrichmentDecision.UNRESOLVED, None, reason
            )

        validation = await self.validator.validate(result.proposed_website_url)
        evidence["ashby_job_board"]["validation"] = validation.__dict__
        if not validation.valid or not validation.normalized_domain:
            reason = _ashby_validation_reason(validation.reason)
            self.attempt_repository.mark_unresolved(attempt, reason, evidence)
            return self._result(
                candidate, CompanyEnrichmentDecision.UNRESOLVED, None, reason
            )
        logger.info(
            "Ashby company domain resolved",
            extra={
                "candidate_id": candidate.id,
                "domain": validation.normalized_domain,
            },
        )
        return self._resolve_candidate_with_domain(
            candidate,
            attempt,
            validation,
            CompanyEnrichmentResolver.ASHBY_PUBLIC_JOB_BOARD,
            result.confidence or 0.9,
            evidence,
        )

    async def _try_web_search_resolution(
        self,
        candidate: DiscoveryCandidate,
        attempt: CompanyEnrichmentAttempt,
        base_evidence: dict[str, Any],
    ) -> CandidateEnrichmentResult | None:
        if not self.web_search_resolver.supports(candidate):
            return None
        logger.info(
            "Web search resolver selected",
            extra={"candidate_id": candidate.id},
        )
        result = await self.web_search_resolver.resolve(candidate)
        evidence = {
            **base_evidence,
            "web_search_company_identity": result.evidence
            or {
                "provider": result.provider,
                "queries": list(result.queries),
                "reason": result.reason,
            },
        }
        self.attempt_repository.update(
            attempt,
            {
                "resolver": CompanyEnrichmentResolver.WEB_SEARCH_COMPANY_IDENTITY,
                "proposed_website_url": result.proposed_website_url,
                "proposed_domain": result.proposed_domain,
                "confidence": result.confidence,
                "reason": result.reason,
                "evidence_json": evidence,
            },
        )
        if not result.resolved or not result.proposed_website_url:
            reason = result.reason or "no_trustworthy_company_domain"
            self.attempt_repository.mark_unresolved(attempt, reason, evidence)
            logger.info(
                "Web search candidate remained unresolved",
                extra={"candidate_id": candidate.id, "reason": reason},
            )
            return self._result(
                candidate,
                CompanyEnrichmentDecision.UNRESOLVED,
                None,
                reason,
            )

        validation = DomainValidationResult(
            valid=True,
            requested_url=result.proposed_website_url,
            final_url=result.proposed_website_url,
            normalized_domain=result.proposed_domain,
            status_code=200,
        )
        return self._resolve_candidate_with_domain(
            candidate,
            attempt,
            validation,
            CompanyEnrichmentResolver.WEB_SEARCH_COMPANY_IDENTITY,
            result.confidence or 0.9,
            evidence,
        )

    def _persist_ashby_evidence(
        self,
        candidate: DiscoveryCandidate,
        result: AshbyCompanyResolutionResult,
    ) -> None:
        job = result.matched_job
        if job is None:
            return
        identity = job.raw_posting_id or job.job_url or job.apply_url
        for existing in candidate.evidence:
            metadata = existing.metadata_json or {}
            if (
                existing.evidence_type == "ashby_job_posting"
                and metadata.get("identity") == identity
            ):
                return
        source_url = job.job_url or job.apply_url
        if not source_url:
            return
        self.evidence_repository.create_evidence(
            DiscoveryEvidence(
                discovery_candidate_id=candidate.id,
                evidence_type="ashby_job_posting",
                source_url=source_url,
                title=job.title,
                excerpt=(job.description_plain or "")[:500] or None,
                published_at=job.published_at,
                metadata_json={
                    "identity": identity,
                    "resolver": (
                        CompanyEnrichmentResolver.ASHBY_PUBLIC_JOB_BOARD.value
                    ),
                    "board_slug": result.board_slug,
                    **job.focused_metadata(),
                },
            )
        )

    def _resolve_candidate_with_domain(
        self,
        candidate: DiscoveryCandidate,
        attempt: CompanyEnrichmentAttempt,
        validation: DomainValidationResult,
        resolver: CompanyEnrichmentResolver,
        confidence: float,
        evidence: dict[str, Any],
    ) -> CandidateEnrichmentResult:
        domain = validation.normalized_domain
        if not domain:
            raise ValidationAppError("Validated domain missing")
        existing = self.company_repository.get_by_domain(domain)
        if existing is not None:
            candidate = self.candidate_repository.update_candidate(
                candidate,
                {
                    "normalized_website_url": normalize_url(validation.final_url or domain),
                    "normalized_domain": domain,
                    "status": DiscoveryCandidateStatus.INGESTED,
                    "decision": DiscoveryDecision.MATCHED_EXISTING_COMPANY,
                    "matched_company_id": existing.id,
                    "deferred_reason": None,
                },
            )
            attempt = self.attempt_repository.mark_resolved(
                attempt,
                {
                    "resolver": resolver,
                    "proposed_website_url": validation.final_url,
                    "proposed_domain": domain,
                    "confidence": confidence,
                    "decision": CompanyEnrichmentDecision.MATCHED_EXISTING_COMPANY,
                    "evidence_json": evidence,
                },
            )
            return self._result(
                candidate,
                CompanyEnrichmentDecision.MATCHED_EXISTING_COMPANY,
                domain,
                "Matched existing company",
            )

        company = self.company_service.create_company(
            {
                "name": candidate.normalized_name or candidate.raw_name,
                "website_url": validation.final_url or domain,
                "normalized_domain": domain,
                "description": candidate.normalized_description,
                "country": candidate.normalized_country,
                "source": self._company_source_for_candidate(candidate),
                "stage": CompanyStage.UNKNOWN,
                "is_active": True,
            }
        )
        candidate = self.candidate_repository.update_candidate(
            candidate,
            {
                "normalized_website_url": normalize_url(validation.final_url or domain),
                "normalized_domain": domain,
                "status": DiscoveryCandidateStatus.INGESTED,
                "decision": DiscoveryDecision.CREATED_COMPANY,
                "matched_company_id": company.id,
                "deferred_reason": None,
            },
        )
        self.attempt_repository.mark_resolved(
            attempt,
            {
                "resolver": resolver,
                "proposed_website_url": validation.final_url,
                "proposed_domain": domain,
                "confidence": confidence,
                "decision": CompanyEnrichmentDecision.CREATED_COMPANY,
                "evidence_json": evidence,
            },
        )
        return self._result(
            candidate,
            CompanyEnrichmentDecision.CREATED_COMPANY,
            domain,
            "Created company",
        )

    def _create_attempt(
        self,
        candidate: DiscoveryCandidate,
        resolver: CompanyEnrichmentResolver,
        reason: str,
        website_url: str | None = None,
        domain: str | None = None,
        confidence: float | None = None,
    ) -> CompanyEnrichmentAttempt:
        return self.attempt_repository.create_attempt(
            CompanyEnrichmentAttempt(
                discovery_candidate_id=candidate.id,
                status=CompanyEnrichmentStatus.PENDING,
                resolver=resolver,
                proposed_website_url=website_url,
                proposed_domain=domain,
                confidence=confidence,
                reason=reason,
            )
        )

    def _require_candidate(self, candidate_id: str) -> DiscoveryCandidate:
        candidate = self.candidate_repository.get_by_id(candidate_id)
        if candidate is None:
            raise NotFoundError("Discovery candidate not found")
        return candidate

    def _require_auto_eligible(self, candidate: DiscoveryCandidate) -> None:
        if not self._is_auto_eligible(candidate):
            raise ValidationAppError("Discovery candidate is not eligible for enrichment")

    def _is_auto_eligible(self, candidate: DiscoveryCandidate) -> bool:
        return (
            candidate.decision == DiscoveryDecision.DEFERRED
            and candidate.deferred_reason == "requires_company_domain_enrichment"
        )

    def _company_source_for_candidate(self, candidate: DiscoveryCandidate) -> CompanySource:
        try:
            return CompanySource(candidate.source.value)
        except ValueError:
            return CompanySource.OTHER

    def _result(
        self,
        candidate: DiscoveryCandidate,
        decision: CompanyEnrichmentDecision,
        resolved_domain: str | None,
        message: str,
    ) -> CandidateEnrichmentResult:
        refreshed = self.candidate_repository.get_by_id(candidate.id) or candidate
        return CandidateEnrichmentResult(
            candidate=refreshed,
            attempts=self.attempt_repository.list_by_candidate(candidate.id),
            company_id=refreshed.matched_company_id,
            decision=decision,
            resolved_domain=resolved_domain,
            message=message,
        )


def _yc_validation_reason(reason: str | None) -> str:
    if reason in {"blocked_or_shared_domain", "blocked_redirect_domain"}:
        return "yc_profile_website_blocked"
    if reason and "unsafe" in reason:
        return "yc_profile_website_unsafe"
    if reason in {"unreachable", "too_many_redirects"}:
        return "yc_profile_website_unreachable"
    return "yc_profile_website_unreachable"


def _ashby_validation_reason(reason: str | None) -> str:
    if reason in {
        "unsafe_host",
        "unsafe_redirect",
        "unsafe_redirect_host",
        "blocked_or_shared_domain",
        "blocked_redirect_domain",
        "invalid_hostname",
        "embedded_credentials",
    }:
        return "ashby_company_domain_unsafe"
    return "ashby_company_domain_unreachable"


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    return message if message else exc.__class__.__name__
