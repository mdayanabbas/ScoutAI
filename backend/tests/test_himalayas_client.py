import httpx
import pytest

from app.discovery.sources.himalayas.client import HimalayasRemoteJobsClient


def official_payload():
    return {
        "comments": "API release notes",
        "updatedAt": 1783910400000,
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
                "pubDate": 1783824000000,
                "expiryDate": 1786416000000,
                "applicationLink": "https://himalayas.app/companies/example-ai/jobs/junior-ai-engineer",
                "guid": "example-ai-junior-ai-engineer",
            }
        ],
    }


@pytest.mark.asyncio
async def test_client_uses_official_endpoint_and_encodes_targeting_params():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"updatedAt": 1783910400000, "jobs": [], "offset": 0, "limit": 20, "totalCount": 0})

    client = HimalayasRemoteJobsClient(transport=httpx.MockTransport(handler))
    result = await client.search_jobs(
        query="AI Engineer",
        worldwide=True,
        country="IN",
        seniority=["junior", "entry-level"],
        employment_types=["Full Time", "Contractor"],
    )

    assert result.reason is None
    assert seen["url"].startswith("https://himalayas.app/jobs/api/search?")
    assert "q=AI+Engineer" in seen["url"]
    assert "worldwide=true" in seen["url"]
    assert "country=IN" in seen["url"]
    assert "seniority=junior%2Centry-level" in seen["url"]
    assert "employment_type=Full+Time%2CContractor" in seen["url"]


@pytest.mark.asyncio
async def test_client_handles_errors_without_raising():
    async def timeout_handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    timeout = await HimalayasRemoteJobsClient(transport=httpx.MockTransport(timeout_handler), max_retries=0).search_jobs(query="AI Engineer")
    assert timeout.reason == "himalayas_request_timeout"

    rate_limited = await HimalayasRemoteJobsClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(429, json={}))
    ).search_jobs(query="AI Engineer")
    assert rate_limited.reason == "himalayas_rate_limited"

    malformed = await HimalayasRemoteJobsClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, content=b"{", headers={"content-type": "application/json"}))
    ).search_jobs(query="AI Engineer")
    assert malformed.reason == "himalayas_invalid_json"


@pytest.mark.asyncio
async def test_client_contract_fixture_parses_ms_timestamps_and_seniority_list():
    client = HimalayasRemoteJobsClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=official_payload()))
    )

    response = await client.search_jobs(query="AI Engineer")

    assert response.reason is None
    assert response.total_count == 1
    assert len(response.jobs) == 1
    assert response.updated_at.tzinfo is not None
    assert response.jobs[0].published_at.tzinfo is not None
    assert response.jobs[0].expiry_at.tzinfo is not None
    assert response.jobs[0].seniority == ["Entry-level"]


@pytest.mark.asyncio
async def test_client_valid_envelope_with_malformed_record_keeps_valid_jobs():
    payload = official_payload()
    payload["jobs"] = [payload["jobs"][0], "bad-record"]

    response = await HimalayasRemoteJobsClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    ).search_jobs(query="AI Engineer")

    assert response.reason is None
    assert len(response.jobs) == 1
    assert response.malformed_records == 1


@pytest.mark.asyncio
async def test_client_rejects_unexpected_html_and_error_body_safely():
    html = await HimalayasRemoteJobsClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, content=b"<html></html>", headers={"content-type": "text/html"}))
    ).search_jobs(query="AI Engineer")
    assert html.reason == "himalayas_invalid_json"

    bad_request = await HimalayasRemoteJobsClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(400, json={"ok": False, "errors": "Invalid country"}))
    ).search_jobs(query="AI Engineer")
    assert bad_request.reason == "himalayas_bad_request"
