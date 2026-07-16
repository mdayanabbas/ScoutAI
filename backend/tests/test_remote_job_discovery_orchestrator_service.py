from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.core.errors import AppError
from app.schemas.himalayas_discovery import HimalayasDiscoveryResult
from app.schemas.remotive_discovery import RemotiveDiscoveryResult
from app.schemas.we_work_remotely_discovery import WWRDiscoveryResult
from app.services.remote_job_discovery_orchestrator_service import RemoteJobDiscoveryOrchestratorService


class FakeSession:
    def __init__(self):
        self.rollbacks = 0

    def rollback(self):
        self.rollbacks += 1


class FakeProvider:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = []
        self.plan_calls = 0

    def query_plan_result(self, **_kwargs):
        self.plan_calls += 1
        return {"cooldown_active": False, "warnings": []}

    async def run_discovery(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc:
            raise self.exc
        return self.result


class FakeMatchingService:
    def __init__(self, matches=None):
        self.profile = SimpleNamespace(id="profile-1")
        self.matches = matches or []
        self.list_kwargs = None

    def current_profile(self):
        return self.profile

    def list_matches(self, profile_id, **kwargs):
        self.list_kwargs = {"profile_id": profile_id, **kwargs}
        return self.matches


def _result(source: str, *, status="succeeded", reason=None, created=1, records=10):
    now = datetime.now(timezone.utc)
    common = {
        "discovery_run_id": f"{source}-run",
        "status": status,
        "reason": reason,
        "profile_id": "profile-1",
        "candidates_created": created,
        "candidates_existing": 2,
        "candidates_rejected": 3,
        "jobs_created": created,
        "jobs_existing": 4,
        "jobs_updated": 5,
        "jobs_scored": 6,
        "jobs_failed": 7,
        "accepted_jobs": [{"job_id": f"{source}-job", "title": "AI Engineer"}],
        "rejected_samples": [{"source_item_id": f"{source}-reject", "rejection_reason": "rejected"}],
        "started_at": now,
        "finished_at": now,
        "duration_ms": 1,
    }
    if source == "himalayas":
        return HimalayasDiscoveryResult(provider_records_seen=records, unique_records=8, **common)
    if source == "we_work_remotely":
        return WWRDiscoveryResult(feed_items_seen=records, unique_items=8, **common)
    return RemotiveDiscoveryResult(provider_records_seen=records, unique_records=8, **common)


def _service(*, himalayas=None, wwr=None, remotive=None, matching=None):
    return RemoteJobDiscoveryOrchestratorService(
        FakeSession(),
        himalayas_service=himalayas or FakeProvider(_result("himalayas")),
        we_work_remotely_service=wwr or FakeProvider(_result("we_work_remotely")),
        remotive_service=remotive or FakeProvider(_result("remotive")),
        matching_service=matching or FakeMatchingService(),
    )


@pytest.mark.asyncio
async def test_runs_all_sources_by_default_and_aggregates_counters():
    service = _service()

    result = await service.run_remote_discovery()

    assert result.status == "succeeded"
    assert result.sources_planned == ["himalayas", "we_work_remotely", "remotive"]
    assert result.sources_completed == 3
    assert result.total_provider_records_seen == 30
    assert result.total_unique_records == 24
    assert result.total_jobs_created == 3
    assert result.total_jobs_existing == 12
    assert result.total_jobs_updated == 15
    assert result.total_jobs_scored == 18


@pytest.mark.asyncio
async def test_runs_only_selected_sources_and_passes_options_force_and_scoring():
    himalayas = FakeProvider(_result("himalayas"))
    remotive = FakeProvider(_result("remotive"))
    wwr = FakeProvider(_result("we_work_remotely"))
    service = _service(himalayas=himalayas, wwr=wwr, remotive=remotive)

    result = await service.run_remote_discovery(
        force=True,
        sources=["remotive"],
        score_after_ingestion=False,
        remotive_options={"max_requests": 2, "limit_per_request": 25},
    )

    assert result.sources_planned == ["remotive"]
    assert himalayas.calls == []
    assert wwr.calls == []
    assert remotive.calls == [
        {"force": True, "score_after_ingestion": False, "max_requests": 2, "limit_per_request": 25}
    ]


@pytest.mark.asyncio
async def test_provider_failure_is_isolated_and_partial_result_has_safe_error():
    failing = FakeProvider(exc=RuntimeError("secret stack trace"))
    service = _service(wwr=failing)

    result = await service.run_remote_discovery()

    assert result.status == "partial"
    assert result.reason == "some_sources_failed"
    failed = [item for item in result.source_results if item.source == "we_work_remotely"][0]
    assert failed.status == "failed"
    assert failed.error == "RuntimeError"
    assert "secret stack trace" not in result.model_dump_json()


@pytest.mark.asyncio
async def test_all_failed_and_all_cooldown_skipped_statuses_have_reasons():
    failed_service = _service(
        himalayas=FakeProvider(exc=RuntimeError("boom")),
        wwr=FakeProvider(exc=RuntimeError("boom")),
        remotive=FakeProvider(exc=RuntimeError("boom")),
    )
    failed = await failed_service.run_remote_discovery()
    assert failed.status == "failed"
    assert failed.reason == "all_sources_failed"

    skipped_service = _service(
        himalayas=FakeProvider(_result("himalayas", status="skipped", reason="cooldown")),
        wwr=FakeProvider(_result("we_work_remotely", status="skipped", reason="cooldown")),
        remotive=FakeProvider(_result("remotive", status="skipped", reason="cooldown")),
    )
    skipped = await skipped_service.run_remote_discovery()
    assert skipped.status == "skipped"
    assert skipped.reason == "provider_cooldowns_active"


@pytest.mark.asyncio
async def test_disabled_selected_source_is_skipped(monkeypatch):
    service = _service()
    monkeypatch.setattr(service.settings, "REMOTIVE_DISCOVERY_ENABLED", False)

    result = await service.run_remote_discovery(sources=["remotive"])

    assert result.status == "skipped"
    assert result.source_results[0].status == "disabled"
    assert result.reason == "no_sources_enabled"


@pytest.mark.asyncio
async def test_top_recommendations_are_included_without_descriptions():
    job = SimpleNamespace(
        id="job-1",
        title="AI Engineer",
        company=SimpleNamespace(name="Jobs Co"),
        salary_min=100000,
        salary_max=150000,
        salary_currency="USD",
        job_url="https://jobs.example/1",
        apply_url="https://jobs.example/apply/1",
        description="Do not expose this",
    )
    match = SimpleNamespace(
        job=job,
        remote_eligibility="work_from_anywhere",
        match_tier="best_match",
        eligibility_status="eligible",
        total_score=91.5,
        eligibility_reason="Strong match",
    )
    matching = FakeMatchingService(matches=[match])
    service = _service(matching=matching)

    result = await service.run_remote_discovery()

    assert matching.list_kwargs["include_unsuitable"] is False
    assert matching.list_kwargs["include_remote_unknown"] is False
    assert matching.list_kwargs["order_by"] == "recommended"
    assert result.top_recommendations[0].company_name == "Jobs Co"
    assert "Do not expose this" not in result.model_dump_json()


def test_plan_endpoint_data_uses_provider_plans_without_running_discovery(monkeypatch):
    himalayas = FakeProvider(_result("himalayas"))
    wwr = FakeProvider(_result("we_work_remotely"))
    remotive = FakeProvider(_result("remotive"))
    service = _service(himalayas=himalayas, wwr=wwr, remotive=remotive)
    monkeypatch.setattr(service.settings, "WWR_DISCOVERY_ENABLED", False)

    plan = service.plan_remote_discovery()

    assert plan.profile_id == "profile-1"
    assert plan.enabled_sources == ["himalayas", "remotive"]
    assert plan.disabled_sources == ["we_work_remotely"]
    assert himalayas.plan_calls == 1
    assert wwr.plan_calls == 0
    assert remotive.plan_calls == 1
    assert himalayas.calls == []


@pytest.mark.asyncio
async def test_no_enabled_sources_can_be_reported_by_service(monkeypatch):
    service = _service()
    monkeypatch.setattr(service.settings, "HIMALAYAS_DISCOVERY_ENABLED", False)
    monkeypatch.setattr(service.settings, "WWR_DISCOVERY_ENABLED", False)
    monkeypatch.setattr(service.settings, "REMOTIVE_DISCOVERY_ENABLED", False)

    with pytest.raises(AppError) as exc:
        await service.run_remote_discovery()

    assert exc.value.status_code == 503
