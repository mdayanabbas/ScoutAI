import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import get_settings
from app.jobs.job_source_detector import compare_registrable_domains, normalize_job_url

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FirstPartyJobPageResponse:
    requested_url: str
    final_url: str | None = None
    normalized_domain: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    html: str | None = None
    response_size: int | None = None
    redirect_count: int = 0
    fetched_at: datetime | None = None
    robots_allowed: bool | None = None
    reason: str | None = None
    warnings: list[str] = field(default_factory=list)


class FirstPartyJobClient:
    def __init__(
        self,
        *,
        timeout_seconds: int | None = None,
        max_redirects: int | None = None,
        max_retries: int | None = None,
        max_response_bytes: int | None = None,
        user_agent: str | None = None,
        respect_robots: bool | None = None,
        allowed_content_types: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.timeout_seconds = timeout_seconds or settings.FIRST_PARTY_JOB_REQUEST_TIMEOUT_SECONDS
        self.max_redirects = settings.FIRST_PARTY_JOB_MAX_REDIRECTS if max_redirects is None else max_redirects
        self.max_retries = settings.FIRST_PARTY_JOB_MAX_RETRIES if max_retries is None else max_retries
        self.max_response_bytes = max_response_bytes or settings.FIRST_PARTY_JOB_MAX_RESPONSE_BYTES
        self.user_agent = user_agent or settings.FIRST_PARTY_JOB_USER_AGENT
        self.respect_robots = settings.FIRST_PARTY_JOB_RESPECT_ROBOTS if respect_robots is None else respect_robots
        self.allowed_content_types = {
            item.strip().lower()
            for item in (allowed_content_types or settings.FIRST_PARTY_JOB_ALLOWED_CONTENT_TYPES).split(",")
            if item.strip()
        }
        self.transport = transport
        self._robots_cache: dict[str, RobotFileParser] = {}

    async def fetch_job_page(self, url: str, *, company_domain: str) -> FirstPartyJobPageResponse:
        normalized = normalize_job_url(url)
        if not normalized.valid or not normalized.canonical_url:
            return FirstPartyJobPageResponse(url, reason=_normalize_url_reason(normalized.reason))
        if not compare_registrable_domains(normalized.normalized_domain, company_domain):
            return FirstPartyJobPageResponse(url, reason="first_party_unsafe_host")
        current_url = normalized.canonical_url
        redirects = 0
        warnings: list[str] = []

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers={"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"},
            follow_redirects=False,
            transport=self.transport,
        ) as client:
            robots_allowed = True
            if self.respect_robots:
                robots_allowed, robots_reason = await self._robots_allowed(client, current_url, company_domain)
                if not robots_allowed:
                    return FirstPartyJobPageResponse(
                        requested_url=normalized.canonical_url,
                        final_url=current_url,
                        normalized_domain=normalized.normalized_domain,
                        robots_allowed=False,
                        reason=robots_reason,
                        warnings=warnings,
                    )

            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.get(current_url)
                except httpx.TimeoutException:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return FirstPartyJobPageResponse(url, final_url=current_url, reason="first_party_request_timeout", warnings=warnings)
                except httpx.HTTPError:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return FirstPartyJobPageResponse(url, final_url=current_url, reason="first_party_provider_error", warnings=warnings)

                try:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        redirect_url = str(response.url.join(location or ""))
                        redirect_normalized = normalize_job_url(redirect_url)
                        if (
                            not redirect_normalized.valid
                            or not redirect_normalized.canonical_url
                            or not compare_registrable_domains(redirect_normalized.normalized_domain, company_domain)
                        ):
                            return FirstPartyJobPageResponse(
                                url,
                                final_url=current_url,
                                status_code=response.status_code,
                                redirect_count=redirects,
                                reason="first_party_redirect_rejected",
                                warnings=warnings,
                            )
                        redirects += 1
                        if redirects > self.max_redirects:
                            return FirstPartyJobPageResponse(url, final_url=current_url, status_code=response.status_code, redirect_count=redirects, reason="first_party_redirect_rejected")
                        current_url = redirect_normalized.canonical_url
                        continue
                    result = self._handle_response(
                        url,
                        current_url,
                        normalized.normalized_domain,
                        response,
                        redirects,
                        robots_allowed,
                        warnings,
                    )
                    if result.reason in {"first_party_rate_limited", "first_party_provider_error"} and attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return result
                finally:
                    await response.aclose()
        return FirstPartyJobPageResponse(url, final_url=current_url, reason="first_party_provider_error", warnings=warnings)

    def _handle_response(
        self,
        requested_url: str,
        final_url: str,
        normalized_domain: str | None,
        response: httpx.Response,
        redirects: int,
        robots_allowed: bool,
        warnings: list[str],
    ) -> FirstPartyJobPageResponse:
        body = response.content
        content_length = response.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > self.max_response_bytes:
            return FirstPartyJobPageResponse(requested_url, final_url, normalized_domain, response.status_code, response.headers.get("content-type"), response_size=int(content_length), redirect_count=redirects, robots_allowed=robots_allowed, reason="first_party_response_too_large")
        if len(body) > self.max_response_bytes:
            return FirstPartyJobPageResponse(requested_url, final_url, normalized_domain, response.status_code, response.headers.get("content-type"), response_size=len(body), redirect_count=redirects, robots_allowed=robots_allowed, reason="first_party_response_too_large")
        if response.status_code == 404:
            reason = "first_party_page_not_found"
        elif response.status_code == 410:
            reason = "first_party_page_gone"
        elif response.status_code == 403:
            reason = "first_party_page_forbidden"
        elif response.status_code == 429:
            reason = "first_party_rate_limited"
        elif response.status_code >= 500:
            reason = "first_party_provider_error"
        elif response.status_code != 200:
            reason = "first_party_provider_error"
        else:
            reason = None
        if reason:
            return FirstPartyJobPageResponse(requested_url, final_url, normalized_domain, response.status_code, response.headers.get("content-type"), response_size=len(body), redirect_count=redirects, robots_allowed=robots_allowed, reason=reason, warnings=warnings)
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in self.allowed_content_types:
            return FirstPartyJobPageResponse(requested_url, final_url, normalized_domain, response.status_code, content_type, response_size=len(body), redirect_count=redirects, robots_allowed=robots_allowed, reason="first_party_unexpected_content_type", warnings=warnings)
        if not body.strip():
            return FirstPartyJobPageResponse(requested_url, final_url, normalized_domain, response.status_code, content_type, response_size=0, redirect_count=redirects, robots_allowed=robots_allowed, reason="first_party_job_data_missing", warnings=warnings)
        text = response.text
        if _looks_antibot(text):
            return FirstPartyJobPageResponse(requested_url, final_url, normalized_domain, response.status_code, content_type, response_size=len(body), redirect_count=redirects, robots_allowed=robots_allowed, reason="first_party_antibot_challenge", warnings=warnings)
        logger.info("First-party page fetched", extra={"status_code": response.status_code, "response_size": len(body), "redirect_count": redirects})
        return FirstPartyJobPageResponse(
            requested_url=requested_url,
            final_url=final_url,
            normalized_domain=normalized_domain,
            status_code=response.status_code,
            content_type=content_type,
            html=text,
            response_size=len(body),
            redirect_count=redirects,
            fetched_at=datetime.now(timezone.utc),
            robots_allowed=robots_allowed,
            warnings=warnings,
        )

    async def _robots_allowed(
        self,
        client: httpx.AsyncClient,
        url: str,
        company_domain: str,
    ) -> tuple[bool, str | None]:
        parsed = urlparse(url)
        origin = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
        if origin in self._robots_cache:
            return self._robots_cache[origin].can_fetch(self.user_agent, url), "first_party_robots_disallowed"
        robots_url = f"{origin}/robots.txt"
        robots_normalized = normalize_job_url(robots_url)
        if not robots_normalized.valid or not compare_registrable_domains(robots_normalized.normalized_domain, company_domain):
            return False, "first_party_robots_unavailable"
        try:
            response = await client.get(robots_normalized.canonical_url)
        except httpx.HTTPError:
            return False, "first_party_robots_unavailable"
        try:
            if response.is_redirect:
                location = str(response.url.join(response.headers.get("location", "")))
                redirected = normalize_job_url(location)
                if not redirected.valid or not compare_registrable_domains(redirected.normalized_domain, company_domain):
                    return False, "first_party_robots_unavailable"
                response = await client.get(redirected.canonical_url)
            parser = RobotFileParser()
            if response.status_code in {404, 410}:
                parser.parse([])
            elif response.status_code != 200:
                return False, "first_party_robots_unavailable"
            else:
                parser.parse(response.text.splitlines())
            self._robots_cache[origin] = parser
            allowed = parser.can_fetch(self.user_agent, url)
            return allowed, None if allowed else "first_party_robots_disallowed"
        finally:
            await response.aclose()


def _normalize_url_reason(reason: str) -> str:
    if reason in {"unsafe_host", "embedded_credentials", "unsupported_scheme", "malformed_job_url"}:
        return "first_party_unsafe_host"
    return "first_party_unsafe_host"


def _looks_antibot(html: str) -> bool:
    lower = html[:5000].lower()
    return any(token in lower for token in ("cloudflare", "captcha", "are you human", "access denied"))

