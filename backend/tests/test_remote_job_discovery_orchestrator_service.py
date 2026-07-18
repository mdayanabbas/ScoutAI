from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.jobs.enrichment.providers.ashby_models import AshbyPublicJobBoardResponse, AshbyPublicJobPosting
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
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
    def __init__(self, matches=None, score_result=None):
        self.profile = SimpleNamespace(id="profile-1")
        self.matches = matches or []
        self.list_kwargs = None
        self.score_kwargs = None
        self.score_result = score_result

    def current_profile(self):
        return self.profile

    def list_matches(self, profile_id, **kwargs):
        self.list_kwargs = {"profile_id": profile_id, **kwargs}
        matches = list(self.matches)
        job_ids = set(kwargs.get("job_ids") or [])
        source_platforms = set(kwargs.get("source_platforms") or [])
        if job_ids:
            matches = [match for match in matches if match.job.id in job_ids]
        if source_platforms:
            matches = [match for match in matches if getattr(match.job, "source_platform", None) in source_platforms]
        return matches

    def score_jobs(self, profile_id, **kwargs):
        self.score_kwargs = {"profile_id": profile_id, **kwargs}
        if self.score_result is not None:
            return self.score_result
        return SimpleNamespace(
            jobs_scored=len(kwargs.get("job_ids") or []),
            jobs_failed=0,
            eligible=0,
            stretch=0,
            uncertain=0,
            unsuitable=0,
        )


class FakeHackerNewsDiscoveryService:
    def __init__(self, events):
        self.events = events
        self.request = None

    async def run_hacker_news_discovery(self, request):
        self.events.append("discover")
        self.request = request
        run = SimpleNamespace(
            id="hn-run",
            candidates_found=2,
            candidates_normalized=2,
            candidates_deferred=0,
            candidates_rejected=0,
            candidates_failed=0,
            companies_created=1,
            companies_matched=1,
        )
        return SimpleNamespace(run=run, fetched_item_count=3, skipped_item_count=1)


class FakeDomainEnrichmentService:
    def __init__(self, events):
        self.events = events
        self.run_id = None

    async def enrich_discovery_run(self, run_id):
        self.events.append("enrich_domains")
        self.run_id = run_id
        return SimpleNamespace(candidates_resolved=2, candidates_unresolved=0, results=[])


class FakeDiscoveryJobIngestionService:
    def __init__(self, events):
        self.events = events
        self.run_id = None

    def ingest_discovery_run(self, run_id):
        self.events.append("ingest_jobs")
        self.run_id = run_id
        return SimpleNamespace(
            jobs_created=1,
            jobs_existing=1,
            candidates_skipped=0,
            candidates_failed=0,
            results=[SimpleNamespace(job_id="job-1"), SimpleNamespace(job_id="job-2")],
        )


class FakeJobEnrichmentService:
    def __init__(self, events, *, unresolved=0, failed=0):
        self.events = events
        self.kwargs = None
        self.unresolved = unresolved
        self.failed = failed

    async def enrich_jobs(self, **kwargs):
        self.events.append("enrich_jobs")
        self.kwargs = kwargs
        return SimpleNamespace(
            jobs_enriched=1,
            jobs_partially_enriched=1,
            jobs_unresolved=self.unresolved,
            jobs_failed=self.failed,
        )


class FakeAshbyBoardClient:
    def __init__(self, jobs):
        self.jobs = jobs
        self.calls = []

    async def list_published_jobs(self, board_slug: str):
        self.calls.append(board_slug)
        return AshbyPublicJobBoardResponse(board_slug=board_slug, jobs=self.jobs, status_code=200)


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
        "accepted_jobs": [
            {
                "job_id": f"{source}-job",
                "company_name": "Jobs Co",
                "title": "AI Engineer",
                "remote_eligibility": "work_from_anywhere",
                "action": "created",
                "attribution_label": "Remote Jobs",
            }
        ],
        "rejected_samples": [
            {
                "source_item_id": f"{source}-reject",
                "title": "Senior AI Engineer",
                "company_name": "Jobs Co",
                "rejection_reason": "rejected",
            }
        ],
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


def _service_with_hacker_news(events, *, matching=None, job_enrichment_service=None):
    return RemoteJobDiscoveryOrchestratorService(
        FakeSession(),
        himalayas_service=FakeProvider(_result("himalayas")),
        we_work_remotely_service=FakeProvider(_result("we_work_remotely")),
        remotive_service=FakeProvider(_result("remotive")),
        discovery_service=FakeHackerNewsDiscoveryService(events),
        domain_enrichment_service=FakeDomainEnrichmentService(events),
        job_ingestion_service=FakeDiscoveryJobIngestionService(events),
        job_enrichment_service=job_enrichment_service or FakeJobEnrichmentService(events),
        matching_service=matching or FakeMatchingService(),
    )


def _match(job_id: str, *, source_platform: str, total_score: float = 90, status: str = "eligible"):
    job = SimpleNamespace(
        id=job_id,
        title=f"{source_platform} job {job_id}",
        company=SimpleNamespace(name=f"{source_platform} Co"),
        source_platform=source_platform,
        salary_min=None,
        salary_max=None,
        salary_currency=None,
        job_url=f"https://jobs.example/{job_id}",
        apply_url=f"https://jobs.example/{job_id}/apply",
        description="Do not expose this",
    )
    return SimpleNamespace(
        job=job,
        remote_eligibility="work_from_anywhere",
        match_tier="best_match",
        eligibility_status=status,
        total_score=total_score,
        eligibility_reason="Strong match",
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
    assert result.recommendation_scope == "global"
    assert result.recommendation_source_filter == []
    assert result.recommendation_job_ids_count == 0


@pytest.mark.asyncio
async def test_explicit_hacker_news_run_returns_only_run_job_recommendations():
    matches = [
        _match("job-1", source_platform="hacker_news", total_score=91),
        _match("job-2", source_platform="ashby", total_score=88),
        _match("himalayas-job", source_platform="himalayas", total_score=99),
    ]
    matching = FakeMatchingService(matches=matches)
    service = _service_with_hacker_news([], matching=matching)

    result = await service.run_remote_discovery(sources=["hacker_news"])

    assert result.recommendation_scope == "run_jobs"
    assert result.recommendation_source_filter == ["hacker_news"]
    assert result.recommendation_job_ids_count == 2
    assert {item.job_id for item in result.top_recommendations} == {"job-1", "job-2"}
    assert "himalayas-job" not in {item.job_id for item in result.top_recommendations}
    assert matching.list_kwargs["job_ids"] == ["job-1", "job-2"]
    assert matching.list_kwargs["source_platforms"] is None


@pytest.mark.asyncio
async def test_explicit_himalayas_run_returns_only_himalayas_recommendations():
    matches = [
        _match("himalayas-job", source_platform="himalayas", total_score=91),
        _match("remotive-job", source_platform="remotive", total_score=99),
    ]
    service = _service(matching=FakeMatchingService(matches=matches))

    result = await service.run_remote_discovery(sources=["himalayas"])

    assert result.recommendation_scope == "run_jobs"
    assert result.recommendation_source_filter == ["himalayas"]
    assert result.recommendation_job_ids_count == 1
    assert [item.job_id for item in result.top_recommendations] == ["himalayas-job"]


@pytest.mark.asyncio
async def test_explicit_multiple_source_run_does_not_leak_unrelated_recommendations():
    matches = [
        _match("himalayas-job", source_platform="himalayas", total_score=91),
        _match("remotive-job", source_platform="remotive", total_score=89),
        _match("we_work_remotely-job", source_platform="we_work_remotely", total_score=99),
    ]
    service = _service(matching=FakeMatchingService(matches=matches))

    result = await service.run_remote_discovery(sources=["himalayas", "remotive"])

    assert result.recommendation_scope == "run_jobs"
    assert result.recommendation_source_filter == ["himalayas", "remotive"]
    assert result.recommendation_job_ids_count == 2
    assert {item.job_id for item in result.top_recommendations} == {"himalayas-job", "remotive-job"}


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
    assert plan.available_sources
    assert {item["source"] for item in plan.available_sources} >= {"hacker_news", "ycombinator", "ashby"}
    assert plan.recommended_defaults["hacker_news"]["enabled"] is True
    assert plan.recommended_defaults["ycombinator"]["enabled"] is True
    assert plan.recommended_defaults["ashby"]["enabled"] is True


@pytest.mark.asyncio
async def test_hacker_news_source_runs_discovery_enrichment_ingestion_enrichment_and_scoring():
    events = []
    matching = FakeMatchingService(
        score_result=SimpleNamespace(
            jobs_scored=2,
            jobs_failed=0,
            eligible=1,
            stretch=1,
            uncertain=0,
            unsuitable=0,
        )
    )
    service = _service_with_hacker_news(events, matching=matching)

    result = await service.run_remote_discovery(
        sources=["hacker_news"],
        hacker_news_options={
            "feeds": ["jobs"],
            "limit": 20,
            "lookback_days": 14,
            "minimum_score": 1,
        },
    )

    assert result.status == "succeeded"
    assert result.sources_planned == ["hacker_news"]
    assert events == ["discover", "enrich_domains", "ingest_jobs", "enrich_jobs"]
    source = result.source_results[0]
    assert source.source == "hacker_news"
    assert source.provider_records_seen == 3
    assert source.candidates_found == 2
    assert source.candidates_created == 2
    assert source.companies_created == 1
    assert source.companies_matched == 1
    assert source.domains_resolved == 2
    assert source.jobs_created == 1
    assert source.jobs_existing == 1
    assert source.jobs_enriched == 2
    assert source.jobs_scored == 2
    assert source.diagnostics["job_ids"] == ["job-1", "job-2"]
    assert source.diagnostics["h_n_jobs_scored_eligible"] == 1
    assert source.diagnostics["h_n_jobs_scored_stretch"] == 1
    assert source.diagnostics["h_n_jobs_scored_uncertain"] == 0
    assert source.diagnostics["h_n_jobs_scored_unsuitable"] == 0
    assert source.diagnostics["h_n_jobs_remaining_open_roles"] == 0
    assert source.diagnostics["h_n_jobs_remaining_remote_unknown"] == 0
    assert source.diagnostics["h_n_jobs_not_enriched"] == 0
    assert matching.score_kwargs == {"profile_id": "profile-1", "job_ids": ["job-1", "job-2"], "force": True}


@pytest.mark.asyncio
async def test_hacker_news_source_reports_enrichment_warning_counts():
    events = []
    service = _service_with_hacker_news(
        events,
        job_enrichment_service=FakeJobEnrichmentService(events, unresolved=1, failed=1),
    )

    result = await service.run_remote_discovery(sources=["hacker_news"])

    source = result.source_results[0]
    assert source.status == "partial"
    assert "2 of 2 Hacker News jobs were not enriched" in source.warnings
    assert source.diagnostics["h_n_jobs_not_enriched"] == 2
    assert source.diagnostics["jobs_not_enriched"] == 2


@pytest.mark.asyncio
async def test_new_opt_in_sources_can_be_disabled_by_request_and_ashby_requires_board_slugs():
    hn_disabled = await _service_with_hacker_news([]).run_remote_discovery(
        sources=["hacker_news"],
        hacker_news_options={"enabled": False},
    )
    assert hn_disabled.status == "skipped"
    assert hn_disabled.source_results[0].reason == "hacker_news_disabled_by_request"

    yc_disabled = await _service().run_remote_discovery(
        sources=["ycombinator"],
        ycombinator_options={"enabled": False},
    )
    assert yc_disabled.status == "skipped"
    assert yc_disabled.source_results[0].reason == "ycombinator_disabled_by_request"

    ashby_missing = await _service().run_remote_discovery(sources=["ashby"])
    assert ashby_missing.status == "skipped"
    assert ashby_missing.source_results[0].reason == "ashby_board_slugs_required"


@pytest.mark.asyncio
async def test_ashby_standalone_board_source_creates_exact_enriched_jobs(db_session):
    slug = f"lago-{uuid4().hex[:8]}"
    posting = AshbyPublicJobPosting(
        id="backend",
        title="Backend Engineer",
        location="Remote",
        workplace_type="Remote",
        employment_type="FullTime",
        description_plain="Build billing systems with Python and PostgreSQL.",
        job_url=f"https://jobs.ashbyhq.com/{slug}/backend",
        apply_url=f"https://jobs.ashbyhq.com/{slug}/backend/application",
    )
    matching = FakeMatchingService()
    ashby_client = FakeAshbyBoardClient([posting])
    service = RemoteJobDiscoveryOrchestratorService(
        db_session,
        himalayas_service=FakeProvider(_result("himalayas")),
        we_work_remotely_service=FakeProvider(_result("we_work_remotely")),
        remotive_service=FakeProvider(_result("remotive")),
        ashby_client=ashby_client,
        matching_service=matching,
    )

    result = await service.run_remote_discovery(
        sources=["ashby"],
        ashby_options={"board_slugs": [slug], "max_jobs_per_board": 5},
    )

    assert result.status == "succeeded"
    assert ashby_client.calls == [slug]
    source = result.source_results[0]
    assert source.source == "ashby"
    assert source.status == "partial"
    assert source.jobs_created == 1
    assert source.jobs_enriched == 1
    assert source.jobs_scored == 1
    assert source.diagnostics["ashby_boards_resolved"] == 1
    assert source.diagnostics["ashby_jobs_expanded"] == 1
    assert source.diagnostics["ashby_company_domain_missing_count"] == 1
    company = CompanyRepository(db_session).get_by_domain(f"ashby:{slug}")
    assert company is not None
    assert company.website_url is None
    job = JobRepository(db_session).get_by_company_and_url(company.id, f"https://jobs.ashbyhq.com/{slug}/backend")
    assert job is not None
    assert job.title == "Backend Engineer"
    assert job.apply_url == f"https://jobs.ashbyhq.com/{slug}/backend/application"
    assert job.enrichment_status == "enriched"
    assert matching.score_kwargs == {"profile_id": "profile-1", "job_ids": [job.id], "force": True}


@pytest.mark.asyncio
async def test_no_enabled_sources_can_be_reported_by_service(monkeypatch):
    service = _service()
    monkeypatch.setattr(service.settings, "HIMALAYAS_DISCOVERY_ENABLED", False)
    monkeypatch.setattr(service.settings, "WWR_DISCOVERY_ENABLED", False)
    monkeypatch.setattr(service.settings, "REMOTIVE_DISCOVERY_ENABLED", False)

    with pytest.raises(AppError) as exc:
        await service.run_remote_discovery()

    assert exc.value.status_code == 503
