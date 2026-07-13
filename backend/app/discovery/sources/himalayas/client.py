import asyncio
import logging
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.discovery.sources.himalayas.models import (
    HimalayasSearchResponse,
    parse_himalayas_jobs_response,
    schema_diagnostics_for_payload,
)

logger = logging.getLogger(__name__)

HIMALAYAS_API_HOST = "himalayas.app"
MAX_RESPONSE_BYTES = 4_000_000


class HimalayasRemoteJobsClient:
    def __init__(
        self,
        *,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = settings.HIMALAYAS_API_BASE_URL.rstrip("/")
        self.search_path = settings.HIMALAYAS_SEARCH_PATH
        self.timeout_seconds = timeout_seconds or settings.HIMALAYAS_REQUEST_TIMEOUT_SECONDS
        self.max_retries = settings.HIMALAYAS_MAX_RETRIES if max_retries is None else max_retries
        self.transport = transport

    async def search_jobs(
        self,
        *,
        query: str,
        country: str | None = None,
        worldwide: bool | None = None,
        exclude_worldwide: bool | None = None,
        seniority: list[str] | None = None,
        employment_types: list[str] | None = None,
        sort: str = "recent",
        page: int = 1,
    ) -> HimalayasSearchResponse:
        url = self._search_url()
        if url is None:
            return _error("himalayas_invalid_provider_host", "Invalid Himalayas provider host")
        params = _query_params(
            query=query,
            country=country,
            worldwide=worldwide,
            exclude_worldwide=exclude_worldwide,
            seniority=seniority,
            employment_types=employment_types,
            sort=sort,
            page=page,
        )
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers={"Accept": "application/json", "User-Agent": "ScoutAI/0.1 himalayas-discovery"},
            transport=self.transport,
        ) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.get(url, params=params)
                except httpx.TimeoutException:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return _error("himalayas_request_timeout", "Himalayas request timed out")
                except httpx.HTTPError:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return _error("himalayas_provider_error", "Himalayas provider request failed")
                try:
                    result = self._handle_response(response)
                    if result.reason in {"himalayas_provider_error"} and attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return result
                finally:
                    await response.aclose()
        return _error("himalayas_provider_error", "Himalayas provider request failed")

    def _search_url(self) -> str | None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or parsed.hostname != HIMALAYAS_API_HOST:
            return None
        path = self.search_path if self.search_path.startswith("/") else f"/{self.search_path}"
        return f"{self.base_url}{path}"

    def _handle_response(self, response: httpx.Response) -> HimalayasSearchResponse:
        status_code = response.status_code
        content_length = response.headers.get("content-length")
        content_type = response.headers.get("content-type")
        provider_request_id = response.headers.get("x-request-id") or response.headers.get("cf-ray")
        if content_length and content_length.isdigit() and int(content_length) > MAX_RESPONSE_BYTES:
            return _error("himalayas_response_too_large", "Himalayas response too large", status_code=status_code, response_size=int(content_length))
        body = response.content
        if len(body) > MAX_RESPONSE_BYTES:
            return _error("himalayas_response_too_large", "Himalayas response too large", status_code=status_code, response_size=len(body))
        if status_code == 400:
            return _error("himalayas_bad_request", "Himalayas rejected request parameters", status_code=status_code, response_size=len(body))
        if status_code == 429:
            return _error("himalayas_rate_limited", "Himalayas rate limited the request", status_code=status_code, response_size=len(body))
        if status_code >= 500:
            return _error("himalayas_provider_error", "Himalayas provider error", status_code=status_code, response_size=len(body))
        if status_code != 200:
            return _error("himalayas_provider_error", "Himalayas provider error", status_code=status_code, response_size=len(body))
        try:
            payload = response.json()
        except ValueError:
            return _error(
                "himalayas_invalid_json",
                "Himalayas returned invalid JSON",
                status_code=status_code,
                response_size=len(body),
                schema_diagnostics=schema_diagnostics_for_payload(
                    "invalid_json",
                    status_code=status_code,
                    response_size=len(body),
                    content_type=content_type,
                    provider_request_id=provider_request_id,
                    validation_paths=[],
                ),
            )
        parsed = parse_himalayas_jobs_response(
            payload,
            status_code=status_code,
            response_size=len(body),
            content_type=content_type,
            provider_request_id=provider_request_id,
        )
        if parsed.reason:
            logger.info("Himalayas schema validation failed", extra=parsed.schema_diagnostics or {})
            return parsed
        logger.info(
            "Himalayas query completed",
            extra={
                "status_code": status_code,
                "jobs": len(parsed.jobs),
                "malformed_records": parsed.malformed_records,
            },
        )
        return parsed


def _query_params(
    *,
    query: str,
    country: str | None,
    worldwide: bool | None,
    exclude_worldwide: bool | None,
    seniority: list[str] | None,
    employment_types: list[str] | None,
    sort: str,
    page: int,
) -> list[tuple[str, str]]:
    params = [("q", query.strip()), ("sort", sort), ("page", str(max(1, page)))]
    if country:
        params.append(("country", country.upper()))
    if worldwide is not None:
        params.append(("worldwide", "true" if worldwide else "false"))
    if exclude_worldwide is not None:
        params.append(("exclude_worldwide", "true" if exclude_worldwide else "false"))
    if seniority:
        params.append(("seniority", ",".join(str(value) for value in seniority)))
    if employment_types:
        params.append(("employment_type", ",".join(str(value) for value in employment_types)))
    return params


def _error(
    code: str,
    summary: str,
    *,
    status_code: int | None = None,
    response_size: int | None = None,
    schema_diagnostics: dict | None = None,
) -> HimalayasSearchResponse:
    return HimalayasSearchResponse(
        status_code=status_code,
        response_size=response_size,
        reason=code,
        error_code=code,
        error_summary=summary,
        schema_diagnostics=schema_diagnostics,
    )
