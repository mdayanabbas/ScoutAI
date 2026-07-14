import httpx
import pytest

from app.discovery.sources.we_work_remotely.client import WeWorkRemotelyRSSClient
from app.discovery.sources.we_work_remotely.models import WWRFeedDefinition


FEED = WWRFeedDefinition(
    name="Remote Programming Jobs",
    feed_type="programming",
    feed_url="https://weworkremotely.com/categories/remote-programming-jobs.rss",
)


@pytest.mark.asyncio
async def test_client_rejects_non_official_feed_url_without_http_call():
    calls = []

    async def handler(request):
        calls.append(request)
        return httpx.Response(200, content=b"<rss />")

    client = WeWorkRemotelyRSSClient(transport=httpx.MockTransport(handler))
    result = await client.fetch_feed(
        WWRFeedDefinition("Bad", "bad", "https://evil.example/jobs.rss")
    )

    assert result.success is False
    assert result.reason == "wwr_invalid_feed_url"
    assert calls == []


@pytest.mark.asyncio
async def test_client_sends_conditional_headers_and_accepts_rss():
    seen = {}

    async def handler(request):
        seen["headers"] = request.headers
        return httpx.Response(
            200,
            headers={"content-type": "application/rss+xml", "etag": '"next"'},
            content=b"<?xml version='1.0'?><rss><channel /></rss>",
        )

    client = WeWorkRemotelyRSSClient(transport=httpx.MockTransport(handler))
    result = await client.fetch_feed(FEED, etag='"old"', last_modified="Tue, 14 Jul 2026 10:00:00 GMT")

    assert result.success is True
    assert result.etag == '"next"'
    assert seen["headers"]["if-none-match"] == '"old"'
    assert seen["headers"]["if-modified-since"] == "Tue, 14 Jul 2026 10:00:00 GMT"


@pytest.mark.asyncio
async def test_client_handles_not_modified_rate_limit_html_and_timeout():
    async def not_modified(_request):
        return httpx.Response(304, headers={"etag": '"same"'})

    result = await WeWorkRemotelyRSSClient(transport=httpx.MockTransport(not_modified)).fetch_feed(FEED)
    assert result.not_modified is True
    assert result.status_code == 304

    async def rate_limited(_request):
        return httpx.Response(429, content=b"slow down")

    result = await WeWorkRemotelyRSSClient(transport=httpx.MockTransport(rate_limited), max_retries=0).fetch_feed(FEED)
    assert result.success is False
    assert result.reason == "wwr_rate_limited"

    async def html(_request):
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"<!doctype html><html></html>")

    result = await WeWorkRemotelyRSSClient(transport=httpx.MockTransport(html)).fetch_feed(FEED)
    assert result.success is False
    assert result.reason == "wwr_html_response"

    async def timeout(_request):
        raise httpx.TimeoutException("timed out")

    result = await WeWorkRemotelyRSSClient(transport=httpx.MockTransport(timeout), max_retries=0).fetch_feed(FEED)
    assert result.success is False
    assert result.reason == "wwr_request_timeout"
