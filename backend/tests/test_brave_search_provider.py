import httpx
import pytest

from app.search.providers.brave import BraveSearchProvider


@pytest.mark.asyncio
async def test_brave_search_sends_token_and_expected_params():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["token"] = request.headers.get("X-Subscription-Token")
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"web": {"results": [{"title": "Supabase", "url": "https://supabase.com"}]}},
        )

    provider = BraveSearchProvider(
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    provider.enabled = True

    response = await provider.search('"Supabase" official website company', count=25)

    assert response.success
    assert seen["token"] == "secret"
    assert seen["params"]["q"] == '"Supabase" official website company'
    assert seen["params"]["count"] == "20"
    assert seen["params"]["search_lang"] == "en"
    assert seen["params"]["safesearch"] == "strict"


@pytest.mark.asyncio
async def test_brave_search_handles_unauthorized_without_secret_leak():
    provider = BraveSearchProvider(
        api_key="secret",
        transport=httpx.MockTransport(lambda _request: httpx.Response(401)),
    )
    provider.enabled = True

    response = await provider.search('"Lago" official website company')

    assert not response.success
    assert response.reason == "web_search_not_configured"
    assert "secret" not in str(response)


@pytest.mark.asyncio
async def test_brave_search_handles_rate_limit():
    provider = BraveSearchProvider(
        api_key="secret",
        max_retries=0,
        transport=httpx.MockTransport(lambda _request: httpx.Response(429)),
    )
    provider.enabled = True

    response = await provider.search('"Lago" official website company')

    assert response.reason == "web_search_rate_limited"


@pytest.mark.asyncio
async def test_brave_search_handles_timeout():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    provider = BraveSearchProvider(
        api_key="secret",
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )
    provider.enabled = True

    response = await provider.search('"Lago" official website company')

    assert response.reason == "web_search_timeout"


@pytest.mark.asyncio
async def test_brave_search_handles_malformed_json():
    provider = BraveSearchProvider(
        api_key="secret",
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
