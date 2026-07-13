from datetime import timezone

from app.discovery.sources.himalayas.models import (
    HimalayasJobPayload,
    parse_himalayas_jobs_response,
    parse_himalayas_timestamp,
)


MS_UPDATED = 1783910400000
MS_PUBLISHED = 1783824000000
MS_EXPIRY = 1786416000000


def official_payload(**overrides):
    payload = {
        "comments": "API release notes",
        "updatedAt": MS_UPDATED,
        "offset": 0,
        "limit": 20,
        "totalCount": 1,
        "jobs": [
            {
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
                "pubDate": MS_PUBLISHED,
                "expiryDate": MS_EXPIRY,
                "applicationLink": "https://himalayas.app/companies/example-ai/jobs/junior-ai-engineer",
                "guid": "example-ai-junior-ai-engineer",
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_himalayas_models_map_official_camel_case_contract():
    response = parse_himalayas_jobs_response(official_payload())

    assert response.reason is None
    assert response.total_count == 1
    assert response.updated_at.tzinfo == timezone.utc
    assert response.jobs[0].company_name == "Example AI"
    assert response.jobs[0].published_at.tzinfo == timezone.utc
    assert response.jobs[0].expiry_at.tzinfo == timezone.utc
    assert response.jobs[0].seniority == ["Entry-level"]


def test_timestamp_parser_accepts_ms_seconds_and_iso_and_rejects_bad_values():
    assert parse_himalayas_timestamp(MS_UPDATED).value.tzinfo == timezone.utc
    assert parse_himalayas_timestamp(str(MS_UPDATED)).value.tzinfo == timezone.utc
    assert parse_himalayas_timestamp(1783910400).value.tzinfo == timezone.utc
    assert parse_himalayas_timestamp("2026-07-13T00:00:00Z").value.tzinfo == timezone.utc
    assert parse_himalayas_timestamp(-1).error == "timestamp_negative"
    assert parse_himalayas_timestamp("12345").error == "timestamp_invalid"


def test_seniority_and_legacy_fields_are_tolerant():
    single = HimalayasJobPayload.model_validate({"title": "AI Engineer", "seniority": "Entry-level"})
    multi = HimalayasJobPayload.model_validate({"title": "AI Engineer", "seniority": ["Mid-level", "Senior", "Mid-level"]})
    legacy = HimalayasJobPayload.model_validate({"category": "Python", "timezoneRestriction": "UTC+5:30"})

    assert single.seniority == ["Entry-level"]
    assert multi.seniority == ["Mid-level", "Senior"]
    assert legacy.categories == ["Python"]
    assert legacy.timezone_restrictions == ["UTC+5:30"]
    assert legacy.salary_period == "annual"


def test_malformed_job_is_isolated_from_valid_sibling():
    payload = official_payload()
    payload["jobs"] = [payload["jobs"][0], "not-a-job", {**payload["jobs"][0], "minSalary": "bad"}]

    response = parse_himalayas_jobs_response(payload)

    assert response.reason is None
    assert len(response.jobs) == 1
    assert response.malformed_records == 2
    assert response.validation_failures


def test_invalid_envelope_gets_safe_schema_diagnostics():
    response = parse_himalayas_jobs_response({"updatedAt": MS_UPDATED, "jobs": {}, "totalCount": 1}, status_code=200, response_size=42, content_type="application/json")

    assert response.reason == "himalayas_unexpected_schema"
    assert response.schema_diagnostics["top_level_keys"] == ["updatedAt", "jobs", "totalCount"]
    assert response.schema_diagnostics["field_types"]["jobs"] == "dict"
    assert "jobs" in response.schema_diagnostics["validation_paths"]
