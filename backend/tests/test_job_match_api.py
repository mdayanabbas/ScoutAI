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
        target_titles_json=["Software Engineer", "AI Engineer", "ML Engineer"],
        target_role_categories_json=["software_engineer", "ai_engineer", "ml_engineer"],
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


def _create_match_job(db_session, company, **kwargs):
    values = {
        "company_id": company.id,
        "title": "Software Engineer",
        "normalized_title": "software engineer",
        "role_category": "software_engineer",
        "description": "Remote worldwide. Build APIs.",
        "remote_type": "remote_worldwide",
        "experience_min": 1,
        "employment_type": "full_time",
        "job_url": f"https://{company.normalized_domain}/jobs/{abs(hash(str(kwargs))) % 100000}",
        "status": JobStatus.ACTIVE,
        "enrichment_status": "enriched",
    }
    values.update(kwargs)
    return JobRepository(db_session).create_job(Job(**values))


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


@pytest.mark.asyncio
async def test_default_recommendations_exclude_invalid_onsite_and_unknown_remote(db_session, match_api_client):
    _setup(db_session)
    company = CompanyRepository(db_session).create_company(Company(name="Recommendation Co", normalized_domain="recommendation.example"))
    worldwide = _create_match_job(db_session, company, title="AI Engineer", role_category="ai_engineer")
    india = _create_match_job(
        db_session,
        company,
        title="ML Engineer",
        role_category="ml_engineer",
        description="Remote in India. Build models.",
        remote_type="unknown",
        job_url="https://recommendation.example/jobs/ml",
    )
    wildcard = _create_match_job(
        db_session,
        company,
        title="Software Engineer",
        location="San Francisco",
        description="Build developer tools.",
        remote_type="unknown",
        job_url="https://recommendation.example/jobs/wildcard",
    )
    acme = _create_match_job(
        db_session,
        company,
        title="Software Engineer",
        job_url="bjasvhcjhv",
        apply_url=None,
    )
    nox = _create_match_job(
        db_session,
        company,
        title="Software Engineer",
        location="Detroit",
        description="This role is full time, in person in Detroit.",
        remote_type="unknown",
        job_url="https://recommendation.example/jobs/nox",
    )

    scored = await match_api_client.post(
        "/api/v1/job-matches/score",
        json={"job_ids": [worldwide.id, india.id, wildcard.id, acme.id, nox.id], "force": True},
    )
    default_list = await match_api_client.get("/api/v1/job-matches")
    with_unknown = await match_api_client.get("/api/v1/job-matches", params={"include_remote_unknown": "true"})

    assert scored.status_code == 200
    assert all(item["reason"] for item in scored.json()["results"] if item["status"] == "scored")
    default_ids = [item["job_id"] for item in default_list.json()["items"]]
    assert worldwide.id in default_ids
    assert india.id in default_ids
    assert wildcard.id not in default_ids
    assert acme.id not in default_ids
    assert nox.id not in default_ids
    assert default_list.json()["items"][0]["valid_job_url"] is True
    unknown_ids = [item["job_id"] for item in with_unknown.json()["items"]]
    assert wildcard.id in unknown_ids
    assert unknown_ids.index(wildcard.id) > unknown_ids.index(worldwide.id)
