import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import unquote, urljoin, urlparse
from uuid import UUID

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.enrichment.ashby_public_job_parser import (
    AshbyPublicJob,
    parse_ashby_job_board,
)
from app.enrichment.domain_extractor import (
    DomainProposal,
    extract_email_domains_from_text,
    extract_urls_from_text,
    is_allowed_company_domain,
    normalize_domain_proposal,
)
from app.enrichment.proposal_ranker import (
    rank_domain_proposals,
    select_resolvable_proposal,
)
from app.models.discovery_candidate import DiscoveryCandidate
from app.utils.enums import DiscoverySource

logger = logging.getLogger(__name__)

BOARD_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
POSTING_ID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
MEANINGFUL_TOKEN_RE = re.compile(r"[a-z0-9]+")
GENERIC_TOKENS = {
    "a", "an", "and", "at", "for", "hiring", "in", "is", "of", "our", "role",
    "team", "the", "to", "we", "with",
}
GTM_TERMS = {"gtm", "sales", "marketing", "growth", "go", "market"}


@dataclass(frozen=True)
class AshbyJobBoardResult:
    success: bool
    board_slug: str
    status_code: int | None = None
    jobs: tuple[AshbyPublicJob, ...] = ()
    reason: str | None = None


@dataclass(frozen=True)
class AshbyJobMatchResult:
    matched: bool
    match_strategy: str | None = None
    confidence: float | None = None
    job: AshbyPublicJob | None = None
    reason: str | None = None


@dataclass(frozen=True)
class AshbyCompanyResolutionResult:
    resolved: bool
    board_slug: str | None = None
    posting_id: str | None = None
    matched_job: AshbyPublicJob | None = None
    proposed_website_url: str | None = None
    proposed_domain: str | None = None
    resolver: str = "ashby_public_job_board"
    evidence: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None
    status_code: int | None = None
    confidence: float | None = None
    domain_proposals: tuple[DomainProposal, ...] = ()


class AshbyJobBoardResolver:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        max_response_bytes: int | None = None,
        user_agent: str | None = None,
        include_compensation: bool | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.enabled = settings.ASHBY_RESOLVER_ENABLED
        self.base_url = (
            base_url or settings.ASHBY_POSTING_API_BASE_URL
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.ASHBY_REQUEST_TIMEOUT_SECONDS
        self.max_retries = (
            settings.ASHBY_MAX_RETRIES if max_retries is None else max_retries
        )
        self.max_response_bytes = (
            max_response_bytes or settings.ASHBY_MAX_RESPONSE_BYTES
        )
        self.user_agent = user_agent or settings.ASHBY_USER_AGENT
        self.include_compensation = (
            settings.ASHBY_INCLUDE_COMPENSATION
            if include_compensation is None
            else include_compensation
        )
        self.transport = transport
        parsed = urlparse(self.base_url)
        self._api_origin = (parsed.scheme, parsed.hostname, parsed.port)

    def supports(self, candidate: DiscoveryCandidate) -> bool:
        if not self.enabled or candidate.source != DiscoverySource.HACKER_NEWS:
            return False
        payload = candidate.raw_payload or {}
        classification = payload.get("url_classification") or {}
        url_is_ashby = bool(self._ashby_path_parts(self._candidate_url(candidate)))
        if classification.get("platform") != "ashby" and not url_is_ashby:
            return False
        return payload.get("feed") == "jobs" or payload.get("type") == "job"

    def extract_board_slug(self, candidate: DiscoveryCandidate) -> str | None:
        payload = candidate.raw_payload or {}
        classification = payload.get("url_classification") or {}
        metadata_slug = classification.get("external_company_slug")
        if isinstance(metadata_slug, str):
            return metadata_slug if self._valid_board_slug(metadata_slug) else None
        parts = self._ashby_path_parts(self._candidate_url(candidate))
        return parts[0] if parts and self._valid_board_slug(parts[0]) else None

    def extract_posting_id(self, candidate: DiscoveryCandidate) -> str | None:
        parts = self._ashby_path_parts(self._candidate_url(candidate))
        if not parts or len(parts) < 2:
            return None
        value = parts[1]
        if not POSTING_ID_RE.fullmatch(value):
            return None
        try:
            UUID(value)
        except ValueError:
            return None
        return value.lower()

    def build_api_url(self, board_slug: str) -> str:
        if not self._valid_board_slug(board_slug):
            raise ValueError("Invalid Ashby board slug")
        return f"{self.base_url}/{board_slug}"

    async def fetch_job_board(self, board_slug: str) -> AshbyJobBoardResult:
        if not self._valid_board_slug(board_slug):
            return AshbyJobBoardResult(False, board_slug, reason="ashby_board_slug_invalid")
        url = self.build_api_url(board_slug)
        params = {
            "includeCompensation": str(self.include_compensation).lower(),
        }
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            follow_redirects=False,
            transport=self.transport,
        ) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    logger.info("Ashby board request started", extra={"board_slug": board_slug})
                    response = await client.send(
                        client.build_request("GET", url, params=params),
                        stream=True,
                    )
                except httpx.TimeoutException:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return AshbyJobBoardResult(False, board_slug, reason="ashby_timeout")
                except httpx.HTTPError:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return AshbyJobBoardResult(False, board_slug, reason="ashby_fetch_failed")

                try:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        redirected = urljoin(str(response.url), location or "")
                        if not self._trusted_api_url(redirected):
                            return AshbyJobBoardResult(
                                False,
                                board_slug,
                                response.status_code,
                                reason="ashby_fetch_failed",
                            )
                        url = redirected
                        continue
                    if response.status_code == 404:
                        return AshbyJobBoardResult(
                            False, board_slug, 404, reason="ashby_board_not_found"
                        )
                    if response.status_code == 429:
                        return AshbyJobBoardResult(
                            False, board_slug, 429, reason="ashby_rate_limited"
                        )
                    if response.status_code >= 500:
                        if attempt < self.max_retries:
                            await asyncio.sleep(0.1 * (2**attempt))
                            continue
                        return AshbyJobBoardResult(
                            False,
                            board_slug,
                            response.status_code,
                            reason="ashby_fetch_failed",
                        )
                    if response.status_code != 200:
                        return AshbyJobBoardResult(
                            False,
                            board_slug,
                            response.status_code,
                            reason="ashby_fetch_failed",
                        )
                    content_type = response.headers.get("content-type", "").lower()
                    if "application/json" not in content_type:
                        return AshbyJobBoardResult(
                            False,
                            board_slug,
                            200,
                            reason="ashby_invalid_content_type",
                        )
                    content_length = response.headers.get("content-length")
                    if (
                        content_length
                        and content_length.isdigit()
                        and int(content_length) > self.max_response_bytes
                    ):
                        return AshbyJobBoardResult(
                            False,
                            board_slug,
                            200,
                            reason="ashby_response_too_large",
                        )
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self.max_response_bytes:
                            return AshbyJobBoardResult(
                                False,
                                board_slug,
                                200,
                                reason="ashby_response_too_large",
                            )
                    try:
                        payload = json.loads(body)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        return AshbyJobBoardResult(
                            False, board_slug, 200, reason="ashby_invalid_json"
                        )
                finally:
                    await response.aclose()
                jobs = parse_ashby_job_board(payload)
                if jobs is None:
                    return AshbyJobBoardResult(
                        False, board_slug, 200, reason="ashby_invalid_json"
                    )
                logger.info(
                    "Ashby board request completed",
                    extra={"board_slug": board_slug, "listed_job_count": len(jobs)},
                )
                return AshbyJobBoardResult(True, board_slug, 200, tuple(jobs))
        return AshbyJobBoardResult(False, board_slug, reason="ashby_fetch_failed")

    def match_job(
        self,
        candidate: DiscoveryCandidate,
        jobs: tuple[AshbyPublicJob, ...] | list[AshbyPublicJob],
    ) -> AshbyJobMatchResult:
        posting_id = self.extract_posting_id(candidate)
        path_parts = self._ashby_path_parts(self._candidate_url(candidate))
        if len(path_parts) >= 2 and posting_id is None:
            return AshbyJobMatchResult(False, reason="ashby_job_not_found")
        if posting_id:
            matches = [
                job for job in jobs if self._job_has_posting_id(job, posting_id)
            ]
            if len(matches) == 1:
                return AshbyJobMatchResult(
                    True, "exact_posting_id", 1.0, matches[0]
                )
            return AshbyJobMatchResult(False, reason="ashby_job_not_found")

        signal = " ".join(
            filter(
                None,
                [
                    (candidate.raw_payload or {}).get("title"),
                    candidate.raw_description,
                    candidate.normalized_description,
                ],
            )
        )
        signal_tokens = self._meaningful_tokens(signal)
        scored: list[tuple[int, AshbyPublicJob]] = []
        for job in jobs:
            fields = " ".join(
                filter(None, [job.title, job.team, job.department])
            )
            job_tokens = self._meaningful_tokens(fields)
            overlap = signal_tokens & job_tokens
            score = len(overlap)
            if "gtm" in signal_tokens and job_tokens & GTM_TERMS:
                score += 3
            if job.team and job.team.lower() in signal.lower():
                score += 3
            if job.department and job.department.lower() in signal.lower():
                score += 2
            if score >= 3:
                scored.append((score, job))
        if not scored:
            return AshbyJobMatchResult(False, reason="ashby_job_not_found")
        if len(scored) != 1:
            return AshbyJobMatchResult(
                False, reason="ambiguous_ashby_job_matches"
            )
        best_score, best_job = scored[0]
        return AshbyJobMatchResult(
            True,
            "board_signal_unique_strong_match",
            min(0.95, 0.65 + best_score * 0.05),
            best_job,
        )

    async def resolve(
        self,
        candidate: DiscoveryCandidate,
        board_result: AshbyJobBoardResult | None = None,
    ) -> AshbyCompanyResolutionResult:
        slug = self.extract_board_slug(candidate)
        if not slug:
            return AshbyCompanyResolutionResult(
                False, reason="ashby_board_slug_missing"
            )
        board = board_result or await self.fetch_job_board(slug)
        if not board.success:
            return AshbyCompanyResolutionResult(
                False,
                board_slug=slug,
                posting_id=self.extract_posting_id(candidate),
                status_code=board.status_code,
                reason=board.reason,
                evidence=self._evidence(board, None, (), board.reason),
            )
        match = self.match_job(candidate, board.jobs)
        if not match.matched or match.job is None:
            return AshbyCompanyResolutionResult(
                False,
                board_slug=slug,
                posting_id=self.extract_posting_id(candidate),
                status_code=board.status_code,
                reason=match.reason,
                evidence=self._evidence(board, match, (), match.reason),
            )
        proposals, rejected = self._domain_proposals(match.job)
        ranked = rank_domain_proposals(proposals)
        selected, selection_reason = select_resolvable_proposal(ranked)
        if not ranked:
            reason = "ashby_company_domain_missing"
        elif selection_reason == "ambiguous_domain_proposals":
            reason = "ashby_company_domain_ambiguous"
        else:
            reason = None
        final_reason = reason or "ashby_company_domain_evidence"
        evidence = self._evidence(board, match, proposals, final_reason)
        evidence["rejected_domain_proposals"] = rejected
        return AshbyCompanyResolutionResult(
            resolved=selected is not None,
            board_slug=slug,
            posting_id=self.extract_posting_id(candidate),
            matched_job=match.job,
            proposed_website_url=selected.proposal.value if selected else None,
            proposed_domain=selected.proposal.domain if selected else None,
            status_code=board.status_code,
            confidence=(
                min(match.confidence or 1.0, selected.confidence)
                if selected
                else match.confidence
            ),
            domain_proposals=tuple(proposals),
            evidence=evidence,
            reason=final_reason,
        )

    def _domain_proposals(
        self, job: AshbyPublicJob
    ) -> tuple[list[DomainProposal], list[dict[str, str]]]:
        text = "\n".join(
            value for value in (job.description_plain, job.description_html) if value
        )
        proposals: dict[str, DomainProposal] = {}
        rejected: list[dict[str, str]] = []
        for domain in extract_email_domains_from_text(text):
            if is_allowed_company_domain(domain):
                proposals.setdefault(
                    domain,
                    DomainProposal(
                        value=domain,
                        domain=domain,
                        source="ashby_job_description",
                        resolver="business_email_domain",
                        reason="business email in matched Ashby job",
                    ),
                )
            else:
                rejected.append({"value": domain, "reason": "blocked_or_shared_domain"})
        urls = extract_urls_from_text(text)
        if job.description_html:
            soup = BeautifulSoup(job.description_html, "html.parser")
            urls.extend(
                str(link.get("href"))
                for link in soup.find_all("a", href=True)
                if link.get("href")
            )
        for url in urls:
            domain = normalize_domain_proposal(url)
            if domain and is_allowed_company_domain(domain):
                proposals.setdefault(
                    domain,
                    DomainProposal(
                        value=url,
                        domain=domain,
                        source="ashby_job_description",
                        resolver="evidence_url",
                        reason="explicit URL in matched Ashby job",
                    ),
                )
            else:
                rejected.append({"value": url, "reason": "blocked_or_shared_domain"})
        return list(proposals.values()), rejected

    def _evidence(
        self,
        board: AshbyJobBoardResult,
        match: AshbyJobMatchResult | None,
        proposals: list[DomainProposal] | tuple[DomainProposal, ...],
        reason: str | None,
    ) -> dict[str, Any]:
        job = match.job if match else None
        return {
            "board_slug": board.board_slug,
            "http_status": board.status_code,
            "listed_job_count": len(board.jobs),
            "job_match_strategy": match.match_strategy if match else None,
            "job_match_confidence": match.confidence if match else None,
            "matched_job": (
                {"title": job.title, **job.focused_metadata()} if job else None
            ),
            "accepted_domain_proposals": [
                {
                    "value": proposal.value,
                    "domain": proposal.domain,
                    "resolver": proposal.resolver,
                    "reason": proposal.reason,
                }
                for proposal in proposals
            ],
            "final_resolution_reason": reason,
        }

    def _candidate_url(self, candidate: DiscoveryCandidate) -> str | None:
        payload = candidate.raw_payload or {}
        classification = payload.get("url_classification") or {}
        for value in (
            classification.get("original_url"),
            classification.get("external_url"),
            payload.get("url"),
            candidate.raw_website_url,
        ):
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _ashby_path_parts(self, value: str | None) -> list[str]:
        if not value:
            return []
        parsed = urlparse(value if "://" in value else f"https://{value}")
        if parsed.hostname != "jobs.ashbyhq.com":
            return []
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if any(
            part in {".", ".."} or "/" in part or "\\" in part
            for part in parts
        ):
            return []
        return parts

    def _valid_board_slug(self, value: str) -> bool:
        return bool(BOARD_SLUG_RE.fullmatch(value))

    def _trusted_api_url(self, value: str) -> bool:
        parsed = urlparse(value)
        return (parsed.scheme, parsed.hostname, parsed.port) == self._api_origin

    def _job_has_posting_id(self, job: AshbyPublicJob, posting_id: str) -> bool:
        for value in (job.raw_posting_id, job.job_url, job.apply_url):
            if not value:
                continue
            if value.lower() == posting_id:
                return True
            parts = [part.lower() for part in urlparse(value).path.split("/") if part]
            if posting_id in parts:
                return True
        return False

    def _meaningful_tokens(self, value: str) -> set[str]:
        return {
            token
            for token in MEANINGFUL_TOKEN_RE.findall(value.lower())
            if len(token) >= 2 and token not in GENERIC_TOKENS
        }
