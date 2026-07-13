from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.discovery import get_himalayas_service
from app.core.errors import AppError, NotFoundError
from app.schemas.himalayas_discovery import HimalayasDiscoveryResult


class FakeHimalayasService:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.discovery_called = False

    def query_plan_result(self):
        return {
            "current_profile_target_titles": ["AI Engineer"],
            "normalized_queries": ["AI Engineer"],
            "worldwide_passes": [{"query": "AI Engineer", "query_type": "worldwide", "worldwide": True}],
            "india_passes": [{"query": "AI Engineer", "query_type": "india", "country": "IN"}],
            "query_count": 1,
            "generated_from_profile": True,
            "warnings": [],
        }

    async def run_discovery(self, **_kwargs):
        self.discovery_called = True
        if self.exc:
            raise self.exc
        now = datetime.now(timezone.utc)
        return self.result or HimalayasDiscoveryResult(
            discovery_run_id="run-1",
            status="succeeded",
            profile_id="profile-1",
            started_at=now,
            finished_at=now,
            duration_ms=0,
        )


@pytest.fixture
async def himalayas_client(app):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_query_plan_endpoint_does_not_run_discovery(app, himalayas_client):
    fake = FakeHimalayasService()
    app.dependency_overrides[get_himalayas_service] = lambda: fake

    response = await himalayas_client.get("/api/v1/discovery/himalayas/jobs/query-plan")

    assert response.status_code == 200
    assert response.json()["normalized_queries"] == ["AI Engineer"]
    assert fake.discovery_called is False


@pytest.mark.asyncio
async def test_discovery_endpoint_returns_success_and_errors(app, himalayas_client):
    app.dependency_overrides[get_himalayas_service] = lambda: FakeHimalayasService()
    ok = await himalayas_client.post("/api/v1/discovery/himalayas/jobs", json={"force": True, "max_queries": 1})
    assert ok.status_code == 200
    assert ok.json()["status"] == "succeeded"

    app.dependency_overrides[get_himalayas_service] = lambda: FakeHimalayasService(exc=NotFoundError("Job matching profile not found"))
    missing = await himalayas_client.post("/api/v1/discovery/himalayas/jobs", json={"force": True})
    assert missing.status_code == 404

    app.dependency_overrides[get_himalayas_service] = lambda: FakeHimalayasService(
        exc=AppError("HIMALAYAS_DISCOVERY_DISABLED", "Himalayas discovery is disabled", status_code=503)
    )
    disabled = await himalayas_client.post("/api/v1/discovery/himalayas/jobs", json={"force": True})
    assert disabled.status_code == 503


@pytest.mark.asyncio
async def test_discovery_endpoint_rejects_arbitrary_url_or_profile(app, himalayas_client):
    app.dependency_overrides[get_himalayas_service] = lambda: FakeHimalayasService()

    response = await himalayas_client.post(
        "/api/v1/discovery/himalayas/jobs",
        json={"api_url": "https://evil.example", "profile_id": "profile-2"},
    )

    assert response.status_code == 422
