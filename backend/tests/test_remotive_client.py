import httpx
import pytest

from app.discovery.sources.remotive.client import RemotiveRemoteJobsClient


def _payload(*jobs):
    return {"0-legal-notice": "legal", "job-count": len(jobs), "jobs": list(jobs)}


@pytest.mark.asyncio
async def test_client_uses_official_endpoint_and_supported_params(monkeypatch):
    seen = {}

    async def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(
            200,
            json=_payload({"id": 1, "title": "AI Engineer", "company_name": "Remote AI Co"}),
        )

    client = RemotiveRemoteJobsClient(transport=httpx.MockTransport(handler))
    result = await client.list_jobs(category="software-dev", search="AI Engineer", limit=25)

    assert result.reason is None
    assert str(seen["url"]).startswith("https://remotive.com/api/remote-jobs?")
    assert "category=software-dev" in seen["url"]
    assert "search=AI+Engineer" in seen["url"]
    assert "limit=25" in seen["url"]


@pytest.mark.asyncio
async def test_client_rejects_arbitrary_host_without_http_call(monkeypatch):
    monkeypatch.setattr("app.discovery.sources.remotive.client.get_settings", lambda: type("S", (), {
        "REMOTIVE_API_BASE_URL": "https://evil.example",
        "REMOTIVE_JOBS_PATH": "/api/remote-jobs",
        "REMOTIVE_REQUEST_TIMEOUT_SECONDS": 20,
        "REMOTIVE_MAX_RETRIES": 1,
        "REMOTIVE_MAX_RESPONSE_BYTES": 10_000_000,
    })())
    calls = []

    async def handler(request):
        calls.append(request)
        return httpx.Response(200, json=_payload())

    result = await RemotiveRemoteJobsClient(transport=httpx.MockTransport(handler)).list_jobs()

    assert result.reason == "remotive_invalid_provider_host"
    assert calls == []


@pytest.mark.asyncio
async def test_client_handles_timeout_rate_limit_5xx_size_html_invalid_json_and_malformed_sibling():
    async def timeout(_request):
        raise httpx.TimeoutException("timeout")

    assert (await RemotiveRemoteJobsClient(transport=httpx.MockTransport(timeout), max_retries=0).list_jobs()).reason == "remotive_request_timeout"

    async def rate_limited(_request):
        return httpx.Response(429, content=b"slow down")

    assert (await RemotiveRemoteJobsClient(transport=httpx.MockTransport(rate_limited), max_retries=0).list_jobs()).reason == "remotive_rate_limited"

    calls = {"count": 0}

    async def flaky(_request):
        calls["count"] += 1
        return httpx.Response(500, content=b"oops")

    assert (await RemotiveRemoteJobsClient(transport=httpx.MockTransport(flaky), max_retries=1).list_jobs()).reason == "remotive_provider_error"
    assert calls["count"] == 2

    async def too_large(_request):
        return httpx.Response(200, headers={"content-length": "99"}, content=b"{}")

    assert (await RemotiveRemoteJobsClient(transport=httpx.MockTransport(too_large), max_response_bytes=10).list_jobs()).reason == "remotive_response_too_large"

    async def html(_request):
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html></html>")

    assert (await RemotiveRemoteJobsClient(transport=httpx.MockTransport(html)).list_jobs()).reason == "remotive_html_response"

    async def invalid_json(_request):
        return httpx.Response(200, content=b"not json")

    assert (await RemotiveRemoteJobsClient(transport=httpx.MockTransport(invalid_json)).list_jobs()).reason == "remotive_invalid_json"

    async def mixed(_request):
        return httpx.Response(200, json=_payload({"id": 1, "title": "AI Engineer", "company_name": "Remote AI Co"}, {"id": 2, "title": ""}))

    result = await RemotiveRemoteJobsClient(transport=httpx.MockTransport(mixed)).list_jobs()
    assert len(result.jobs) == 1
    assert len(result.malformed_jobs) == 1
