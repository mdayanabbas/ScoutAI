import json

import httpx
import pytest

from app.search.providers.tavily import TavilySearchProvider


@pytest.mark.asyncio
async def test_tavily_search_sends_bearer_token_and_basic_body():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("Authorization")
        seen["content_type"] = request.headers.get("Content-Type")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "results": [
                    {
                        "title": "Supabase",
                        "url": "https://supabase.com",
                        "content": "Supabase official website",
                        "score": 0.91,
                    }
                ]
            },
        )

    provider = TavilySearchProvider(
        api_key="secret",
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )
    provider.enabled = True

    response = await provider.search('"Supabase" official website company', count=5)

    assert response.success
    assert seen["authorization"] == "Bearer secret"
    assert seen["content_type"] == "application/json"
    assert seen["body"] == {
        "query": '"Supabase" official website company',
        "search_depth": "basic",
        "topic": "general",
        "max_results": 5,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
        "include_image_descriptions": False,
        "include_favicon": False,
        "auto_parameters": False,
    }


@pytest.mark.asyncio
async def test_tavily_search_maps_results():
    provider = TavilySearchProvider(
        api_key="secret",
        max_retries=0,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={
                    "results": [
                        {
                            "title": "Lago",
                            "url": "https://getlago.com",
                            "content": "Open-source billing platform",
                            "score": 0.87,
                        }
                    ]
                },
            )
        ),
    )
    provider.enabled = True

    response = await provider.search('"Lago" YC S21 official website')

    assert response.success
    assert response.results[0].title == "Lago"
    assert response.results[0].url == "https://getlago.com"
    assert response.results[0].description == "Open-source billing platform"
    assert response.results[0].rank == 1
    assert response.results[0].source == "tavily"
    assert response.results[0].provider_score == 0.87


@pytest.mark.asyncio
async def test_tavily_search_missing_key_is_not_configured():
    provider = TavilySearchProvider(api_key="", transport=httpx.MockTransport(lambda _request: httpx.Response(200)))
    provider.enabled = True

    response = await provider.search('"Supabase" official website company')

    assert not response.success
    assert response.reason == "web_search_not_configured"


@pytest.mark.asyncio
async def test_tavily_search_handles_unauthorized_without_secret_leak():
    provider = TavilySearchProvider(
        api_key="secret",
        max_retries=0,
        transport=httpx.MockTransport(lambda _request: httpx.Response(401)),
    )
    provider.enabled = True

    response = await provider.search('"Lago" official website company')

    assert not response.success
    assert response.reason == "web_search_not_configured"
    assert "secret" not in str(response)


@pytest.mark.asyncio
async def test_tavily_search_handles_rate_limit():
    provider = TavilySearchProvider(
        api_key="secret",
        max_retries=0,
        transport=httpx.MockTransport(lambda _request: httpx.Response(429)),
    )
    provider.enabled = True

    response = await provider.search('"Lago" official website company')

    assert response.reason == "web_search_rate_limited"


@pytest.mark.asyncio
async def test_tavily_search_handles_usage_limit_response():
    provider = TavilySearchProvider(
        api_key="secret",
        max_retries=0,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                400,
                headers={"content-type": "application/json"},
                json={"error": "Usage limit exceeded"},
            )
        ),
    )
    provider.enabled = True

    response = await provider.search('"Lago" official website company')

    assert response.reason == "web_search_rate_limited"


@pytest.mark.asyncio
async def test_tavily_search_handles_timeout():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    provider = TavilySearchProvider(
        api_key="secret",
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )
    provider.enabled = True

    response = await provider.search('"Lago" official website company')

    assert response.reason == "web_search_timeout"


@pytest.mark.asyncio
async def test_tavily_search_handles_malformed_json():
    provider = TavilySearchProvider(
        api_key="secret",
        max_retries=0,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                headers={"content-type": "application/json"},
                content=b"{not-json",
            )
        ),
    )
    provider.enabled = True

    response = await provider.search('"Lago" official website company')

    assert response.reason == "web_search_invalid_response"


@pytest.mark.asyncio
async def test_tavily_search_empty_results_are_successful():
    provider = TavilySearchProvider(
        api_key="secret",
        max_retries=0,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={"results": []},
            )
        ),
    )
    provider.enabled = True

    response = await provider.search('"Lago" official website company')

    assert response.success
    assert response.results == ()


@pytest.mark.asyncio
async def test_tavily_search_missing_results_is_invalid_response():
    provider = TavilySearchProvider(
        api_key="secret",
        max_retries=0,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={"answer": None},
            )
        ),
    )
    provider.enabled = True

    response = await provider.search('"Lago" official website company')

    assert response.reason == "web_search_invalid_response"
