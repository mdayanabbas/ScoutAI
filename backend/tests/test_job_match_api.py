import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.models.company import Company
from app.models.job import Job
from app.models.job_matching_profile import JobMatchingProfile
from app.models.user_profile import UserProfile
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import UserProfileRepository
from app.utils.enums import JobStatus


@pytest.fixture
async def match_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _setup(db_session):
    user = UserProfileRepository(db_session).create_profile(UserProfile(display_name="Abbas"))
    profile = JobMatchingProfile(
        user_profile_id=user.id,
        target_titles_json=["Software Engineer"],
        accepted_employment_types_json=["full_time"],
        preferred_countries_json=["India"],
        work_authorization_countries_json=["India"],
        willing_to_relocate=False,
    )
    db_session.add(profile)
    db_session.commit()
    company = CompanyRepository(db_session).create_company(Company(name="API Match Co", normalized_domain="api-match.example"))
    good = JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            title="Software Engineer",
            normalized_title="software engineer",
            role_category="software_engineer",
            description="Remote worldwide. Build APIs.",
            remote_type="remote_worldwide",
            experience_min=1,
            employment_type="full_time",
            job_url="https://api-match.example/jobs/software",
            status=JobStatus.ACTIVE,
            enrichment_status="enriched",
        )
    )
    bad = JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            title="Senior Electrical Engineer",
            normalized_title="senior electrical engineer",
            role_category="other",
            description="Onsite role.",
            remote_type="onsite",
            experience_min=6,
            employment_type="full_time",
            job_url="https://api-match.example/jobs/electrical",
            status=JobStatus.ACTIVE,
        )
    )
    return good, bad


@pytest.mark.asyncio
async def test_job_match_api_scores_lists_and_gets(db_session, match_api_client):
    good, bad = _setup(db_session)

    missing = await match_api_client.get(f"/api/v1/job-matches/{good.id}")
    scored = await match_api_client.post("/api/v1/job-matches/score", json={"job_ids": [good.id, bad.id], "force": True})
    listed = await match_api_client.get("/api/v1/job-matches")
    included = await match_api_client.get("/api/v1/job-matches", params={"include_unsuitable": "true"})
    one = await match_api_client.get(f"/api/v1/job-matches/{good.id}")

    assert missing.status_code == 404
    assert scored.status_code == 200
    assert scored.json()["jobs_scored"] == 2
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1
    assert "description" not in listed.text
    assert included.status_code == 200
    assert len(included.json()["items"]) == 2
    assert one.status_code == 200
    assert one.json()["job_id"] == good.id
