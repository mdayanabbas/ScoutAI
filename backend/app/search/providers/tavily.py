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


class TavilySearchProvider(WebSearchProvider):
    name = "tavily"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        search_depth: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        max_response_bytes: int | None = None,
        user_agent: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.enabled = settings.WEB_SEARCH_ENABLED
        self.api_key = api_key if api_key is not None else settings.TAVILY_API_KEY
        self.base_url = base_url or settings.TAVILY_SEARCH_BASE_URL
        self.search_depth = search_depth or settings.TAVILY_SEARCH_DEPTH
        self.timeout_seconds = (
            timeout_seconds or settings.WEB_SEARCH_REQUEST_TIMEOUT_SECONDS
        )
        self.max_retries = (
            settings.WEB_SEARCH_MAX_RETRIES if max_retries is None else max_retries
        )
        self.max_response_bytes = (
            max_response_bytes or settings.WEB_SEARCH_MAX_RESPONSE_BYTES
        )
        self.user_agent = user_agent or settings.TAVILY_USER_AGENT
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
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "query": query,
            "search_depth": self.search_depth,
            "topic": "general",
            "max_results": bounded_count,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "include_image_descriptions": False,
            "include_favicon": False,
            "auto_parameters": False,
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
                        client.build_request("POST", self.base_url, json=payload),
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
                    body, read_reason = await self._read_body(response)
                    if read_reason:
                        return WebSearchResponse(
                            self.name,
                            query,
                            False,
                            status_code=status_code,
                            reason=read_reason,
                        )
                    parsed = self._parse_json(body)
                    if status_code == 429 or _usage_limited(parsed):
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
                    if status_code == 400:
                        return WebSearchResponse(
                            self.name,
                            query,
                            False,
                            status_code=status_code,
                            reason="web_search_invalid_response",
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
                    if parsed is None:
                        return WebSearchResponse(
                            self.name,
                            query,
                            False,
                            status_code=status_code,
                            reason="web_search_invalid_response",
                        )
                    results = parsed.get("results")
                    if not isinstance(results, list):
                        return WebSearchResponse(
                            self.name,
                            query,
                            False,
                            status_code=status_code,
                            reason="web_search_invalid_response",
                        )
                    return WebSearchResponse(
                        self.name,
                        query,
                        True,
                        results=self._parse_results(results),
                        status_code=status_code,
                    )
                finally:
                    await response.aclose()
        return WebSearchResponse(
            self.name, query, False, reason="web_search_provider_error"
        )

    async def _read_body(
        self, response: httpx.Response
    ) -> tuple[bytes, str | None]:
        content_length = response.headers.get("content-length")
        if (
            content_length
            and content_length.isdigit()
            and int(content_length) > self.max_response_bytes
        ):
            return b"", "web_search_invalid_response"
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body.extend(chunk)
            if len(body) > self.max_response_bytes:
                return b"", "web_search_invalid_response"
        return bytes(body), None

    def _parse_json(self, body: bytes) -> dict[str, Any] | None:
        try:
            payload = json.loads(body or b"{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _parse_results(
        self, raw_results: list[Any]
    ) -> tuple[WebSearchResult, ...]:
        parsed: list[WebSearchResult] = []
        for index, item in enumerate(raw_results[:20], start=1):
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            title = item.get("title")
            if not isinstance(url, str) or not isinstance(title, str):
                continue
            content = item.get("content")
            score = item.get("score")
            parsed.append(
                WebSearchResult(
                    title=title[:300],
                    url=url,
                    description=content[:500] if isinstance(content, str) else None,
                    rank=index,
                    source=self.name,
                    provider_score=(
                        float(score)
                        if isinstance(score, (int, float)) and not isinstance(score, bool)
                        else None
                    ),
                )
            )
        return tuple(parsed)


def _usage_limited(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    text = " ".join(
        str(value)
        for key, value in payload.items()
        if key.lower() in {"error", "detail", "message"}
    ).lower()
    return "usage" in text and ("limit" in text or "quota" in text or "credit" in text)
