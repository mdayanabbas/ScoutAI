import asyncio
import logging
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.jobs.job_source_detector import parse_yc_job_url

logger = logging.getLogger(__name__)

ALLOWED_YC_JOB_HOSTS = {"ycombinator.com", "www.ycombinator.com"}


@dataclass(frozen=True)
class YCombinatorJobFetchResult:
    success: bool
    url: str
    final_url: str | None = None
    html: str | None = None
    status_code: int | None = None
    reason: str | None = None
    redirect_count: int = 0
    content_length: int | None = None


class YCombinatorJobClient:
    def __init__(
        self,
        *,
        timeout_seconds: int | None = None,
        max_redirects: int | None = None,
        max_response_bytes: int | None = None,
        max_retries: int | None = None,
        user_agent: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.timeout_seconds = timeout_seconds or settings.YC_JOB_REQUEST_TIMEOUT_SECONDS
        self.max_redirects = settings.YC_JOB_MAX_REDIRECTS if max_redirects is None else max_redirects
        self.max_response_bytes = max_response_bytes or settings.YC_JOB_MAX_RESPONSE_BYTES
        self.max_retries = settings.YC_JOB_MAX_RETRIES if max_retries is None else max_retries
        self.user_agent = user_agent or settings.YC_JOB_USER_AGENT
        self.transport = transport

    async def fetch(self, url: str) -> YCombinatorJobFetchResult:
        parsed_yc = parse_yc_job_url(url)
        if parsed_yc is None:
            return YCombinatorJobFetchResult(False, url, reason="unsupported_job_source")
        current_url = parsed_yc.canonical_url
        redirects = 0
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers={"User-Agent": self.user_agent, "Accept": "text/html"},
            follow_redirects=False,
            transport=self.transport,
        ) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.get(current_url)
                except httpx.TimeoutException:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return YCombinatorJobFetchResult(
                        False, parsed_yc.canonical_url, reason="yc_job_page_timeout"
                    )
                except httpx.HTTPError:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    return YCombinatorJobFetchResult(
                        False, parsed_yc.canonical_url, reason="yc_job_page_fetch_failed"
                    )

                try:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        redirected_url = str(response.url.join(location or ""))
                        if not _allowed_yc_job_url(redirected_url):
                            logger.info(
                                "YC job page redirect rejected",
                                extra={"status_code": response.status_code},
                            )
                            return YCombinatorJobFetchResult(
                                False,
                                parsed_yc.canonical_url,
                                status_code=response.status_code,
                                reason="yc_job_page_redirect_rejected",
                                redirect_count=redirects,
                            )
                        redirects += 1
                        if redirects > self.max_redirects:
                            return YCombinatorJobFetchResult(
                                False,
                                parsed_yc.canonical_url,
                                status_code=response.status_code,
                                reason="yc_job_page_redirect_rejected",
                                redirect_count=redirects,
                            )
                        current_url = redirected_url
                        continue
                    if response.status_code == 404:
                        return YCombinatorJobFetchResult(
                            False,
                            parsed_yc.canonical_url,
                            status_code=404,
                            reason="yc_job_page_not_found",
                            redirect_count=redirects,
                        )
                    if response.status_code >= 500 and attempt < self.max_retries:
                        await asyncio.sleep(0.1 * (2**attempt))
                        continue
                    if response.status_code != 200:
                        return YCombinatorJobFetchResult(
                            False,
                            parsed_yc.canonical_url,
                            status_code=response.status_code,
                            reason="yc_job_page_fetch_failed",
                            redirect_count=redirects,
                        )
                    content_type = response.headers.get("content-type", "").lower()
                    if "html" not in content_type:
                        return YCombinatorJobFetchResult(
                            False,
                            parsed_yc.canonical_url,
                            status_code=response.status_code,
                            reason="yc_job_unexpected_content_type",
                            redirect_count=redirects,
                        )
                    content_length = response.headers.get("content-length")
                    if content_length and content_length.isdigit():
                        if int(content_length) > self.max_response_bytes:
                            return YCombinatorJobFetchResult(
                                False,
                                parsed_yc.canonical_url,
                                status_code=response.status_code,
                                reason="yc_job_page_too_large",
                                redirect_count=redirects,
                                content_length=int(content_length),
                            )
                    body = response.content
                    if len(body) > self.max_response_bytes:
                        return YCombinatorJobFetchResult(
                            False,
                            parsed_yc.canonical_url,
                            status_code=response.status_code,
                            reason="yc_job_page_too_large",
                            redirect_count=redirects,
                            content_length=len(body),
                        )
                    logger.info(
                        "YC page fetched",
                        extra={
                            "status_code": response.status_code,
                            "content_length": len(body),
                            "redirect_count": redirects,
                        },
                    )
                    return YCombinatorJobFetchResult(
                        True,
                        parsed_yc.canonical_url,
                        final_url=str(response.url),
                        html=response.text,
                        status_code=response.status_code,
                        redirect_count=redirects,
                        content_length=len(body),
                    )
                finally:
                    await response.aclose()
        return YCombinatorJobFetchResult(
            False, parsed_yc.canonical_url, reason="yc_job_page_fetch_failed"
        )


def _allowed_yc_job_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_YC_JOB_HOSTS:
        return False
    return parse_yc_job_url(value) is not None
