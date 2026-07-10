import httpx
import pytest

from app.jobs.enrichment.providers.first_party_job_client import FirstPartyJobClient


@pytest.mark.asyncio
async def test_client_accepts_company_domain_www_and_careers_subdomain():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<h1>Backend Engineer</h1>")

    client = FirstPartyJobClient(respect_robots=False, transport=httpx.MockTransport(handler))

    assert (await client.fetch_job_page("https://example.com/jobs/backend", company_domain="example.com")).reason is None
    assert (await client.fetch_job_page("https://www.example.com/jobs/backend", company_domain="example.com")).reason is None
    assert (await client.fetch_job_page("https://careers.example.com/openings/123", company_domain="example.com")).reason is None
    assert len(seen) == 3


@pytest.mark.asyncio
async def test_client_rejects_unsafe_or_unrelated_urls_without_fetch():
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200)

    client = FirstPartyJobClient(respect_robots=False, transport=httpx.MockTransport(handler))

    assert (await client.fetch_job_page("https://example.com.attacker.com/jobs", company_domain="example.com")).reason == "first_party_unsafe_host"
    assert (await client.fetch_job_page("https://example-careers.com/jobs", company_domain="example.com")).reason == "first_party_unsafe_host"
    assert (await client.fetch_job_page("http://localhost/jobs", company_domain="example.com")).reason == "first_party_unsafe_host"
    assert (await client.fetch_job_page("https://user:pass@example.com/jobs", company_domain="example.com")).reason == "first_party_unsafe_host"
    assert (await client.fetch_job_page("mailto:test@example.com", company_domain="example.com")).reason == "first_party_unsafe_host"
    assert called is False


@pytest.mark.asyncio
async def test_client_redirects_content_type_size_status_and_timeout():
    async def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow", request=request)

    same_redirect_calls = 0

    def same_redirect(request: httpx.Request) -> httpx.Response:
        nonlocal same_redirect_calls
        same_redirect_calls += 1
        if same_redirect_calls == 1:
            return httpx.Response(302, headers={"location": "https://careers.example.com/jobs/backend"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<h1>Backend Engineer</h1>")

    cross_redirect = FirstPartyJobClient(respect_robots=False, transport=httpx.MockTransport(lambda request: httpx.Response(302, headers={"location": "https://evil.example.net/job"})))
    wrong_type = FirstPartyJobClient(respect_robots=False, transport=httpx.MockTransport(lambda request: httpx.Response(200, headers={"content-type": "application/json"}, json={})))
    oversized = FirstPartyJobClient(respect_robots=False, max_response_bytes=4, transport=httpx.MockTransport(lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text="too large")))
    timeout = FirstPartyJobClient(respect_robots=False, max_retries=0, transport=httpx.MockTransport(timeout_handler))
    not_found = FirstPartyJobClient(respect_robots=False, transport=httpx.MockTransport(lambda request: httpx.Response(404, headers={"content-type": "text/html"})))
    gone = FirstPartyJobClient(respect_robots=False, transport=httpx.MockTransport(lambda request: httpx.Response(410, headers={"content-type": "text/html"})))
    forbidden = FirstPartyJobClient(respect_robots=False, transport=httpx.MockTransport(lambda request: httpx.Response(403, headers={"content-type": "text/html"})))
    limited = FirstPartyJobClient(respect_robots=False, transport=httpx.MockTransport(lambda request: httpx.Response(429, headers={"content-type": "text/html"})))

    assert (await FirstPartyJobClient(respect_robots=False, transport=httpx.MockTransport(same_redirect)).fetch_job_page("https://example.com/jobs/backend", company_domain="example.com")).reason is None
    assert (await cross_redirect.fetch_job_page("https://example.com/jobs/backend", company_domain="example.com")).reason == "first_party_redirect_rejected"
    assert (await wrong_type.fetch_job_page("https://example.com/jobs/backend", company_domain="example.com")).reason == "first_party_unexpected_content_type"
    assert (await oversized.fetch_job_page("https://example.com/jobs/backend", company_domain="example.com")).reason == "first_party_response_too_large"
    assert (await timeout.fetch_job_page("https://example.com/jobs/backend", company_domain="example.com")).reason == "first_party_request_timeout"
    assert (await not_found.fetch_job_page("https://example.com/jobs/backend", company_domain="example.com")).reason == "first_party_page_not_found"
    assert (await gone.fetch_job_page("https://example.com/jobs/backend", company_domain="example.com")).reason == "first_party_page_gone"
    assert (await forbidden.fetch_job_page("https://example.com/jobs/backend", company_domain="example.com")).reason == "first_party_page_forbidden"
    assert (await limited.fetch_job_page("https://example.com/jobs/backend", company_domain="example.com")).reason == "first_party_rate_limited"


@pytest.mark.asyncio
async def test_client_respects_robots_txt():
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, headers={"content-type": "text/plain"}, text="User-agent: ScoutAI\nDisallow: /private")
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<h1>Backend Engineer</h1>")

    client = FirstPartyJobClient(transport=httpx.MockTransport(handler))

    allowed = await client.fetch_job_page("https://example.com/jobs/backend", company_domain="example.com")
    disallowed = await client.fetch_job_page("https://example.com/private/backend", company_domain="example.com")

    assert allowed.reason is None
    assert disallowed.reason == "first_party_robots_disallowed"
    assert requests.count("/robots.txt") == 1

