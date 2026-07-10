import httpx
import pytest

from app.jobs.enrichment.providers.ashby_public_job_client import AshbyPublicJobClient


@pytest.mark.asyncio
async def test_client_uses_official_endpoint_and_include_compensation():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.ashbyhq.com"
        assert request.url.path == "/posting-api/job-board/lago"
        assert request.url.params["includeCompensation"] == "true"
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"jobs": [{"id": "abc", "title": "Backend Engineer", "isListed": True}]},
        )

    result = await AshbyPublicJobClient(transport=httpx.MockTransport(handler)).list_published_jobs("lago")

    assert result.reason is None
    assert result.jobs[0].id == "abc"
    assert result.jobs[0].title == "Backend Engineer"


@pytest.mark.asyncio
async def test_client_rejects_unsafe_board_slugs_without_network():
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={"jobs": []})

    client = AshbyPublicJobClient(transport=httpx.MockTransport(handler))

    assert (await client.list_published_jobs("../lago")).reason == "ashby_invalid_board_slug"
    assert (await client.list_published_jobs("https://jobs.ashbyhq.com/lago")).reason == "ashby_invalid_board_slug"
    assert called is False


@pytest.mark.asyncio
async def test_client_handles_provider_errors_timeout_json_and_size():
    async def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow", request=request)

    timeout = AshbyPublicJobClient(max_retries=0, transport=httpx.MockTransport(timeout_handler))
    missing = AshbyPublicJobClient(transport=httpx.MockTransport(lambda request: httpx.Response(404, json={})))
    limited = AshbyPublicJobClient(transport=httpx.MockTransport(lambda request: httpx.Response(429, json={})))
    malformed = AshbyPublicJobClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, headers={"content-type": "application/json"}, text="{"))
    )
    wrong_type = AshbyPublicJobClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text="<html>"))
    )
    oversized = AshbyPublicJobClient(
        max_response_bytes=4,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, headers={"content-type": "application/json"}, text='{"jobs": []}')),
    )

    assert (await timeout.list_published_jobs("lago")).reason == "ashby_request_timeout"
    assert (await missing.list_published_jobs("lago")).reason == "ashby_board_not_found"
    assert (await limited.list_published_jobs("lago")).reason == "ashby_rate_limited"
    assert (await malformed.list_published_jobs("lago")).reason == "ashby_invalid_response"
    assert (await wrong_type.list_published_jobs("lago")).reason == "ashby_unexpected_content_type"
    assert (await oversized.list_published_jobs("lago")).reason == "ashby_response_too_large"


@pytest.mark.asyncio
async def test_client_retries_bounded_5xx():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, headers={"content-type": "application/json"}, json={})

    result = await AshbyPublicJobClient(max_retries=1, transport=httpx.MockTransport(handler)).list_published_jobs("lago")

    assert result.reason == "ashby_provider_error"
    assert calls == 2

