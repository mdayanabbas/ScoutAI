import asyncio
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.discovery.sources.we_work_remotely.constants import WWR_ALLOWED_HOST
from app.discovery.sources.we_work_remotely.models import WWRFeedDefinition, WWRFeedResponse

XML_CONTENT_TYPES = ("application/rss+xml", "application/xml", "text/xml", "application/atom+xml", "text/plain")


class WeWorkRemotelyRSSClient:
    def __init__(
        self,
        *,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        max_response_bytes: int | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.timeout_seconds = timeout_seconds or settings.WWR_REQUEST_TIMEOUT_SECONDS
        self.max_retries = settings.WWR_MAX_RETRIES if max_retries is None else max_retries
        self.max_response_bytes = max_response_bytes or settings.WWR_MAX_RESPONSE_BYTES
        self.transport = transport

    async def fetch_feed(
        self,
        feed: WWRFeedDefinition,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> WWRFeedResponse:
        if not _allowed_feed_url(feed.feed_url):
            return WWRFeedResponse(False, feed, reason="wwr_invalid_feed_url")
        headers = {"Accept": "application/rss+xml, application/xml, text/xml", "User-Agent": "ScoutAI/0.1 wwr-rss-discovery"}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers=headers,
            follow_redirects=False,
            transport=self.transport,
        ) as client:
            url = feed.feed_url
            redirects = 0
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.get(url)
                except httpx.TimeoutException:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return WWRFeedResponse(False, feed, reason="wwr_request_timeout")
                except httpx.HTTPError:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return WWRFeedResponse(False, feed, reason="wwr_provider_error")
                try:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        redirected = str(response.url.join(location or ""))
                        if not _allowed_feed_url(redirected):
                            return WWRFeedResponse(False, feed, status_code=response.status_code, reason="wwr_redirect_rejected")
                        redirects += 1
                        if redirects > 3:
                            return WWRFeedResponse(False, feed, status_code=response.status_code, reason="wwr_redirect_rejected")
                        url = redirected
                        continue
                    result = self._handle_response(feed, response)
                    if result.reason == "wwr_provider_error" and attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return result
                finally:
                    await response.aclose()
        return WWRFeedResponse(False, feed, reason="wwr_provider_error")

    def _handle_response(self, feed: WWRFeedDefinition, response: httpx.Response) -> WWRFeedResponse:
        status_code = response.status_code
        if status_code == 304:
            return WWRFeedResponse(True, feed, status_code=status_code, reason="not_modified", not_modified=True, etag=response.headers.get("etag"), last_modified=response.headers.get("last-modified"))
        if status_code == 429:
            return WWRFeedResponse(False, feed, status_code=status_code, reason="wwr_rate_limited")
        if status_code >= 500:
            return WWRFeedResponse(False, feed, status_code=status_code, reason="wwr_provider_error")
        if status_code != 200:
            return WWRFeedResponse(False, feed, status_code=status_code, reason="wwr_provider_error")
        content_length = response.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > self.max_response_bytes:
            return WWRFeedResponse(False, feed, status_code=status_code, reason="wwr_response_too_large", response_size=int(content_length))
        body = response.content
        if len(body) > self.max_response_bytes:
            return WWRFeedResponse(False, feed, status_code=status_code, reason="wwr_response_too_large", response_size=len(body))
        stripped = body.lstrip()[:100].lower()
        if stripped.startswith(b"<!doctype html") or stripped.startswith(b"<html"):
            return WWRFeedResponse(False, feed, status_code=status_code, reason="wwr_html_response", response_size=len(body))
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if content_type not in XML_CONTENT_TYPES:
            return WWRFeedResponse(False, feed, status_code=status_code, reason="wwr_unexpected_content_type", response_size=len(body))
        return WWRFeedResponse(True, feed, body=body, status_code=status_code, etag=response.headers.get("etag"), last_modified=response.headers.get("last-modified"), response_size=len(body))


def _allowed_feed_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme == "https" and parsed.hostname == WWR_ALLOWED_HOST and parsed.path.endswith(".rss")
