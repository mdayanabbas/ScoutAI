import httpx
import pytest

from app.jobs.enrichment.providers.ycombinator_client import YCombinatorJobClient

YC_URL = "https://www.ycombinator.com/companies/hazel-2/jobs/3epPWgu-full-stack-engineer-ts-sci"


@pytest.mark.asyncio
async def test_client_accepts_canonical_yc_job_url_and_valid_html():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "www.ycombinator.com"
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<h1>Full Stack Engineer</h1>")

    result = await YCombinatorJobClient(transport=httpx.MockTransport(handler)).fetch(YC_URL)

    assert result.success is True
    assert result.status_code == 200
    assert result.html == "<h1>Full Stack Engineer</h1>"


@pytest.mark.asyncio
async def test_client_rejects_general_yc_company_and_account_urls():
    client = YCombinatorJobClient(transport=httpx.MockTransport(lambda request: httpx.Response(200)))

    assert (await client.fetch("https://www.ycombinator.com/companies/hazel-2")).reason == "unsupported_job_source"
    assert (await client.fetch("https://account.ycombinator.com/login")).reason == "unsupported_job_source"


@pytest.mark.asyncio
async def test_client_rejects_external_redirect():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://workatastartup.com/login"})

    result = await YCombinatorJobClient(transport=httpx.MockTransport(handler)).fetch(YC_URL)

    assert result.success is False
    assert result.reason == "yc_job_page_redirect_rejected"


@pytest.mark.asyncio
async def test_client_rejects_wrong_content_type_oversized_timeout_and_404():
    async def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow", request=request)

    wrong_type = YCombinatorJobClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, headers={"content-type": "application/json"}, json={}))
    )
    oversized = YCombinatorJobClient(
        max_response_bytes=4,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text="too large")),
    )
    timeout = YCombinatorJobClient(max_retries=0, transport=httpx.MockTransport(timeout_handler))
    not_found = YCombinatorJobClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(404, headers={"content-type": "text/html"}))
    )

    assert (await wrong_type.fetch(YC_URL)).reason == "yc_job_unexpected_content_type"
    assert (await oversized.fetch(YC_URL)).reason == "yc_job_page_too_large"
    assert (await timeout.fetch(YC_URL)).reason == "yc_job_page_timeout"
    assert (await not_found.fetch(YC_URL)).reason == "yc_job_page_not_found"


@pytest.mark.asyncio
async def test_client_retries_bounded_failures():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, headers={"content-type": "text/html"})

    result = await YCombinatorJobClient(max_retries=1, transport=httpx.MockTransport(handler)).fetch(YC_URL)

    assert result.reason == "yc_job_page_fetch_failed"
    assert calls == 2
