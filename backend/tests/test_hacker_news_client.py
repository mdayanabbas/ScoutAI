import httpx
import pytest

from app.discovery.sources.hacker_news.client import HackerNewsClient


@pytest.mark.asyncio
async def test_fetches_show_and_job_ids():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/showstories.json"):
            return httpx.Response(200, json=[1, 2])
        if request.url.path.endswith("/jobstories.json"):
            return httpx.Response(200, json=[3])
        return httpx.Response(404)

    client = HackerNewsClient(
        base_url="https://example.test/v0",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    assert await client.get_show_story_ids() == [1, 2]
    assert await client.get_job_story_ids() == [3]


@pytest.mark.asyncio
async def test_fetches_item_details_and_handles_null_item():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/item/1.json"):
            return httpx.Response(200, json={"id": 1, "type": "story", "title": "Show HN: Acme"})
        return httpx.Response(200, json=None)

    client = HackerNewsClient(
        base_url="https://example.test/v0",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    assert (await client.get_item(1)).title == "Show HN: Acme"
    assert await client.get_item(2) is None


@pytest.mark.asyncio
async def test_retries_transient_failure_but_not_permanent_404():
    attempts = {"transient": 0, "missing": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/item/1.json"):
            attempts["transient"] += 1
            if attempts["transient"] == 1:
                return httpx.Response(503, request=request)
            return httpx.Response(200, json={"id": 1})
        attempts["missing"] += 1
        return httpx.Response(404, request=request)

    client = HackerNewsClient(
        base_url="https://example.test/v0",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    assert await client.get_item(1) is not None
    assert await client.get_item(404) is None
    assert attempts["transient"] == 2
    assert attempts["missing"] == 1


@pytest.mark.asyncio
async def test_handles_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout", request=request)

    client = HackerNewsClient(
        base_url="https://example.test/v0",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    assert await client.get_item(1) is None
