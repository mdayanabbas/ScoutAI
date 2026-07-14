from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.discovery import get_we_work_remotely_service
from app.core.errors import AppError, NotFoundError
from app.schemas.we_work_remotely_discovery import WWRDiscoveryResult


class FakeWWRService:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.discovery_called = False

    def feed_plan_result(self, **_kwargs):
        return {
            "enabled_feeds": [
                {
                    "feed_type": "programming",
                    "host_path": "weworkremotely.com/categories/remote-programming-jobs.rss",
                    "priority": 0,
                }
            ],
            "profile_target_roles": ["AI Engineer"],
            "accepted_employment_types": ["full_time"],
            "remote_eligibility_policy": ["work_from_anywhere", "remote_india_eligible"],
            "maximum_items": 200,
            "cooldown_active": False,
            "warnings": [],
        }

    async def run_discovery(self, **_kwargs):
        self.discovery_called = True
        if self.exc:
            raise self.exc
        now = datetime.now(timezone.utc)
        return self.result or WWRDiscoveryResult(
            discovery_run_id="run-1",
            status="succeeded",
            profile_id="profile-1",
            feeds_planned=1,
            feeds_completed=1,
            started_at=now,
            finished_at=now,
            duration_ms=0,
        )


@pytest.fixture
async def wwr_client(app):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_feed_plan_endpoint_does_not_run_discovery(app, wwr_client):
    fake = FakeWWRService()
    app.dependency_overrides[get_we_work_remotely_service] = lambda: fake

    response = await wwr_client.get("/api/v1/discovery/we-work-remotely/jobs/feed-plan")

    assert response.status_code == 200
    assert response.json()["enabled_feeds"][0]["feed_type"] == "programming"
    assert fake.discovery_called is False


@pytest.mark.asyncio
async def test_discovery_endpoint_returns_success_and_errors(app, wwr_client):
    app.dependency_overrides[get_we_work_remotely_service] = lambda: FakeWWRService()
    ok = await wwr_client.post("/api/v1/discovery/we-work-remotely/jobs", json={"force": True})
    assert ok.status_code == 200
    assert ok.json()["status"] == "succeeded"

    app.dependency_overrides[get_we_work_remotely_service] = lambda: FakeWWRService(exc=NotFoundError("Job matching profile not found"))
    missing = await wwr_client.post("/api/v1/discovery/we-work-remotely/jobs", json={"force": True})
    assert missing.status_code == 404

    app.dependency_overrides[get_we_work_remotely_service] = lambda: FakeWWRService(
        exc=AppError("WWR_DISCOVERY_DISABLED", "We Work Remotely discovery is disabled", status_code=503)
    )
    disabled = await wwr_client.post("/api/v1/discovery/we-work-remotely/jobs", json={"force": True})
    assert disabled.status_code == 503


@pytest.mark.asyncio
async def test_discovery_endpoint_rejects_arbitrary_url_and_profile(app, wwr_client):
    app.dependency_overrides[get_we_work_remotely_service] = lambda: FakeWWRService()

    response = await wwr_client.post(
        "/api/v1/discovery/we-work-remotely/jobs",
        json={"rss_url": "https://evil.example/jobs.rss", "profile_id": "profile-2"},
    )

    assert response.status_code == 422
