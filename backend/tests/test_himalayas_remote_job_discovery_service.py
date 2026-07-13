from types import SimpleNamespace

import pytest

from app.discovery.sources.himalayas.models import HimalayasJobPayload, HimalayasSearchResponse
from app.models.user_profile import UserProfile
from app.models.job_matching_profile import JobMatchingProfile
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import UserProfileRepository
from app.services.himalayas_remote_job_discovery_service import HimalayasRemoteJobDiscoveryService


class FakeHimalayasClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def search_jobs(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0) if self.responses else HimalayasSearchResponse(jobs=[])


def _profile(db_session):
    user = UserProfileRepository(db_session).create_profile(UserProfile(display_name="Abbas"))
    profile = JobMatchingProfile(
        user_profile_id=user.id,
        target_titles_json=["AI Engineer"],
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


def _job(guid="job-1", title="AI Engineer", restrictions=None):
    return HimalayasJobPayload.model_validate(
        {
            "title": title,
            "companyName": "Remote AI Co",
            "companySlug": "remote-ai",
            "employmentType": "Full Time",
            "seniority": "Entry-level",
            "locationRestrictions": [] if restrictions is None else restrictions,
            "description": "Remote worldwide. Build LLM systems.",
            "applicationLink": f"https://himalayas.app/companies/remote-ai/jobs/{guid}",
            "guid": guid,
        }
    )


@pytest.mark.asyncio
async def test_service_creates_run_candidate_company_job_and_deduplicates(db_session, monkeypatch):
    _profile(db_session)
    monkeypatch.setattr("app.services.himalayas_remote_job_discovery_service.get_settings", lambda: SimpleNamespace(
        HIMALAYAS_DISCOVERY_ENABLED=True,
        HIMALAYAS_MAX_QUERIES_PER_RUN=1,
        HIMALAYAS_MAX_PAGES_PER_QUERY=1,
        HIMALAYAS_REQUEST_DELAY_MS=0,
        HIMALAYAS_DISCOVERY_COOLDOWN_HOURS=24,
        HIMALAYAS_MAX_JOBS_PER_RUN=100,
        HIMALAYAS_SCORE_AFTER_INGESTION=False,
        HIMALAYAS_STORE_REJECTED_CANDIDATES=True,
    ))
    response = HimalayasSearchResponse(jobs=[_job(), _job()])
    service = HimalayasRemoteJobDiscoveryService(db_session, client=FakeHimalayasClient([response, response]))

    result = await service.run_discovery(force=True, max_queries=1, max_pages_per_query=1, score_after_ingestion=False)

    assert result.status == "succeeded"
    assert result.unique_records == 1
    assert result.candidates_created == 1
    assert result.jobs_created == 1
    assert len(JobRepository(db_session).list_jobs()) == 1


@pytest.mark.asyncio
async def test_service_rejected_candidate_does_not_create_job(db_session, monkeypatch):
    _profile(db_session)
    monkeypatch.setattr("app.services.himalayas_remote_job_discovery_service.get_settings", lambda: SimpleNamespace(
        HIMALAYAS_DISCOVERY_ENABLED=True,
        HIMALAYAS_MAX_QUERIES_PER_RUN=1,
        HIMALAYAS_MAX_PAGES_PER_QUERY=1,
        HIMALAYAS_REQUEST_DELAY_MS=0,
        HIMALAYAS_DISCOVERY_COOLDOWN_HOURS=24,
        HIMALAYAS_MAX_JOBS_PER_RUN=100,
        HIMALAYAS_SCORE_AFTER_INGESTION=False,
        HIMALAYAS_STORE_REJECTED_CANDIDATES=True,
    ))
    response = HimalayasSearchResponse(jobs=[_job(guid="job-us", restrictions=[{"alpha2": "US", "name": "United States"}])])

    result = await HimalayasRemoteJobDiscoveryService(db_session, client=FakeHimalayasClient([response, response])).run_discovery(
        force=True,
        max_queries=1,
        max_pages_per_query=1,
        score_after_ingestion=False,
    )

    assert result.candidates_rejected == 1
    assert result.jobs_created == 0
    assert result.rejected_samples[0].rejection_reason == "rejected_country_restriction"
