import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.discovery.sources.hacker_news.adapter import HackerNewsDiscoveryAdapter
from app.schemas.discovery import RawStartupCandidate


@pytest.fixture
async def hacker_news_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_hacker_news_discovery_api_returns_201(
    hacker_news_api_client: AsyncClient,
    monkeypatch,
):
    async def discover(self, request):
        self.fetched_item_count = 1
        return [
            RawStartupCandidate(
                source_identifier="hn:1",
                name="Acme AI",
                website_url="https://acme.ai",
                evidence=[
                    {
                        "evidence_type": "launch_post",
                        "source_url": "https://news.ycombinator.com/item?id=1",
                    }
                ],
            )
        ]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)

    response = await hacker_news_api_client.post(
        "/api/v1/discovery/hacker-news",
        json={"feeds": ["show", "jobs"], "limit": 1, "lookback_days": 30},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["run"]["source"] == "hacker_news"
    assert data["fetched_item_count"] == 1
    assert data["candidates"][0]["source_identifier"] == "hn:1"


@pytest.mark.asyncio
async def test_hacker_news_discovery_api_rejects_invalid_feed(
    hacker_news_api_client: AsyncClient,
):
    response = await hacker_news_api_client.post(
        "/api/v1/discovery/hacker-news",
        json={"feeds": ["invalid"], "limit": 1},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_hacker_news_run_can_be_retrieved(
    hacker_news_api_client: AsyncClient,
    monkeypatch,
):
    async def discover(self, request):
        return [
            RawStartupCandidate(
                source_identifier="hn:1",
                name="Acme AI",
                website_url="https://acme.ai",
            )
        ]

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)
    create_response = await hacker_news_api_client.post(
        "/api/v1/discovery/hacker-news",
        json={"feeds": ["show"], "limit": 1},
    )
    run_id = create_response.json()["run"]["id"]

    response = await hacker_news_api_client.get(f"/api/v1/discovery/runs/{run_id}")

    assert response.status_code == 200
    assert response.json()["run"]["id"] == run_id


@pytest.mark.asyncio
async def test_hacker_news_adapter_failure_returns_clean_error(
    hacker_news_api_client: AsyncClient,
    monkeypatch,
):
    async def discover(self, request):
        raise RuntimeError("upstream unavailable")

    monkeypatch.setattr(HackerNewsDiscoveryAdapter, "discover", discover)

    response = await hacker_news_api_client.post(
        "/api/v1/discovery/hacker-news",
        json={"feeds": ["show"], "limit": 1},
    )

    assert response.status_code == 502
    data = response.json()
    assert data["error"]["code"] == "HACKER_NEWS_DISCOVERY_ERROR"
    assert data["error"]["details"]["run_id"]
