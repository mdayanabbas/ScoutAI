import pytest
import httpx

from app.enrichment.ashby_public_job_parser import AshbyPublicJob
from app.enrichment.resolvers import AshbyJobBoardResolver
from app.models.discovery_candidate import DiscoveryCandidate
from app.utils.enums import (
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoverySource,
)

POSTING_ID = "2e718684-4f75-4a99-8d6b-3b6bd44e4228"


def _candidate(
    url: str,
    *,
    platform: str = "ashby",
    slug: str | None = None,
    title: str = "Supabase Is Hiring a Software Engineer",
    feed: str = "jobs",
):
    classification = {
        "platform": platform,
        "original_url": url,
        "external_url": url,
    }
    if slug is not None:
        classification["external_company_slug"] = slug
    return DiscoveryCandidate(
        discovery_run_id="run-1",
        source=DiscoverySource.HACKER_NEWS,
        source_identifier="hn:1",
        raw_name="Supabase",
        raw_description=title,
        normalized_name="Supabase",
        normalized_description=title,
        status=DiscoveryCandidateStatus.NORMALIZED,
        decision=DiscoveryDecision.DEFERRED,
        deferred_reason="requires_company_domain_enrichment",
        raw_payload={
            "type": "job",
            "feed": feed,
            "title": title,
            "url": url,
            "url_classification": classification,
        },
    )


def _job(
    *,
    title: str = "Software Engineer",
    team: str | None = "Engineering",
    description: str = "Email careers@supabase.com",
    posting_id: str = POSTING_ID,
):
    url = f"https://jobs.ashbyhq.com/supabase/{posting_id}"
    return AshbyPublicJob(
        title=title,
        location="Remote",
        secondary_locations=(),
        department="Engineering",
        team=team,
        is_listed=True,
        is_remote=True,
        workplace_type="Remote",
        description_plain=description,
        description_html=None,
        published_at=None,
        employment_type="FullTime",
        job_url=url,
        apply_url=f"{url}/application",
        compensation_summary=None,
        raw_posting_id=posting_id,
    )


def test_supports_posting_and_board_urls_and_rejects_other_candidates():
    resolver = AshbyJobBoardResolver()
    posting = _candidate(
        f"https://jobs.ashbyhq.com/supabase/{POSTING_ID}", slug="supabase"
    )
    board = _candidate("https://jobs.ashbyhq.com/lago", slug="lago")
    yc = _candidate(
        "https://www.ycombinator.com/companies/supabase/jobs/1",
        platform="ycombinator",
        slug="supabase",
    )
    show = _candidate(
        "https://jobs.ashbyhq.com/lago", slug="lago", feed="show"
    )
    show.raw_payload["type"] = "story"

    assert resolver.supports(posting)
    assert resolver.extract_board_slug(posting) == "supabase"
    assert resolver.extract_posting_id(posting) == POSTING_ID
    assert resolver.supports(board)
    assert resolver.extract_posting_id(board) is None
    assert not resolver.supports(yc)
    assert not resolver.supports(show)


def test_rejects_malformed_slug_and_path_traversal():
    resolver = AshbyJobBoardResolver()
    malformed = _candidate("https://jobs.ashbyhq.com/good", slug="../supabase")
    traversal = _candidate(
        "https://jobs.ashbyhq.com/%2e%2e/application", slug=None
    )

    assert resolver.extract_board_slug(malformed) is None
    assert resolver.extract_board_slug(traversal) is None


@pytest.mark.asyncio
async def test_fetches_official_json_with_compensation_and_filters_unlisted():
    def handler(request: httpx.Request):
        assert request.url.host == "api.ashbyhq.com"
        assert request.url.params["includeCompensation"] == "true"
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "jobs": [
                    {
                        "id": POSTING_ID,
                        "title": "Software Engineer",
                        "isListed": True,
                        "jobUrl": (
                            "https://jobs.ashbyhq.com/supabase/"
                            f"{POSTING_ID}"
                        ),
                    },
                    {"title": "Hidden", "isListed": False},
                ]
            },
        )

    resolver = AshbyJobBoardResolver(
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    result = await resolver.fetch_job_board("supabase")

    assert result.success
    assert result.status_code == 200
    assert [job.title for job in result.jobs] == ["Software Engineer"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (httpx.Response(404), "ashby_board_not_found"),
        (httpx.Response(429), "ashby_rate_limited"),
        (
            httpx.Response(200, headers={"content-type": "text/html"}, text="no"),
            "ashby_invalid_content_type",
        ),
        (
            httpx.Response(
                200,
                headers={"content-type": "application/json"},
                content=b"{bad",
            ),
            "ashby_invalid_json",
        ),
    ],
)
async def test_fetch_failure_reasons(response, reason):
    resolver = AshbyJobBoardResolver(
        max_retries=0,
        transport=httpx.MockTransport(lambda _request: response),
    )

    result = await resolver.fetch_job_board("supabase")

    assert not result.success
    assert result.reason == reason


@pytest.mark.asyncio
async def test_rejects_oversized_response_and_untrusted_redirect():
    oversized = AshbyJobBoardResolver(
        max_retries=0,
        max_response_bytes=4,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                headers={"content-type": "application/json"},
                content=b'{"jobs":[]}',
            )
        ),
    )
    redirected = AshbyJobBoardResolver(
        max_retries=0,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                302, headers={"location": "https://example.com/jobs"}
            )
        ),
    )

    assert (
        await oversized.fetch_job_board("supabase")
    ).reason == "ashby_response_too_large"
    assert (
        await redirected.fetch_job_board("supabase")
    ).reason == "ashby_fetch_failed"


def test_exact_posting_id_match_and_wrong_id():
    resolver = AshbyJobBoardResolver()
    candidate = _candidate(
        f"https://jobs.ashbyhq.com/supabase/{POSTING_ID}", slug="supabase"
    )

    assert resolver.match_job(candidate, [_job()]).matched
    wrong = _candidate(
        "https://jobs.ashbyhq.com/supabase/"
        "11111111-1111-4111-8111-111111111111",
        slug="supabase",
    )
    assert resolver.match_job(wrong, [_job()]).reason == "ashby_job_not_found"


def test_board_signal_requires_one_unique_strong_match():
    resolver = AshbyJobBoardResolver()
    candidate = _candidate(
        "https://jobs.ashbyhq.com/lago",
        slug="lago",
        title="Lago Is Hiring for Our GTM Team",
    )
    gtm = _job(title="Account Executive", team="GTM")
    engineering = _job(title="Backend Engineer", team="Engineering")

    assert resolver.match_job(candidate, [gtm, engineering]).job == gtm
    second_gtm = _job(title="Growth Lead", team="GTM")
    assert (
        resolver.match_job(candidate, [gtm, second_gtm]).reason
        == "ambiguous_ashby_job_matches"
    )


@pytest.mark.asyncio
async def test_domain_proposals_are_strong_and_never_guessed_from_slug():
    resolver = AshbyJobBoardResolver()
    candidate = _candidate(
        f"https://jobs.ashbyhq.com/supabase/{POSTING_ID}", slug="supabase"
    )
    board = type(
        "Board",
        (),
        {
            "success": True,
            "board_slug": "supabase",
            "status_code": 200,
            "jobs": (_job(description=(
                "Visit https://supabase.com or email jobs@supabase.com. "
                "Ignore me@gmail.com and https://github.com/supabase."
            )),),
            "reason": None,
        },
    )()

    result = await resolver.resolve(candidate, board)

    assert result.resolved
    assert result.proposed_domain == "supabase.com"
    assert {item.domain for item in result.domain_proposals} == {"supabase.com"}

    missing = type(
        "Board",
        (),
        {
            "success": True,
            "board_slug": "supabase",
            "status_code": 200,
            "jobs": (_job(description="Build great databases."),),
            "reason": None,
        },
    )()
    unresolved = await resolver.resolve(candidate, missing)
    assert not unresolved.resolved
    assert unresolved.reason == "ashby_company_domain_missing"
