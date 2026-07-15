from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.discovery.sources.remotive.models import RemotiveJobPayload, RemotiveJobsResponse
from app.models.job_matching_profile import JobMatchingProfile
from app.models.user_profile import UserProfile
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import UserProfileRepository
from app.services.remotive_remote_job_discovery_service import RemotiveRemoteJobDiscoveryService


class FakeRemotiveClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def list_jobs(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def _settings(**overrides):
    values = {
        "REMOTIVE_DISCOVERY_ENABLED": True,
        "REMOTIVE_API_BASE_URL": "https://remotive.com",
        "REMOTIVE_JOBS_PATH": "/api/remote-jobs",
        "REMOTIVE_REQUEST_TIMEOUT_SECONDS": 20,
        "REMOTIVE_MAX_RETRIES": 1,
        "REMOTIVE_MAX_RESPONSE_BYTES": 10_000_000,
        "REMOTIVE_DISCOVERY_COOLDOWN_HOURS": 0,
        "REMOTIVE_MAX_REQUESTS_PER_RUN": 2,
        "REMOTIVE_MAX_JOBS_PER_REQUEST": 200,
        "REMOTIVE_MAX_JOBS_PER_RUN": 100,
        "REMOTIVE_SCORE_AFTER_INGESTION": False,
        "REMOTIVE_STORE_REJECTED_CANDIDATES": True,
        "REMOTIVE_SOFTWARE_CATEGORY_ENABLED": True,
        "REMOTIVE_DATA_CATEGORY_ENABLED": True,
        "REMOTIVE_REQUEST_DELAY_MS": 0,
        "REMOTIVE_MAX_JOB_AGE_DAYS": 45,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _profile(db_session):
    user = UserProfileRepository(db_session).create_profile(UserProfile(display_name="Abbas"))
    profile = JobMatchingProfile(
        user_profile_id=user.id,
        target_titles_json=["AI Engineer", "Machine Learning Engineer"],
        target_role_categories_json=["ai_engineer"],
        accepted_employment_types_json=["full_time", "contract"],
        preferred_countries_json=["India"],
        work_authorization_countries_json=["India"],
        willing_to_relocate=False,
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


def _job(id=1, title="AI Engineer", company="Remote AI Co", location="Worldwide"):
    return RemotiveJobPayload.model_validate(
        {
            "id": id,
            "url": f"https://remotive.com/remote-jobs/software-dev/{id}",
            "title": title,
            "company_name": company,
            "job_type": "full_time",
            "publication_date": "2026-07-14T10:00:00",
            "candidate_required_location": location,
            "description": "Build AI systems. 2 years experience.",
        }
    )


def _response(*jobs, reason=None):
    return RemotiveJobsResponse(
        job_count=len(jobs),
        jobs=list(jobs),
        status_code=429 if reason == "remotive_rate_limited" else 200,
        reason=reason,
        error_code=reason,
    )


@pytest.mark.asyncio
async def test_service_creates_candidate_evidence_company_job_and_deduplicates(db_session, monkeypatch):
    profile = _profile(db_session)
    monkeypatch.setattr("app.services.remotive_remote_job_discovery_service.get_settings", lambda: _settings())
    client = FakeRemotiveClient([_response(_job(), _job()), _response(_job(id=2, title="Product Manager"))])

    result = await RemotiveRemoteJobDiscoveryService(db_session, client=client).run_discovery(force=True, score_after_ingestion=False)

    assert result.status == "succeeded"
    assert result.profile_id == profile.id
    assert result.unique_records == 2
    assert result.duplicate_records == 1
    assert result.candidates_created == 2
    assert result.candidates_rejected == 1
    assert result.jobs_created == 1
    assert result.accepted_jobs[0].attribution_label == "Remotive"
    assert result.rejected_samples[0].rejection_reason == "rejected_role"
    assert len(JobRepository(db_session).list_jobs()) == 1


@pytest.mark.asyncio
async def test_service_missing_company_preserves_rejected_candidate_without_job(db_session, monkeypatch):
    _profile(db_session)
    monkeypatch.setattr("app.services.remotive_remote_job_discovery_service.get_settings", lambda: _settings(REMOTIVE_MAX_REQUESTS_PER_RUN=1))
    missing_company = _job(id=20, company=None)

    result = await RemotiveRemoteJobDiscoveryService(db_session, client=FakeRemotiveClient([_response(missing_company)])).run_discovery(force=True)

    assert result.candidates_rejected == 1
    assert result.jobs_created == 0
    assert result.rejected_samples[0].rejection_reason == "rejected_missing_company_identity"


@pytest.mark.asyncio
async def test_service_repeated_run_reuses_existing_job_and_force_bypasses_cooldown(db_session, monkeypatch):
    _profile(db_session)
    monkeypatch.setattr("app.services.remotive_remote_job_discovery_service.get_settings", lambda: _settings(REMOTIVE_DISCOVERY_COOLDOWN_HOURS=24, REMOTIVE_MAX_REQUESTS_PER_RUN=1))
    client = FakeRemotiveClient([_response(_job()), _response(_job())])
    service = RemotiveRemoteJobDiscoveryService(db_session, client=client)

    first = await service.run_discovery(force=True, score_after_ingestion=False)
    skipped = await service.run_discovery(force=False, score_after_ingestion=False)
    forced = await service.run_discovery(force=True, score_after_ingestion=False)

    assert first.jobs_created == 1
    assert skipped.status == "skipped"
    assert skipped.reason == "remotive_discovery_cooldown_active"
    assert forced.jobs_existing == 1
    assert len(JobRepository(db_session).list_jobs()) == 1


@pytest.mark.asyncio
async def test_service_partial_failed_empty_and_rate_limited_runs(db_session, monkeypatch):
    _profile(db_session)
    monkeypatch.setattr("app.services.remotive_remote_job_discovery_service.get_settings", lambda: _settings(REMOTIVE_MAX_REQUESTS_PER_RUN=2))

    partial = await RemotiveRemoteJobDiscoveryService(db_session, client=FakeRemotiveClient([_response(_job()), _response(reason="remotive_provider_error")])).run_discovery(force=True)
    assert partial.status == "partial"
    assert partial.reason == "remotive_partial_query_failure"

    failed = await RemotiveRemoteJobDiscoveryService(db_session, client=FakeRemotiveClient([_response(reason="remotive_provider_error"), _response(reason="remotive_provider_error")])).run_discovery(force=True)
    assert failed.status == "failed"
    assert failed.reason

    empty = await RemotiveRemoteJobDiscoveryService(db_session, client=FakeRemotiveClient([_response(), _response()])).run_discovery(force=True)
    assert empty.status == "succeeded"
    assert empty.jobs_created == 0

    rate = await RemotiveRemoteJobDiscoveryService(db_session, client=FakeRemotiveClient([_response(reason="remotive_rate_limited"), _response(_job(id=3))])).run_discovery(force=True)
    assert rate.status == "failed"
    assert rate.reason == "remotive_discovery_rate_limited"
