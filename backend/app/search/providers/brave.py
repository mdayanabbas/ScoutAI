import asyncio
import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.search.providers.base import (
    WebSearchProvider,
    WebSearchResponse,
    WebSearchResult,
)

logger = logging.getLogger(__name__)


class BraveSearchProvider(WebSearchProvider):
    name = "brave"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        max_response_bytes: int | None = None,
        user_agent: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.enabled = settings.WEB_SEARCH_ENABLED
        self.api_key = api_key if api_key is not None else settings.BRAVE_SEARCH_API_KEY
        self.base_url = base_url or settings.BRAVE_SEARCH_BASE_URL
        self.timeout_seconds = (
            timeout_seconds or settings.WEB_SEARCH_REQUEST_TIMEOUT_SECONDS
        )
        self.max_retries = (
            settings.WEB_SEARCH_MAX_RETRIES if max_retries is None else max_retries
        )
        self.max_response_bytes = (
            max_response_bytes or settings.WEB_SEARCH_MAX_RESPONSE_BYTES
        )
        self.user_agent = user_agent or settings.BRAVE_SEARCH_USER_AGENT
        self.transport = transport

    async def search(
        self,
        query: str,
        *,
        count: int = 10,
    ) -> WebSearchResponse:
        if not self.enabled:
            return WebSearchResponse(self.name, query, False, reason="web_search_disabled")
        if not self.api_key:
            return WebSearchResponse(
                self.name, query, False, reason="web_search_not_configured"
            )
        bounded_count = max(1, min(int(count), 20))
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": self.user_agent,
            "X-Subscription-Token": self.api_key,
        }
        params = {
            "q": query,
            "count": bounded_count,
            "search_lang": "en",
            "safesearch": "strict",
            "result_filter": "web",
            "text_decorations": "false",
            "spellcheck": "false",
        }
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers=headers,
            follow_redirects=False,
            transport=self.transport,
        ) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    logger.info("Web search query executed", extra={"provider": self.name})
                    response = await client.send(
                        client.build_request("GET", self.base_url, params=params),
                        stream=True,
                    )
                except httpx.TimeoutException:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return WebSearchResponse(
                        self.name, query, False, reason="web_search_timeout"
                    )
                except httpx.HTTPError:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return WebSearchResponse(
                        self.name, query, False, reason="web_search_provider_error"
                    )

                try:
                    status_code = response.status_code
                    if status_code == 429:
                        if attempt < self.max_retries:
                            await asyncio.sleep(0.2 * (2**attempt))
                            continue
                        return WebSearchResponse(
                            self.name,
                            query,
                            False,
                            status_code=status_code,
                            reason="web_search_rate_limited",
                        )
                    if status_code >= 500:
                        if attempt < self.max_retries:
                            await asyncio.sleep(0.2 * (2**attempt))
                            continue
                        return WebSearchResponse(
                            self.name,
                            query,
                            False,
                            status_code=status_code,
                            reason="web_search_provider_error",
                        )
                    if status_code in {401, 403}:
                        return WebSearchResponse(
                            self.name,
                            query,
                            False,
                            status_code=status_code,
                            reason="web_search_not_configured",
                        )
                    if 400 <= status_code < 500:
                        return WebSearchResponse(
                            self.name,
                            query,
                            False,
                            status_code=status_code,
                            reason="web_search_provider_error",
                        )
                    if status_code != 200:
                        return WebSearchResponse(
                            self.name,
                            query,
                            False,
                            status_code=status_code,
                            reason="web_search_provider_error",
                        )
                    content_type = response.headers.get("content-type", "").lower()
                    if "application/json" not in content_type:
                        return WebSearchResponse(
                            self.name,
                            query,
                            False,
                            status_code=status_code,
                            reason="web_search_invalid_response",
                        )
                    content_length = response.headers.get("content-length")
                    if (
                        content_length
                        and content_length.isdigit()
                        and int(content_length) > self.max_response_bytes
                    ):
                        return WebSearchResponse(
                            self.name,
                            query,
                            False,
                            status_code=status_code,
                            reason="web_search_invalid_response",
                        )
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self.max_response_bytes:
                            return WebSearchResponse(
                                self.name,
                                query,
                                False,
                                status_code=status_code,
                                reason="web_search_invalid_response",
                            )
                    try:
                        payload = json.loads(body)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        return WebSearchResponse(
                            self.name,
                            query,
                            False,
                            status_code=status_code,
                            reason="web_search_invalid_response",
                        )
                finally:
                    await response.aclose()
                return WebSearchResponse(
                    self.name,
                    query,
                    True,
                    results=self._parse_results(payload),
                    status_code=status_code,
                )
        return WebSearchResponse(
            self.name, query, False, reason="web_search_provider_error"
        )

    def _parse_results(self, payload: dict[str, Any]) -> tuple[WebSearchResult, ...]:
        raw_results = ((payload.get("web") or {}).get("results") or [])[:20]
        parsed: list[WebSearchResult] = []
        for index, item in enumerate(raw_results, start=1):
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            title = item.get("title")
            if not isinstance(url, str) or not isinstance(title, str):
                continue
            snippets = item.get("extra_snippets") or ()
            parsed.append(
                WebSearchResult(
                    title=title[:300],
                    url=url,
                    description=(
                        item.get("description")[:500]
                        if isinstance(item.get("description"), str)
                        else None
                    ),
                    rank=index,
                    source=item.get("profile", {}).get("name")
                    if isinstance(item.get("profile"), dict)
                    else None,
                    language=item.get("language")
                    if isinstance(item.get("language"), str)
                    else None,
                    age=item.get("age") if isinstance(item.get("age"), str) else None,
                    extra_snippets=tuple(
                        snippet[:300] for snippet in snippets if isinstance(snippet, str)
                    )[:3],
                )
            )
        return tuple(parsed)
