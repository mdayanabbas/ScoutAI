from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.discovery import get_remotive_service
from app.core.errors import AppError, NotFoundError
from app.schemas.remotive_discovery import RemotiveDiscoveryResult


class FakeRemotiveService:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.discovery_called = False

    def query_plan_result(self, **_kwargs):
        return {
            "profile_target_roles": ["AI Engineer"],
            "planned_requests": [{"request_type": "category", "category": "software-dev", "limit": 200}],
            "total_planned_requests": 1,
            "configured_request_cap": 4,
            "generated_from_profile": True,
            "canonical_target_roles": ["AI Engineer"],
            "cooldown_active": False,
            "warnings": [],
        }

    async def run_discovery(self, **_kwargs):
        self.discovery_called = True
        if self.exc:
            raise self.exc
        now = datetime.now(timezone.utc)
        return self.result or RemotiveDiscoveryResult(
            discovery_run_id="run-1",
            status="succeeded",
            reason=None,
            profile_id="profile-1",
            requests_planned=1,
            requests_completed=1,
            started_at=now,
            finished_at=now,
            duration_ms=0,
        )


@pytest.fixture
async def remotive_client(app):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_query_plan_endpoint_does_not_run_discovery(app, remotive_client):
    fake = FakeRemotiveService()
    app.dependency_overrides[get_remotive_service] = lambda: fake

    response = await remotive_client.get("/api/v1/discovery/remotive/jobs/query-plan")

    assert response.status_code == 200
    assert response.json()["planned_requests"][0]["category"] == "software-dev"
    assert fake.discovery_called is False


@pytest.mark.asyncio
async def test_discovery_endpoint_success_partial_skipped_and_errors(app, remotive_client):
    app.dependency_overrides[get_remotive_service] = lambda: FakeRemotiveService()
    ok = await remotive_client.post("/api/v1/discovery/remotive/jobs", json={"force": True})
    assert ok.status_code == 200
    assert ok.json()["status"] == "succeeded"

    now = datetime.now(timezone.utc)
    partial_result = RemotiveDiscoveryResult(status="partial", reason="remotive_partial_query_failure", started_at=now, finished_at=now, duration_ms=0)
    app.dependency_overrides[get_remotive_service] = lambda: FakeRemotiveService(result=partial_result)
    partial = await remotive_client.post("/api/v1/discovery/remotive/jobs", json={"force": True})
    assert partial.status_code == 200
    assert partial.json()["reason"] == "remotive_partial_query_failure"

    skipped_result = RemotiveDiscoveryResult(status="skipped", reason="remotive_discovery_cooldown_active", started_at=now, finished_at=now, duration_ms=0)
    app.dependency_overrides[get_remotive_service] = lambda: FakeRemotiveService(result=skipped_result)
    skipped = await remotive_client.post("/api/v1/discovery/remotive/jobs", json={})
    assert skipped.status_code == 200
    assert skipped.json()["status"] == "skipped"

    app.dependency_overrides[get_remotive_service] = lambda: FakeRemotiveService(exc=NotFoundError("Job matching profile not found"))
    missing = await remotive_client.post("/api/v1/discovery/remotive/jobs", json={"force": True})
    assert missing.status_code == 404

    app.dependency_overrides[get_remotive_service] = lambda: FakeRemotiveService(
        exc=AppError("REMOTIVE_DISCOVERY_DISABLED", "Remotive discovery is disabled", status_code=503)
    )
    disabled = await remotive_client.post("/api/v1/discovery/remotive/jobs", json={"force": True})
    assert disabled.status_code == 503


@pytest.mark.asyncio
async def test_discovery_endpoint_rejects_arbitrary_provider_inputs_and_excludes_raw_payload(app, remotive_client):
    app.dependency_overrides[get_remotive_service] = lambda: FakeRemotiveService()

    response = await remotive_client.post(
        "/api/v1/discovery/remotive/jobs",
        json={"api_url": "https://evil.example", "search": "Account Executive", "profile_id": "profile-2"},
    )
    assert response.status_code == 422

    ok = await remotive_client.post("/api/v1/discovery/remotive/jobs", json={"max_requests": 1, "limit_per_request": 10})
    assert ok.status_code == 200
    body = ok.json()
    assert "description" not in body
    assert "raw_payload" not in body
