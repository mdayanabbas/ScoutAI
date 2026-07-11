from dataclasses import dataclass, field
from uuid import uuid4

import pytest

from app.jobs.enrichment.providers.first_party_job_client import FirstPartyJobPageResponse
from app.models.company import Company
from app.models.discovery_candidate import DiscoveryCandidate
from app.models.discovery_run import DiscoveryRun
from app.models.job import Job
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_board_expansion_link_repository import JobBoardExpansionLinkRepository
from app.repositories.job_discovery_link_repository import JobDiscoveryLinkRepository
from app.repositories.job_enrichment_attempt_repository import JobEnrichmentAttemptRepository
from app.repositories.job_repository import JobRepository
from app.services.first_party_listing_expansion_service import FirstPartyListingExpansionService
from app.utils.enums import (
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoveryRunStatus,
    DiscoverySource,
    JobStatus,
)


@dataclass
class FakeClient:
    pages: dict[str, FirstPartyJobPageResponse]
    fetched: list[str] = field(default_factory=list)

    async def fetch_job_page(self, url: str, *, company_domain: str):
        self.fetched.append(url)
        return self.pages[url]


def response(url: str, html: str | None = None, reason: str | None = None):
    return FirstPartyJobPageResponse(
        requested_url=url,
        final_url=url,
        normalized_domain="example.com",
        status_code=200 if not reason else None,
        content_type="text/html",
        html=html,
        response_size=len(html or ""),
        reason=reason,
    )


def parent(db_session, *, title="Open Roles", description="Example is hiring for open roles"):
    token = uuid4().hex[:8]
    company = CompanyRepository(db_session).create_company(
        Company(name=f"Example {token}", normalized_domain=f"example-{token}.com", website_url=f"https://example-{token}.com")
    )
    run = DiscoveryRun(
        source=DiscoverySource.HACKER_NEWS,
        status=DiscoveryRunStatus.SUCCESS,
        candidates_found=1,
        candidates_normalized=1,
        companies_created=1,
        companies_matched=0,
        candidates_deferred=0,
        candidates_rejected=0,
        candidates_failed=0,
    )
    db_session.add(run)
    db_session.commit()
    candidate = DiscoveryCandidate(
        discovery_run_id=run.id,
        source=DiscoverySource.HACKER_NEWS,
        source_identifier=f"hn:{token}",
        raw_name="Example",
        raw_description=description,
        normalized_name="Example",
        normalized_description=description,
        status=DiscoveryCandidateStatus.INGESTED,
        decision=DiscoveryDecision.CREATED_COMPANY,
        matched_company_id=company.id,
        raw_payload={"title": description},
    )
    db_session.add(candidate)
    db_session.commit()
    job = JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            discovery_candidate_id=candidate.id,
            title=title,
            normalized_title=title.lower(),
            description=description,
            job_url=f"https://example-{token}.com/careers",
            status=JobStatus.ACTIVE,
        )
    )
    JobDiscoveryLinkRepository(db_session).get_or_create_link(job.id, candidate.id)
    return job, candidate, company.normalized_domain


def listing_html(domain: str):
    return f"""
    <main>
      <article><h3>Backend Engineer</h3><p>Department: Engineering</p><a href="https://{domain}/careers/backend-engineer">Details</a></article>
      <article><h3>Account Executive</h3><p>Department: Sales</p><a href="https://{domain}/careers/account-executive">Details</a></article>
    </main>
    """


def detail_html(title: str):
    return f"""
    <main>
      <h1>{title}</h1>
      <p>Location: Remote</p>
      <p>Employment: Full-time</p>
      <p>{title} role building durable systems for customers. Python, React, and SQL experience preferred.</p>
    </main>
    """


@pytest.mark.asyncio
async def test_broad_listing_creates_children_links_and_deactivates_parent(db_session):
    job, candidate, domain = parent(db_session)
    client = FakeClient(
        {
            f"https://{domain}/careers": response(f"https://{domain}/careers", listing_html(domain)),
            f"https://{domain}/careers/backend-engineer": response(f"https://{domain}/careers/backend-engineer", detail_html("Backend Engineer")),
            f"https://{domain}/careers/account-executive": response(f"https://{domain}/careers/account-executive", detail_html("Account Executive")),
        }
    )

    result = await FirstPartyListingExpansionService(db_session, client=client).expand_listing(job.id)

    assert result.status == "succeeded"
    assert result.jobs_created == 2
    assert result.detail_pages_fetched == 2
    assert JobRepository(db_session).get_by_id(job.id).status == "inactive"
    assert JobDiscoveryLinkRepository(db_session).count_by_candidate_id(candidate.id) == 3
    assert len(JobBoardExpansionLinkRepository(db_session).list_children(job.id)) == 2
    attempt = JobEnrichmentAttemptRepository(db_session).get_by_id(result.attempt_id)
    assert attempt.status == "succeeded"
    assert "raw_html" not in str(attempt.evidence_json)
    assert "Backend Engineer role building" not in str(attempt.evidence_json)


@pytest.mark.asyncio
async def test_engineering_scope_selects_engineering_only_and_repeated_reuses(db_session):
    job, _, domain = parent(db_session, title="Engineering Team", description="Example engineering team roles")
    pages = {
        f"https://{domain}/careers": response(f"https://{domain}/careers", listing_html(domain)),
        f"https://{domain}/careers/backend-engineer": response(f"https://{domain}/careers/backend-engineer", detail_html("Backend Engineer")),
        f"https://{domain}/careers/account-executive": response(f"https://{domain}/careers/account-executive", detail_html("Account Executive")),
    }

    first = await FirstPartyListingExpansionService(db_session, client=FakeClient(pages)).expand_listing(job.id)
    JobRepository(db_session).update_job(JobRepository(db_session).get_by_id(job.id), {"status": JobStatus.ACTIVE})
    second = await FirstPartyListingExpansionService(db_session, client=FakeClient(pages)).expand_listing(job.id)

    assert first.jobs_created == 1
    assert first.children[0].title == "Backend Engineer"
    assert second.jobs_existing == 1
    assert JobRepository(db_session).count_jobs() == 2
    assert len(JobBoardExpansionLinkRepository(db_session).list_children(job.id)) == 1


@pytest.mark.asyncio
async def test_specific_unknown_exact_and_fetch_failure_states(db_session):
    specific, _, specific_domain = parent(db_session, title="Founding Backend Engineer", description="Founding Backend Engineer")
    specific_result = await FirstPartyListingExpansionService(
        db_session,
        client=FakeClient({f"https://{specific_domain}/careers": response(f"https://{specific_domain}/careers", listing_html(specific_domain))}),
    ).expand_listing(specific.id)
    assert specific_result.status == "skipped"
    assert specific_result.reason == "specific_role_should_use_job_enrichment"

    unknown, _, unknown_domain = parent(db_session, title="Example update", description="Company update")
    unknown_result = await FirstPartyListingExpansionService(
        db_session,
        client=FakeClient({f"https://{unknown_domain}/careers": response(f"https://{unknown_domain}/careers", listing_html(unknown_domain))}),
    ).expand_listing(unknown.id)
    assert unknown_result.status == "unresolved"
    assert JobRepository(db_session).get_by_id(unknown.id).status == "active"

    exact, _, exact_domain = parent(db_session)
    exact_html = detail_html("Backend Engineer")
    exact_result = await FirstPartyListingExpansionService(
        db_session,
        client=FakeClient({f"https://{exact_domain}/careers": response(f"https://{exact_domain}/careers", exact_html)}),
    ).expand_listing(exact.id)
    assert exact_result.status == "skipped"
    assert exact_result.reason == "exact_page_should_use_job_enrichment"

    failed, _, failed_domain = parent(db_session)
    failed_result = await FirstPartyListingExpansionService(
        db_session,
        client=FakeClient({f"https://{failed_domain}/careers": response(f"https://{failed_domain}/careers", reason="first_party_robots_disallowed")}),
    ).expand_listing(failed.id)
    assert failed_result.status == "failed"
    assert JobRepository(db_session).get_by_id(failed.id).status == "active"
