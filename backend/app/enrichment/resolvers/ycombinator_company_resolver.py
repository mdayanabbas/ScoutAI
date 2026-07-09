import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from app.core.config import get_settings
from app.enrichment.yc_profile_parser import parse_yc_company_profile
from app.models.discovery_candidate import DiscoveryCandidate
from app.utils.enums import DiscoveryDecision
from app.utils.urls import normalize_domain

logger = logging.getLogger(__name__)

YC_SLUG_RE = re.compile(r"^[a-z0-9-]{1,80}$")
MAX_HTML_BYTES = 1_000_000


@dataclass(frozen=True)
class YCCompanyResolutionResult:
    resolved: bool
    company_slug: str | None = None
    profile_url: str | None = None
    proposed_website_url: str | None = None
    proposed_domain: str | None = None
    company_name: str | None = None
    description: str | None = None
    location: str | None = None
    batch: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None
    status_code: int | None = None
    confidence: float | None = None


class YCombinatorCompanyResolver:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        user_agent: str | None = None,
    ) -> None:
        settings = get_settings()
        self.enabled = settings.YC_COMPANY_RESOLVER_ENABLED
        self.base_url = (base_url or settings.YC_COMPANY_BASE_URL).rstrip("/")
        self.timeout_seconds = (
            timeout_seconds or settings.YC_COMPANY_REQUEST_TIMEOUT_SECONDS
        )
        self.max_retries = max_retries if max_retries is not None else settings.YC_COMPANY_MAX_RETRIES
        self.user_agent = user_agent or settings.YC_COMPANY_USER_AGENT
        self.allowed_host = urlparse(self.base_url).hostname or "www.ycombinator.com"

    def supports(self, candidate: DiscoveryCandidate) -> bool:
        if not self.enabled:
            return False
        if (
            candidate.decision != DiscoveryDecision.DEFERRED
            or candidate.deferred_reason != "requires_company_domain_enrichment"
        ):
            return False
        return self.extract_company_slug(candidate) is not None

    def extract_company_slug(self, candidate: DiscoveryCandidate) -> str | None:
        classification = (candidate.raw_payload or {}).get("url_classification") or {}
        if classification.get("platform") == "ycombinator":
            slug = classification.get("external_company_slug")
            if self._valid_slug(slug):
                return str(slug)
            if slug:
                return None

        for value in [
            candidate.raw_website_url,
            candidate.normalized_website_url,
            (candidate.raw_payload or {}).get("url"),
            classification.get("original_url"),
            classification.get("external_url"),
        ]:
            slug = self._extract_slug_from_url(value)
            if slug:
                return slug
        return None

    def build_profile_url(self, slug: str) -> str:
        if not self._valid_slug(slug):
            raise ValueError("Invalid YC company slug")
        return f"{self.base_url}/{slug}"

    async def resolve(
        self, candidate: DiscoveryCandidate
    ) -> YCCompanyResolutionResult:
        slug = self.extract_company_slug(candidate)
        if not slug:
            logger.info("YC company slug missing", extra={"candidate_id": candidate.id})
            return YCCompanyResolutionResult(resolved=False, reason="yc_slug_missing")
        if not self._valid_slug(slug):
            logger.info(
                "YC company slug invalid",
                extra={"candidate_id": candidate.id, "company_slug": slug},
            )
            return YCCompanyResolutionResult(
                resolved=False, company_slug=slug, reason="yc_slug_invalid"
            )

        profile_url = self.build_profile_url(slug)
        logger.info(
            "YC profile request started",
            extra={"candidate_id": candidate.id, "company_slug": slug, "profile_url": profile_url},
        )
        html, status_code, reason = await self._fetch_profile(profile_url)
        logger.info(
            "YC profile request completed",
            extra={
                "candidate_id": candidate.id,
                "company_slug": slug,
                "status_code": status_code,
                "reason": reason,
            },
        )
        if html is None:
            return YCCompanyResolutionResult(
                resolved=False,
                company_slug=slug,
                profile_url=profile_url,
                reason=reason,
                status_code=status_code,
            )

        parsed = parse_yc_company_profile(html, profile_url)
        logger.info(
            "YC profile parsing completed",
            extra={
                "candidate_id": candidate.id,
                "company_slug": slug,
                "resolved": parsed.resolved,
                "reason": parsed.reason,
                "proposed_domain": parsed.proposed_domain,
                "anchors": (parsed.evidence.get("stats") or {}).get(
                    "anchors_inspected"
                ),
                "external": (parsed.evidence.get("stats") or {}).get(
                    "external_anchors"
                ),
                "allowed": (parsed.evidence.get("stats") or {}).get(
                    "allowed_company_domain_candidates"
                ),
                "strategy": parsed.evidence.get("extraction_strategy"),
            },
        )
        return YCCompanyResolutionResult(
            resolved=parsed.resolved,
            company_slug=slug,
            profile_url=profile_url,
            proposed_website_url=parsed.proposed_website_url,
            proposed_domain=parsed.proposed_domain,
            company_name=parsed.company_name,
            description=parsed.description,
            location=parsed.location,
            batch=parsed.batch,
            evidence=parsed.evidence,
            reason=parsed.reason,
            status_code=status_code,
            confidence=parsed.confidence,
        )

    async def _fetch_profile(
        self, profile_url: str
    ) -> tuple[str | None, int | None, str | None]:
        current_url = profile_url
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers={"User-Agent": self.user_agent},
            follow_redirects=False,
        ) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.get(current_url)
                except httpx.TimeoutException:
                    if attempt >= self.max_retries:
                        return None, None, "yc_profile_timeout"
                    await asyncio.sleep(0.1 * (2**attempt))
                    continue
                except httpx.HTTPError:
                    if attempt >= self.max_retries:
                        return None, None, "yc_profile_fetch_failed"
                    await asyncio.sleep(0.1 * (2**attempt))
                    continue

                status_code = response.status_code
                if status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        return None, status_code, "yc_profile_fetch_failed"
                    redirected_url = str(response.url.join(location))
                    if not self._redirect_allowed(redirected_url):
                        return None, status_code, "yc_profile_fetch_failed"
                    current_url = redirected_url
                    continue
                if status_code == 404:
                    return None, status_code, "yc_profile_not_found"
                if status_code == 429:
                    return None, status_code, "yc_profile_rate_limited"
                if status_code >= 500:
                    if attempt >= self.max_retries:
                        return None, status_code, "yc_profile_fetch_failed"
                    await asyncio.sleep(0.1 * (2**attempt))
                    continue
                if status_code != 200:
                    return None, status_code, "yc_profile_fetch_failed"

                content_type = response.headers.get("content-type", "").lower()
                if "html" not in content_type:
                    return None, status_code, "yc_profile_invalid_content"
                if len(response.content) > MAX_HTML_BYTES:
                    return None, status_code, "yc_profile_invalid_content"
                return response.text, status_code, None
        return None, None, "yc_profile_fetch_failed"

    def _extract_slug_from_url(self, value: str | None) -> str | None:
        if not value:
            return None
        parsed = urlparse(value if "://" in value else f"https://{value}")
        host = normalize_domain(parsed.hostname or "")
        if host != "ycombinator.com":
            return None
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "companies" and self._valid_slug(parts[1]):
            if len(parts) == 2 or parts[2] == "jobs":
                return parts[1]
        return None

    def _valid_slug(self, value: Any) -> bool:
        return isinstance(value, str) and bool(YC_SLUG_RE.fullmatch(value))

    def _redirect_allowed(self, value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme == "https" and parsed.hostname == self.allowed_host
