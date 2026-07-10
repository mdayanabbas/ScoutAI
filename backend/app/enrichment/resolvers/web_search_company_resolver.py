import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.enrichment.company_identity_checker import (
    CompanyIdentityCheckResult,
    HomepageMetadata,
    check_company_identity,
    extract_homepage_metadata,
)
from app.enrichment.domain_extractor import (
    is_allowed_company_domain,
    normalize_domain_proposal,
)
from app.enrichment.domain_validator import DomainValidator
from app.models.discovery_candidate import DiscoveryCandidate
from app.search.providers.base import WebSearchProvider, WebSearchResult
from app.search.providers.factory import create_web_search_provider
from app.utils.enums import DiscoveryCandidateStatus, DiscoveryDecision
from app.utils.urls import normalize_domain

logger = logging.getLogger(__name__)

MIN_CONFIDENCE = 0.90
MIN_SCORE_GAP = 0.10
MAX_QUERY_LENGTH = 180
MAX_HOMEPAGE_BYTES = 200_000
BLOCKED_PATH_PARTS = {
    "blog",
    "careers",
    "directory",
    "jobs",
    "news",
    "profile",
    "reviews",
}
NEGATIVE_TITLE_TERMS = {
    "crunchbase",
    "funding",
    "linkedin",
    "product hunt",
    "profile",
    "review",
}


@dataclass(frozen=True)
class ScoredSearchResult:
    result: WebSearchResult
    domain: str
    homepage_url: str
    score: float
    signals: tuple[str, ...] = ()
    negative_signals: tuple[str, ...] = ()
    query: str | None = None


@dataclass(frozen=True)
class WebSearchCompanyResolutionResult:
    resolved: bool
    proposed_website_url: str | None = None
    proposed_domain: str | None = None
    confidence: float | None = None
    selected_result: dict[str, Any] | None = None
    provider: str | None = None
    queries: tuple[str, ...] = ()
    corroborating_results: tuple[dict[str, Any], ...] = ()
    rejected_results: tuple[dict[str, Any], ...] = ()
    identity_check: CompanyIdentityCheckResult | None = None
    reason: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


class WebSearchCompanyResolver:
    def __init__(
        self,
        *,
        provider: WebSearchProvider | None = None,
        validator: DomainValidator | None = None,
        timeout_seconds: int | None = None,
        max_response_bytes: int | None = None,
        user_agent: str | None = None,
        query_cache: dict[str, Any] | None = None,
    ) -> None:
        settings = get_settings()
        self.enabled = settings.WEB_SEARCH_ENABLED
        self.provider = provider or create_web_search_provider()
        self.validator = validator or DomainValidator()
        self.max_queries = max(1, settings.WEB_SEARCH_MAX_QUERIES_PER_CANDIDATE)
        self.results_per_query = min(settings.WEB_SEARCH_RESULTS_PER_QUERY, 20)
        self.timeout_seconds = (
            timeout_seconds or settings.WEB_SEARCH_REQUEST_TIMEOUT_SECONDS
        )
        self.max_response_bytes = max_response_bytes or settings.WEB_SEARCH_MAX_RESPONSE_BYTES
        self.user_agent = user_agent or settings.TAVILY_USER_AGENT
        self.query_cache = query_cache if query_cache is not None else {}

    def supports(self, candidate: DiscoveryCandidate) -> bool:
        if not self.enabled:
            return False
        if candidate.decision != DiscoveryDecision.DEFERRED:
            return False
        if candidate.deferred_reason != "requires_company_domain_enrichment":
            return False
        if candidate.status == DiscoveryCandidateStatus.INGESTED:
            return False
        if not (candidate.normalized_name or "").strip():
            return False
        payload = candidate.raw_payload or {}
        title = f"{payload.get('title') or ''} {candidate.raw_description or ''}".lower()
        if "show hn" in title:
            return False
        return True

    def build_queries(self, candidate: DiscoveryCandidate) -> tuple[str, ...]:
        name = _clean_query_term(candidate.normalized_name or candidate.raw_name)
        if not name:
            return ()
        payload = candidate.raw_payload or {}
        classification = payload.get("url_classification") or {}
        contexts: list[str] = ["official website company"]
        yc_batch = _extract_yc_batch(candidate)
        yc_slug = classification.get("external_company_slug")
        if yc_batch:
            contexts.append(f"YC {yc_batch}")
        elif classification.get("platform") == "ycombinator":
            contexts.append("YC official website")
        if classification.get("platform") == "ashby":
            contexts.append("Ashby jobs official")
        elif isinstance(yc_slug, str):
            contexts.append(f"{_clean_query_term(yc_slug)} startup official")
        role_context = _safe_role_context(candidate)
        if role_context:
            contexts.append(role_context)
        queries = []
        for context in contexts:
            query = f'"{name}" {context}'.strip()
            if len(query) <= MAX_QUERY_LENGTH:
                queries.append(query)
        return tuple(dict.fromkeys(queries))[: self.max_queries]

    async def resolve(
        self, candidate: DiscoveryCandidate
    ) -> WebSearchCompanyResolutionResult:
        if not self.supports(candidate):
            reason = "web_search_disabled" if not self.enabled else "web_search_not_eligible"
            return WebSearchCompanyResolutionResult(
                False, provider=self.provider.name, reason=reason
            )
        queries = self.build_queries(candidate)
        if not queries:
            return WebSearchCompanyResolutionResult(
                False,
                provider=self.provider.name,
                reason="web_search_not_eligible",
                queries=queries,
            )
        rejected: list[dict[str, Any]] = []
        scored: list[ScoredSearchResult] = []
        api_status: list[dict[str, Any]] = []
        for query in queries:
            response = await self._cached_search(query)
            api_status.append(
                {
                    "query": query,
                    "success": response.success,
                    "status_code": response.status_code,
                    "reason": response.reason,
                    "result_count": len(response.results),
                }
            )
            if not response.success:
                logger.info(
                    "Web search provider failure",
                    extra={"provider": self.provider.name, "reason": response.reason},
                )
                return self._unresolved(
                    response.reason or "web_search_provider_error",
                    queries,
                    rejected,
                    api_status,
                )
            for result in response.results:
                score = self.score_result(candidate, result, query=query)
                if score is None:
                    rejected.append(
                        {
                            "url": result.url,
                            "domain": normalize_domain_proposal(result.url),
                            "reason": "blocked_or_untrustworthy_result",
                        }
                    )
                    continue
                scored.append(score)
        if not scored:
            reason = "no_search_results" if not rejected else "no_trustworthy_company_domain"
            return self._unresolved(reason, queries, rejected, api_status)

        selected, reason = self.select_domain(candidate, scored)
        if selected is None:
            return self._unresolved(reason, queries, rejected, api_status, scored)

        validation = await self.validator.validate(selected.homepage_url)
        if not validation.valid or not validation.final_url or not validation.normalized_domain:
            rejected.append(
                {
                    "domain": selected.domain,
                    "url": selected.homepage_url,
                    "reason": validation.reason or "selected_domain_validation_failed",
                }
            )
            return self._unresolved(
                "selected_domain_validation_failed", queries, rejected, api_status, scored
            )
        metadata = await self._fetch_homepage_metadata(validation.final_url)
        identity_check = check_company_identity(
            candidate.normalized_name or candidate.raw_name,
            metadata,
        )
        logger.info(
            "Homepage identity checked",
            extra={
                "candidate_id": candidate.id,
                "domain": validation.normalized_domain,
                "matched": identity_check.matched,
            },
        )
        if not identity_check.matched:
            rejected.append(
                {
                    "domain": selected.domain,
                    "url": selected.homepage_url,
                    "reason": identity_check.reason or "homepage_identity_mismatch",
                }
            )
            return self._unresolved(
                "homepage_identity_mismatch", queries, rejected, api_status, scored
            )
        confidence = min(0.98, selected.score, identity_check.confidence)
        evidence = self._evidence(
            queries, rejected, api_status, scored, selected, identity_check, metadata
        )
        logger.info(
            "Web search domain selected",
            extra={
                "candidate_id": candidate.id,
                "domain": validation.normalized_domain,
                "confidence": confidence,
            },
        )
        return WebSearchCompanyResolutionResult(
            True,
            proposed_website_url=validation.final_url,
            proposed_domain=validation.normalized_domain,
            confidence=confidence,
            selected_result=_result_evidence(selected),
            provider=self.provider.name,
            queries=queries,
            corroborating_results=tuple(
                _result_evidence(item)
                for item in scored
                if item.domain == selected.domain
            ),
            rejected_results=tuple(rejected),
            identity_check=identity_check,
            reason="web_search_company_identity_resolved",
            evidence=evidence,
        )

    def score_result(
        self,
        candidate: DiscoveryCandidate,
        result: WebSearchResult,
        *,
        query: str | None = None,
    ) -> ScoredSearchResult | None:
        domain = normalize_domain_proposal(result.url)
        if not domain or not is_allowed_company_domain(domain):
            return None
        parsed = urlparse(result.url if "://" in result.url else f"https://{result.url}")
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
            return None
        if _blocked_path(parsed.path):
            return None
        title = result.title or ""
        description = result.description or ""
        haystack = f"{title} {description}".lower()
        if any(term in haystack for term in NEGATIVE_TITLE_TERMS):
            return None

        expected = _identity_text(candidate.normalized_name or candidate.raw_name)
        title_identity = _identity_text(title)
        description_identity = _identity_text(description)
        signals: list[str] = []
        negatives: list[str] = []
        score = 0.0
        if expected and (title_identity == expected or title_identity.startswith(expected)):
            score += 0.45
            signals.append("exact_name_in_title")
        if expected and expected in description_identity:
            score += 0.20
            signals.append("exact_name_in_description")
        if _is_rootish_homepage(parsed.path):
            score += 0.20
            signals.append("root_homepage")
        else:
            score -= 0.15
            negatives.append("non_homepage_path")
        payload = candidate.raw_payload or {}
        if _context_matches(payload, haystack):
            score += 0.10
            signals.append("context_match")
        if result.rank:
            score += max(0.0, 0.05 - ((result.rank - 1) * 0.005))
        if not signals:
            return None
        confidence = min(0.98, score)
        homepage_url = f"https://{_registrable_domain(domain)}"
        return ScoredSearchResult(
            result=result,
            domain=_registrable_domain(domain),
            homepage_url=homepage_url,
            score=confidence,
            signals=tuple(signals),
            negative_signals=tuple(negatives),
            query=query,
        )

    def select_domain(
        self,
        candidate: DiscoveryCandidate,
        scored: list[ScoredSearchResult],
    ) -> tuple[ScoredSearchResult | None, str]:
        grouped: dict[str, list[ScoredSearchResult]] = {}
        for item in scored:
            grouped.setdefault(item.domain, []).append(item)
        domain_scores: list[tuple[float, str, ScoredSearchResult]] = []
        for domain, items in grouped.items():
            best = max(items, key=lambda item: item.score)
            query_count = len({item.query for item in items if item.query})
            score = best.score
            if query_count >= 2:
                score = max(score, 0.98 if best.score >= 0.75 else best.score + 0.10)
            best = ScoredSearchResult(
                result=best.result,
                domain=best.domain,
                homepage_url=best.homepage_url,
                score=min(0.98, score),
                signals=tuple(dict.fromkeys((*best.signals, "corroborated_queries")))
                if query_count >= 2
                else best.signals,
                negative_signals=best.negative_signals,
                query=best.query,
            )
            domain_scores.append((best.score, domain, best))
            logger.info(
                "Web search domain candidate scored",
                extra={"domain": domain, "score": best.score},
            )
        domain_scores.sort(key=lambda item: item[0], reverse=True)
        best_score, _, best = domain_scores[0]
        if best_score < MIN_CONFIDENCE:
            return None, "no_trustworthy_company_domain"
        if len(domain_scores) > 1 and (best_score - domain_scores[1][0]) < MIN_SCORE_GAP:
            return None, "ambiguous_search_company_domains"
        return best, "web_search_company_identity_resolved"

    async def _cached_search(self, query: str):
        if query not in self.query_cache:
            self.query_cache[query] = await self.provider.search(
                query, count=self.results_per_query
            )
        return self.query_cache[query]

    async def _fetch_homepage_metadata(self, url: str) -> HomepageMetadata | None:
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers={"User-Agent": self.user_agent, "Accept": "text/html"},
            follow_redirects=False,
        ) as client:
            try:
                response = await client.send(client.build_request("GET", url), stream=True)
            except httpx.HTTPError:
                return None
            try:
                content_type = response.headers.get("content-type", "").lower()
                if "html" not in content_type:
                    return HomepageMetadata(
                        url=url, status_code=response.status_code, reason="non_html_homepage"
                    )
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > min(self.max_response_bytes, MAX_HOMEPAGE_BYTES):
                        break
                html = body.decode(response.encoding or "utf-8", errors="ignore")
                return extract_homepage_metadata(
                    html, str(response.url), status_code=response.status_code
                )
            finally:
                await response.aclose()

    def _unresolved(
        self,
        reason: str | None,
        queries: tuple[str, ...],
        rejected: list[dict[str, Any]],
        api_status: list[dict[str, Any]] | None = None,
        scored: list[ScoredSearchResult] | None = None,
    ) -> WebSearchCompanyResolutionResult:
        evidence = {
            "provider": self.provider.name,
            "queries": list(queries),
            "api_status": api_status or [],
            "candidate_domains": [_score_evidence(item) for item in scored or []],
            "rejected_results": rejected,
            "resolution_reason": reason,
        }
        return WebSearchCompanyResolutionResult(
            False,
            provider=self.provider.name,
            queries=queries,
            rejected_results=tuple(rejected),
            reason=reason,
            evidence=evidence,
        )

    def _evidence(
        self,
        queries: tuple[str, ...],
        rejected: list[dict[str, Any]],
        api_status: list[dict[str, Any]],
        scored: list[ScoredSearchResult],
        selected: ScoredSearchResult,
        identity_check: CompanyIdentityCheckResult,
        metadata: HomepageMetadata | None,
    ) -> dict[str, Any]:
        return {
            "provider": self.provider.name,
            "queries": list(queries),
            "api_status": api_status,
            "result_count": sum(item.get("result_count", 0) for item in api_status),
            "candidate_domains": [_score_evidence(item) for item in scored],
            "result_scores": [_score_evidence(item) for item in scored],
            "selected_domain": selected.domain,
            "selected_confidence": selected.score,
            "identity_check": {
                "matched": identity_check.matched,
                "confidence": identity_check.confidence,
                "matched_signals": list(identity_check.matched_signals),
                "conflicting_signals": list(identity_check.conflicting_signals),
                "reason": identity_check.reason,
            },
            "homepage_metadata": _metadata_evidence(metadata),
            "rejected_results": rejected,
            "resolution_reason": "web_search_company_identity_resolved",
        }


def _result_evidence(item: ScoredSearchResult) -> dict[str, Any]:
    return {
        "title": item.result.title[:160],
        "url": item.result.url,
        "domain": item.domain,
        "rank": item.result.rank,
        "score": item.score,
        "signals": list(item.signals),
        "negative_signals": list(item.negative_signals),
        "query": item.query,
    }


def _score_evidence(item: ScoredSearchResult) -> dict[str, Any]:
    return _result_evidence(item)


def _metadata_evidence(metadata: HomepageMetadata | None) -> dict[str, Any] | None:
    if metadata is None:
        return None
    return {
        "url": metadata.url,
        "title": metadata.title,
        "og_site_name": metadata.og_site_name,
        "og_title": metadata.og_title,
        "organization_names": list(metadata.organization_names),
        "canonical_url": metadata.canonical_url,
        "header_text": metadata.header_text,
        "status_code": metadata.status_code,
        "reason": metadata.reason,
    }


def _clean_query_term(value: str | None) -> str:
    cleaned = re.sub(r"[\r\n\t]+", " ", value or "")
    cleaned = re.sub(r"[\"<>@]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()[:80]


def _extract_yc_batch(candidate: DiscoveryCandidate) -> str | None:
    values = [
        (candidate.raw_payload or {}).get("yc_batch"),
        ((candidate.raw_payload or {}).get("metadata") or {}).get("batch")
        if isinstance((candidate.raw_payload or {}).get("metadata"), dict)
        else None,
    ]
    for value in values:
        if isinstance(value, str) and re.fullmatch(r"[WSF]\d{2}", value.strip(), re.I):
            return value.strip().upper()
    return None


def _safe_role_context(candidate: DiscoveryCandidate) -> str | None:
    payload = candidate.raw_payload or {}
    title = payload.get("title")
    if not isinstance(title, str):
        return None
    title = re.sub(r"[\w.+-]+@[\w.-]+", " ", title)
    tokens = re.findall(r"[A-Za-z0-9+#.]{2,30}", title)
    keep = [
        token
        for token in tokens
        if token.lower()
        not in {"hiring", "is", "at", "for", "the", "and", "with", "remote"}
    ][:5]
    return " ".join(keep) if keep else None


def _blocked_path(path: str) -> bool:
    parts = {part.lower() for part in path.split("/") if part}
    return bool(parts & BLOCKED_PATH_PARTS)


def _is_rootish_homepage(path: str) -> bool:
    parts = [part for part in path.split("/") if part]
    return len(parts) == 0


def _identity_text(value: str | None) -> str:
    cleaned = re.sub(r"\b(inc|llc|ltd|limited|gmbh|corp|corporation|co)\b\.?", " ", value or "", flags=re.I)
    cleaned = re.sub(r"[\W_]+", " ", cleaned.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _context_matches(payload: dict[str, Any], haystack: str) -> bool:
    classification = payload.get("url_classification") or {}
    for value in (
        payload.get("yc_batch"),
        classification.get("external_company_slug"),
        payload.get("title"),
    ):
        if isinstance(value, str):
            token = _identity_text(value)
            if token and token in haystack:
                return True
    return False


def _registrable_domain(domain: str) -> str:
    value = normalize_domain(domain).lower()
    if value.startswith("www."):
        value = value[4:]
    parts = value.split(".")
    if len(parts) <= 2:
        return value
    if len(parts[-1]) == 2 and len(parts[-2]) <= 3 and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])
