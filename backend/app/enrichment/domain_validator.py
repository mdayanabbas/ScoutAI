import asyncio
import ipaddress
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.enrichment.domain_extractor import is_allowed_company_domain, is_valid_hostname
from app.utils.urls import normalize_domain


@dataclass(frozen=True)
class DomainValidationResult:
    valid: bool
    requested_url: str
    final_url: str | None = None
    normalized_domain: str | None = None
    status_code: int | None = None
    reason: str | None = None
    redirect_count: int = 0


class DomainValidator:
    def __init__(
        self,
        timeout_seconds: int | None = None,
        max_redirects: int | None = None,
        user_agent: str | None = None,
    ) -> None:
        settings = get_settings()
        self.timeout_seconds = (
            timeout_seconds or settings.COMPANY_ENRICHMENT_REQUEST_TIMEOUT_SECONDS
        )
        self.max_redirects = max_redirects or settings.COMPANY_ENRICHMENT_MAX_REDIRECTS
        self.user_agent = user_agent or settings.COMPANY_ENRICHMENT_USER_AGENT

    async def validate(self, value: str) -> DomainValidationResult:
        requested_url = _ensure_url(value)
        parsed = urlparse(requested_url)
        host = parsed.hostname
        if parsed.scheme not in {"http", "https"}:
            return _invalid(requested_url, "unsupported_scheme")
        if parsed.username or parsed.password:
            return _invalid(requested_url, "embedded_credentials")
        if not host:
            return _invalid(requested_url, "invalid_hostname")
        if _is_localhost_name(host) or _is_unsafe_ip_host(host):
            return _invalid(requested_url, "unsafe_host")
        if not _is_ip_host(host) and not is_valid_hostname(host):
            return _invalid(requested_url, "invalid_hostname")
        domain = normalize_domain(host)
        if not is_allowed_company_domain(domain):
            return _invalid(requested_url, "blocked_or_shared_domain")
        if not await self._host_is_public(host):
            return _invalid(requested_url, "unsafe_host")

        current_url = requested_url
        redirects = 0
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers={"User-Agent": self.user_agent},
            follow_redirects=False,
        ) as client:
            while True:
                response = await self._request(client, current_url)
                if response is None:
                    return _invalid(requested_url, "unreachable")
                status_code = response.status_code
                if status_code in {301, 302, 303, 307, 308} and response.headers.get(
                    "location"
                ):
                    redirects += 1
                    if redirects > self.max_redirects:
                        return _invalid(requested_url, "too_many_redirects")
                    current_url = str(response.url.join(response.headers["location"]))
                    parsed = urlparse(current_url)
                    if parsed.scheme not in {"http", "https"}:
                        return _invalid(requested_url, "unsupported_redirect_scheme")
                    if (
                        parsed.username
                        or parsed.password
                    ):
                        return _invalid(requested_url, "unsafe_redirect")
                    if not parsed.hostname:
                        return _invalid(requested_url, "unsafe_redirect")
                    if _is_localhost_name(parsed.hostname) or _is_unsafe_ip_host(parsed.hostname):
                        return _invalid(requested_url, "unsafe_redirect_host")
                    if not _is_ip_host(parsed.hostname) and not is_valid_hostname(parsed.hostname):
                        return _invalid(requested_url, "unsafe_redirect")
                    redirect_domain = normalize_domain(parsed.hostname)
                    if not is_allowed_company_domain(redirect_domain):
                        return _invalid(requested_url, "blocked_redirect_domain")
                    if not await self._host_is_public(parsed.hostname):
                        return _invalid(requested_url, "unsafe_redirect_host")
                    continue
                final_domain = normalize_domain(urlparse(str(response.url)).hostname or host)
                return DomainValidationResult(
                    valid=200 <= status_code < 500,
                    requested_url=requested_url,
                    final_url=str(response.url),
                    normalized_domain=final_domain,
                    status_code=status_code,
                    reason=None if 200 <= status_code < 500 else "unreachable",
                    redirect_count=redirects,
                )

    async def _request(
        self, client: httpx.AsyncClient, url: str
    ) -> httpx.Response | None:
        try:
            response = await client.head(url)
            if response.status_code in {405, 501}:
                response = await client.get(url, headers={"Range": "bytes=0-2048"})
            return response
        except httpx.HTTPError:
            return None

    async def _host_is_public(self, host: str) -> bool:
        try:
            ip = ipaddress.ip_address(host)
            return _is_public_ip(ip)
        except ValueError:
            pass
        if host.lower() == "localhost" or host.endswith(".localhost"):
            return False
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(host, None)
        except OSError:
            return False
        ips = {info[4][0] for info in infos}
        return bool(ips) and all(_is_public_ip(ipaddress.ip_address(ip)) for ip in ips)


def _ensure_url(value: str) -> str:
    trimmed = value.strip()
    return trimmed if "://" in trimmed else f"https://{trimmed}"


def _is_public_ip(ip: ipaddress._BaseAddress) -> bool:
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _is_ip_host(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _is_unsafe_ip_host(host: str) -> bool:
    try:
        return not _is_public_ip(ipaddress.ip_address(host))
    except ValueError:
        return False


def _is_localhost_name(host: str) -> bool:
    value = host.lower().rstrip(".")
    return (
        value == "localhost"
        or value == "localhost.localdomain"
        or value.endswith(".localhost")
    )


def _invalid(url: str, reason: str) -> DomainValidationResult:
    return DomainValidationResult(valid=False, requested_url=url, reason=reason)
