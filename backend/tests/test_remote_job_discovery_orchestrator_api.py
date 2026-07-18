from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.discovery import get_remote_discovery_orchestrator_service
from app.core.errors import AppError, NotFoundError
from app.schemas.remote_discovery import (
    RemoteDiscoverySourceResult,
    RemoteJobDiscoveryOrchestratorResult,
    RemoteJobDiscoveryPlanRead,
)


class FakeRemoteDiscoveryOrchestrator:
    def __init__(self, result=None, plan=None, exc=None):
        self.result = result
        self.plan = plan
        self.exc = exc
        self.run_calls = []
        self.plan_calls = 0

    def plan_remote_discovery(self):
        self.plan_calls += 1
        if self.exc:
            raise self.exc
        return self.plan or _plan()

    async def run_remote_discovery(self, **kwargs):
        self.run_calls.append(kwargs)
        if self.exc:
            raise self.exc
        return self.result or _result()


def _source(source="remotive", status="succeeded"):
    now = datetime.now(timezone.utc)
    return RemoteDiscoverySourceResult(
        source=source,
        status=status,
        reason="provider_failed" if status == "failed" else None,
        started_at=now,
        finished_at=now,
        duration_ms=1,
        jobs_created=1 if status == "succeeded" else 0,
    )


def _result(status="succeeded", reason=None):
    now = datetime.now(timezone.utc)
    return RemoteJobDiscoveryOrchestratorResult(
        status=status,
        reason=reason,
        profile_id="profile-1",
        sources_planned=["remotive"],
        sources_completed=0 if status == "failed" else 1,
        sources_failed=1 if status == "failed" else 0,
        source_results=[_source(status="failed" if status == "failed" else "succeeded")],
        started_at=now,
        finished_at=now,
        duration_ms=1,
    )


def _plan():
    return RemoteJobDiscoveryPlanRead(
        profile_id="profile-1",
        enabled_sources=["himalayas", "we_work_remotely", "remotive"],
        disabled_sources=[],
        cooldowns={
            "himalayas": {"enabled": True, "cooldown_active": False},
            "we_work_remotely": {"enabled": True, "cooldown_active": False},
            "remotive": {"enabled": True, "cooldown_active": False},
        },
        himalayas={"query_count": 1},
        we_work_remotely={"enabled_feeds": [{"feed_type": "programming"}]},
        remotive={"total_planned_requests": 1},
        recommended_defaults={"force": False, "score_after_ingestion": True},
    )


@pytest.fixture
async def remote_discovery_client(app):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_plan_endpoint_returns_source_plan_without_running_discovery(app, remote_discovery_client):
    fake = FakeRemoteDiscoveryOrchestrator()
    app.dependency_overrides[get_remote_discovery_orchestrator_service] = lambda: fake

    response = await remote_discovery_client.get("/api/v1/discovery/remote-jobs/plan")

    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == "profile-1"
    assert body["enabled_sources"] == ["himalayas", "we_work_remotely", "remotive"]
    assert body["remotive"]["total_planned_requests"] == 1
    assert fake.plan_calls == 1
    assert fake.run_calls == []


@pytest.mark.asyncio
async def test_run_endpoint_succeeds_and_supports_selected_sources(app, remote_discovery_client):
    fake = FakeRemoteDiscoveryOrchestrator()
    app.dependency_overrides[get_remote_discovery_orchestrator_service] = lambda: fake

    response = await remote_discovery_client.post(
        "/api/v1/discovery/remote-jobs/run",
        json={
            "force": True,
            "sources": ["remotive"],
            "score_after_ingestion": False,
            "remotive": {"max_requests": 2, "limit_per_request": 25},
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert fake.run_calls == [
        {
            "force": True,
            "sources": ["remotive"],
            "score_after_ingestion": False,
            "himalayas_options": None,
            "we_work_remotely_options": None,
            "remotive_options": {"max_requests": 2, "limit_per_request": 25},
            "hacker_news_options": None,
            "ycombinator_options": None,
            "ashby_options": None,
        }
    ]


@pytest.mark.asyncio
async def test_invalid_source_caps_and_arbitrary_inputs_return_422(app, remote_discovery_client):
    app.dependency_overrides[get_remote_discovery_orchestrator_service] = lambda: FakeRemoteDiscoveryOrchestrator()

    invalid_source = await remote_discovery_client.post("/api/v1/discovery/remote-jobs/run", json={"sources": ["linkedin"]})
    assert invalid_source.status_code == 422

    invalid_cap = await remote_discovery_client.post(
        "/api/v1/discovery/remote-jobs/run",
        json={"remotive": {"max_requests": 999}},
    )
    assert invalid_cap.status_code == 422

    arbitrary_inputs = await remote_discovery_client.post(
        "/api/v1/discovery/remote-jobs/run",
        json={"profile_id": "profile-2", "provider_url": "https://evil.example"},
    )
    assert arbitrary_inputs.status_code == 422


@pytest.mark.asyncio
async def test_missing_profile_and_no_enabled_sources_errors(app, remote_discovery_client):
    app.dependency_overrides[get_remote_discovery_orchestrator_service] = lambda: FakeRemoteDiscoveryOrchestrator(
        exc=NotFoundError("Job matching profile not found")
    )
    missing = await remote_discovery_client.post("/api/v1/discovery/remote-jobs/run", json={})
    assert missing.status_code == 404

    app.dependency_overrides[get_remote_discovery_orchestrator_service] = lambda: FakeRemoteDiscoveryOrchestrator(
        exc=AppError("REMOTE_DISCOVERY_DISABLED", "No remote discovery sources are enabled", status_code=503)
    )
    disabled = await remote_discovery_client.post("/api/v1/discovery/remote-jobs/run", json={})
    assert disabled.status_code == 503


@pytest.mark.asyncio
async def test_partial_and_all_provider_failure_return_200(app, remote_discovery_client):
    app.dependency_overrides[get_remote_discovery_orchestrator_service] = lambda: FakeRemoteDiscoveryOrchestrator(
        result=_result(status="partial", reason="some_sources_failed")
    )
    partial = await remote_discovery_client.post("/api/v1/discovery/remote-jobs/run", json={})
    assert partial.status_code == 200
    assert partial.json()["status"] == "partial"

    app.dependency_overrides[get_remote_discovery_orchestrator_service] = lambda: FakeRemoteDiscoveryOrchestrator(
        result=_result(status="failed", reason="all_sources_failed")
    )
    failed = await remote_discovery_client.post("/api/v1/discovery/remote-jobs/run", json={})
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_response_shape_excludes_descriptions_and_raw_payloads(app, remote_discovery_client):
    fake = FakeRemoteDiscoveryOrchestrator()
    app.dependency_overrides[get_remote_discovery_orchestrator_service] = lambda: fake

    response = await remote_discovery_client.post("/api/v1/discovery/remote-jobs/run", json={})

    assert response.status_code == 200
    text = response.text
    assert "description" not in text
    assert "raw_payload" not in text
