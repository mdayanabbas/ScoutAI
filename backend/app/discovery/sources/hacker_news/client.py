import asyncio
import logging
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.discovery.sources.hacker_news.schemas import HackerNewsItem

logger = logging.getLogger(__name__)

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class HackerNewsClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: int | None = None,
        max_concurrency: int | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.HACKER_NEWS_API_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.HACKER_NEWS_REQUEST_TIMEOUT_SECONDS
        self.max_concurrency = max_concurrency or settings.HACKER_NEWS_MAX_CONCURRENCY
        self._client = http_client
        self._owns_client = http_client is None

    async def __aenter__(self) -> "HackerNewsClient":
        self._ensure_client()
        return self

    async def __aexit__(self, *_exc_info) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def get_show_story_ids(self) -> list[int]:
        return await self._get_ids("/showstories.json")

    async def get_job_story_ids(self) -> list[int]:
        return await self._get_ids("/jobstories.json")

    async def get_item(self, item_id: int) -> HackerNewsItem | None:
        payload = await self._request_json(f"/item/{item_id}.json")
        if payload is None:
            return None
        if not isinstance(payload, dict):
            logger.info("Skipping malformed Hacker News item", extra={"item_id": item_id})
            return None
        try:
            return HackerNewsItem.model_validate(payload)
        except ValidationError:
            logger.info("Skipping invalid Hacker News item", extra={"item_id": item_id})
            return None

    async def get_items(self, item_ids: list[int]) -> list[HackerNewsItem]:
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def fetch_one(item_id: int) -> HackerNewsItem | None:
            async with semaphore:
                return await self.get_item(item_id)

        tasks = [asyncio.create_task(fetch_one(item_id)) for item_id in item_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        items: list[HackerNewsItem] = []
        for item_id, result in zip(item_ids, results):
            if isinstance(result, Exception):
                logger.info(
                    "Hacker News item fetch failed",
                    extra={"item_id": item_id, "error": result.__class__.__name__},
                )
                continue
            if result is not None:
                items.append(result)
        return items

    async def _get_ids(self, path: str) -> list[int]:
        payload = await self._request_json(path)
        if not isinstance(payload, list):
            return []
        return [int(item_id) for item_id in payload if isinstance(item_id, int)]

    async def _request_json(self, path: str) -> Any | None:
        client = self._ensure_client()
        url = f"{self.base_url}{path}"
        for attempt in range(1, 4):
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.json()
                if response.status_code not in TRANSIENT_STATUS_CODES:
                    return None
                raise httpx.HTTPStatusError(
                    "Transient Hacker News API response",
                    request=response.request,
                    response=response,
                )
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
                if attempt == 3:
                    return None
                await asyncio.sleep(0.2 * (2 ** (attempt - 1)))
            except ValueError:
                return None
        return None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout_seconds,
                headers={"User-Agent": "ScoutAI/0.1 startup-discovery"},
            )
        return self._client
