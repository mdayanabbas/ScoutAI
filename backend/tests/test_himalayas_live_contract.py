from datetime import timezone

import httpx
import pytest

from app.discovery.sources.himalayas.client import HimalayasRemoteJobsClient
from app.discovery.sources.himalayas.models import parse_himalayas_jobs_response
from app.discovery.sources.himalayas.query_planner import HimalayasTargetedQueryPlanner


def official_job(**overrides):
    job = {
        "title": "Junior AI Engineer",
        "excerpt": "Build production AI systems.",
        "companyName": "Example AI",
        "companySlug": "example-ai",
        "companyLogo": "https://example.com/logo.png",
        "employmentType": "Full Time",
        "minSalary": 70000,
        "maxSalary": 100000,
        "salaryPeriod": "annual",
        "seniority": ["Entry-level"],
        "currency": "USD",
        "locationRestrictions": [],
        "timezoneRestrictions": [],
        "categories": ["Artificial Intelligence", "Python"],
        "parentCategories": ["Engineering"],
        "description": "<p>Build production AI systems.</p>",
        "pubDate": 1783824000000,
        "expiryDate": 1786416000000,
        "applicationLink": "https://himalayas.app/companies/example-ai/jobs/junior-ai-engineer",
        "guid": "example-ai-junior-ai-engineer",
    }
    job.update(overrides)
    return job


def official_response(jobs=None, **overrides):
    payload = {
        "comments": "API release notes",
        "updatedAt": 1783910400000,
        "offset": 0,
        "limit": 20,
        "totalCount": len(jobs or []),
        "jobs": jobs if jobs is not None else [official_job()],
    }
    payload.update(overrides)
    return payload


def test_official_jobs_response_contract_parses_timestamps_and_lists():
    response = parse_himalayas_jobs_response(official_response())

    assert response.reason is None
    assert response.updated_at.tzinfo == timezone.utc
    assert response.jobs[0].published_at.tzinfo == timezone.utc
    assert response.jobs[0].expiry_at.tzinfo == timezone.utc
    assert response.jobs[0].seniority == ["Entry-level"]
    assert response.jobs[0].location_restrictions == []
    assert response.jobs[0].timezone_restrictions == []


def test_legacy_optional_fields_are_tolerated():
    job = official_job(
        companySlug=None,
        companyLogo=None,
        currency=None,
        minSalary=None,
        maxSalary=None,
        salaryPeriod=None,
        excerpt=None,
        description=None,
        expiryDate=None,
    )
    job.pop("categories")
    job.pop("parentCategories")
    job.pop("timezoneRestrictions")
    job.pop("locationRestrictions")

    response = parse_himalayas_jobs_response(official_response([job]))

    assert response.reason is None
    assert len(response.jobs) == 1
    assert response.jobs[0].salary_period == "annual"
    assert response.jobs[0].location_restrictions is None
    assert response.jobs[0].categories == []


def test_valid_sibling_survives_malformed_job_and_diagnostics_are_safe():
    response = parse_himalayas_jobs_response(
        official_response([official_job(), "bad"], totalCount=2),
        status_code=200,
        response_size=123,
        content_type="application/json",
        provider_request_id="req-1",
    )

    assert len(response.jobs) == 1
    assert response.malformed_records == 1
    assert response.validation_failures[0]["paths"] == ["jobs.1"]

    invalid = parse_himalayas_jobs_response({"data": {"jobs": []}}, status_code=200, response_size=20, content_type="application/json")
    assert invalid.reason == "himalayas_unexpected_schema"
    assert "data" in invalid.schema_diagnostics["top_level_keys"]
    assert "description" not in invalid.schema_diagnostics


def test_max_queries_caps_actual_passes():
    profile = type("Profile", (), {"target_titles_json": ["AI Engineer", "ML Engineer", "SWE"], "target_role_categories_json": []})()

    assert len(HimalayasTargetedQueryPlanner().build_plan(profile, max_queries=1).passes) == 1
    assert len(HimalayasTargetedQueryPlanner().build_plan(profile, max_queries=10).passes) <= 10


@pytest.mark.asyncio
async def test_client_handles_repeated_page_shape_with_official_fixture():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json=official_response())

    response = await HimalayasRemoteJobsClient(transport=httpx.MockTransport(handler)).search_jobs(query="AI Engineer", page=1)

    assert response.reason is None
    assert response.jobs[0].guid == "example-ai-junior-ai-engineer"
