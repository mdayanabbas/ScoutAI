import asyncio
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.discovery.sources.remotive.constants import REMOTIVE_ALLOWED_HOST
from app.discovery.sources.remotive.models import RemotiveJobsResponse, parse_remotive_jobs_response


class RemotiveRemoteJobsClient:
    def __init__(
        self,
        *,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        max_response_bytes: int | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = settings.REMOTIVE_API_BASE_URL.rstrip("/")
        self.jobs_path = settings.REMOTIVE_JOBS_PATH
        self.timeout_seconds = timeout_seconds or settings.REMOTIVE_REQUEST_TIMEOUT_SECONDS
        self.max_retries = settings.REMOTIVE_MAX_RETRIES if max_retries is None else max_retries
        self.max_response_bytes = max_response_bytes or settings.REMOTIVE_MAX_RESPONSE_BYTES
        self.transport = transport

    async def list_jobs(
        self,
        *,
        category: str | None = None,
        search: str | None = None,
        limit: int | None = None,
    ) -> RemotiveJobsResponse:
        url = self._jobs_url()
        if url is None:
            return _error("remotive_invalid_provider_host")
        params = _params(category=category, search=search, limit=limit)
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers={"Accept": "application/json", "User-Agent": "ScoutAI/0.1 remotive-discovery"},
            follow_redirects=False,
            transport=self.transport,
        ) as client:
            current_url = url
            redirects = 0
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.get(current_url, params=params if current_url == url else None)
                except httpx.TimeoutException:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return _error("remotive_request_timeout")
                except httpx.HTTPError:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return _error("remotive_provider_error")
                try:
                    if response.is_redirect:
                        redirected = str(response.url.join(response.headers.get("location") or ""))
                        if not _allowed_url(redirected):
                            return _error("remotive_redirect_rejected", status_code=response.status_code)
                        redirects += 1
                        if redirects > 3:
                            return _error("remotive_redirect_rejected", status_code=response.status_code)
                        current_url = redirected
                        continue
                    result = self._handle_response(response)
                    if result.reason == "remotive_provider_error" and attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return result
                finally:
                    await response.aclose()
        return _error("remotive_provider_error")

    def _jobs_url(self) -> str | None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or parsed.hostname != REMOTIVE_ALLOWED_HOST:
            return None
        path = self.jobs_path if self.jobs_path.startswith("/") else f"/{self.jobs_path}"
        url = f"{self.base_url}{path}"
        return url if _allowed_url(url) else None

    def _handle_response(self, response: httpx.Response) -> RemotiveJobsResponse:
        status_code = response.status_code
        content_length = response.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > self.max_response_bytes:
            return _error("remotive_response_too_large", status_code=status_code, response_size=int(content_length))
        body = response.content
        if len(body) > self.max_response_bytes:
            return _error("remotive_response_too_large", status_code=status_code, response_size=len(body))
        stripped = body.lstrip()[:100].lower()
        if stripped.startswith(b"<!doctype html") or stripped.startswith(b"<html"):
            return _error("remotive_html_response", status_code=status_code, response_size=len(body))
        if status_code == 400:
            return _error("remotive_bad_request", status_code=status_code, response_size=len(body))
        if status_code == 429:
            return _error("remotive_rate_limited", status_code=status_code, response_size=len(body))
        if status_code >= 500:
            return _error("remotive_provider_error", status_code=status_code, response_size=len(body))
        if status_code != 200:
            return _error("remotive_provider_error", status_code=status_code, response_size=len(body))
        try:
            payload = response.json()
        except ValueError:
            return _error("remotive_invalid_json", status_code=status_code, response_size=len(body))
        return parse_remotive_jobs_response(payload, status_code=status_code, response_size=len(body))


def _params(*, category: str | None, search: str | None, limit: int | None) -> list[tuple[str, str]]:
    params: list[tuple[str, str]] = []
    if category:
        params.append(("category", category))
    if search:
        params.append(("search", search))
    if limit is not None:
        params.append(("limit", str(max(1, limit))))
    return params


def _allowed_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname == REMOTIVE_ALLOWED_HOST
        and not parsed.username
        and not parsed.password
        and parsed.path.startswith("/api/remote-jobs")
    )


def _error(code: str, *, status_code: int | None = None, response_size: int | None = None) -> RemotiveJobsResponse:
    return RemotiveJobsResponse(
        status_code=status_code,
        reason=code,
        error_code=code,
        response_size=response_size,
    )
