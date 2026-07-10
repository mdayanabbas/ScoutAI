import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlparse

import httpx

from app.core.config import get_settings
from app.jobs.enrichment.providers.ashby_models import (
    AshbyPublicJobBoardResponse,
    AshbyPublicJobPosting,
)

logger = logging.getLogger(__name__)

ASHBY_API_HOST = "api.ashbyhq.com"
BOARD_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{1,120}$")


class AshbyPublicJobClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        max_response_bytes: int | None = None,
        user_agent: str | None = None,
        max_postings: int | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.ASHBY_JOB_PUBLIC_API_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.ASHBY_JOB_REQUEST_TIMEOUT_SECONDS
        self.max_retries = settings.ASHBY_JOB_MAX_RETRIES if max_retries is None else max_retries
        self.max_response_bytes = max_response_bytes or settings.ASHBY_JOB_MAX_RESPONSE_BYTES
        self.user_agent = user_agent or settings.ASHBY_JOB_USER_AGENT
        self.max_postings = max_postings or settings.ASHBY_JOB_MAX_POSTINGS_PER_BOARD
        self.transport = transport

    async def list_published_jobs(
        self,
        board_slug: str,
        *,
        include_compensation: bool = True,
    ) -> AshbyPublicJobBoardResponse:
        if not _valid_board_slug(board_slug):
            return AshbyPublicJobBoardResponse(board_slug=board_slug, reason="ashby_invalid_board_slug")
        url = self._board_url(board_slug)
        if url is None:
            return AshbyPublicJobBoardResponse(board_slug=board_slug, reason="ashby_invalid_response")

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            transport=self.transport,
        ) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.get(
                        url,
                        params={"includeCompensation": "true" if include_compensation else "false"},
                    )
                except httpx.TimeoutException:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return AshbyPublicJobBoardResponse(board_slug, reason="ashby_request_timeout")
                except httpx.HTTPError:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return AshbyPublicJobBoardResponse(board_slug, reason="ashby_provider_error")

                try:
                    result = await self._handle_response(board_slug, response)
                    if (
                        result.reason in {"ashby_rate_limited", "ashby_provider_error"}
                        and attempt < self.max_retries
                    ):
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return result
                finally:
                    await response.aclose()
        return AshbyPublicJobBoardResponse(board_slug, reason="ashby_provider_error")

    def _board_url(self, board_slug: str) -> str | None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or parsed.hostname != ASHBY_API_HOST:
            return None
        return f"{self.base_url}/{quote(board_slug, safe='-._~')}"

    async def _handle_response(
        self, board_slug: str, response: httpx.Response
    ) -> AshbyPublicJobBoardResponse:
        status_code = response.status_code
        content_length = response.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > self.max_response_bytes:
            return AshbyPublicJobBoardResponse(
                board_slug, status_code=status_code, response_size=int(content_length), reason="ashby_response_too_large"
            )
        body = response.content
        if len(body) > self.max_response_bytes:
            return AshbyPublicJobBoardResponse(
                board_slug, status_code=status_code, response_size=len(body), reason="ashby_response_too_large"
            )
        if status_code in {400, 404}:
            return AshbyPublicJobBoardResponse(
                board_slug, status_code=status_code, response_size=len(body), reason="ashby_board_not_found"
            )
        if status_code == 429:
            return AshbyPublicJobBoardResponse(
                board_slug, status_code=status_code, response_size=len(body), reason="ashby_rate_limited"
            )
        if status_code >= 500:
            return AshbyPublicJobBoardResponse(
                board_slug, status_code=status_code, response_size=len(body), reason="ashby_provider_error"
            )
        if status_code != 200:
            return AshbyPublicJobBoardResponse(
                board_slug, status_code=status_code, response_size=len(body), reason="ashby_provider_error"
            )
        content_type = response.headers.get("content-type", "").lower()
        if "json" not in content_type:
            return AshbyPublicJobBoardResponse(
                board_slug, status_code=status_code, response_size=len(body), reason="ashby_unexpected_content_type"
            )
        try:
            payload = response.json()
        except ValueError:
            return AshbyPublicJobBoardResponse(
                board_slug, status_code=status_code, response_size=len(body), reason="ashby_invalid_response"
            )
        jobs_payload = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs_payload, list):
            return AshbyPublicJobBoardResponse(
                board_slug, status_code=status_code, response_size=len(body), reason="ashby_invalid_response"
            )
        jobs = [_posting_from_payload(item, index) for index, item in enumerate(jobs_payload[: self.max_postings]) if isinstance(item, dict)]
        logger.info(
            "Ashby board fetched",
            extra={"board_slug": board_slug, "status_code": status_code, "posting_count": len(jobs)},
        )
        return AshbyPublicJobBoardResponse(
            board_slug=board_slug,
            jobs=jobs,
            status_code=status_code,
            fetched_at=datetime.now(timezone.utc),
            response_size=len(body),
        )


def _valid_board_slug(value: str | None) -> bool:
    if not value or not value.strip():
        return False
    if value != value.strip():
        return False
    if "://" in value or "/" in value or "\\" in value or "?" in value or "#" in value:
        return False
    if ".." in value or "%2f" in value.lower() or "%5c" in value.lower() or "@" in value:
        return False
    return bool(BOARD_SLUG_RE.fullmatch(value))


def _posting_from_payload(item: dict[str, Any], index: int) -> AshbyPublicJobPosting:
    return AshbyPublicJobPosting(
        id=_string(item.get("id")),
        title=_string(item.get("title")),
        location=_location_value(item.get("location")),
        secondary_locations=_secondary_locations(item.get("secondaryLocations")),
        department=_nested_name(item.get("department")),
        team=_nested_name(item.get("team")),
        is_listed=item.get("isListed") if isinstance(item.get("isListed"), bool) else None,
        is_remote=item.get("isRemote") if isinstance(item.get("isRemote"), bool) else None,
        workplace_type=_string(item.get("workplaceType")),
        employment_type=_string(item.get("employmentType")),
        description_html=_string(item.get("descriptionHtml") or item.get("description")),
        description_plain=_string(item.get("descriptionPlain")),
        published_at=_string(item.get("publishedAt")),
        job_url=_string(item.get("jobUrl")),
        apply_url=_string(item.get("applyUrl")),
        compensation=item.get("compensation"),
        raw_index=index,
    )


def _string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _nested_name(value: Any) -> str | None:
    if isinstance(value, dict):
        return _string(value.get("name") or value.get("title") or value.get("id"))
    return _string(value)


def _location_value(value: Any) -> str | None:
    if isinstance(value, dict):
        return _string(value.get("name") or value.get("displayName") or value.get("city"))
    return _string(value)


def _secondary_locations(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    locations: list[str] = []
    for item in value:
        text = _location_value(item)
        if text and text not in locations:
            locations.append(text)
    return locations[:20]

