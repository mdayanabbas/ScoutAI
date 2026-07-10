import app.models  # noqa: F401
from app.db.base import Base
from app.models import CompanyEnrichmentAttempt, DiscoveryCandidate, DiscoveryRun
from app.repositories.company_enrichment_attempt_repository import (
    CompanyEnrichmentAttemptRepository,
)
from app.utils.enums import (
    CompanyEnrichmentResolver,
    CompanyEnrichmentStatus,
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoveryRunStatus,
    DiscoverySource,
)


def test_company_enrichment_attempt_model_imports():
    assert CompanyEnrichmentAttempt


def test_metadata_contains_company_enrichment_attempts():
    assert "company_enrichment_attempts" in Base.metadata.tables


def test_company_enrichment_resolver_column_supports_current_values():
    table = Base.metadata.tables["company_enrichment_attempts"]
    resolver = table.columns["resolver"]

    assert resolver.type.length >= 64
    assert all(len(item.value) <= resolver.type.length for item in CompanyEnrichmentResolver)


def _candidate(db_session):
    run = DiscoveryRun(
        source=DiscoverySource.HACKER_NEWS,
        status=DiscoveryRunStatus.SUCCESS,
        candidates_found=1,
        candidates_normalized=1,
        companies_created=0,
        companies_matched=0,
        candidates_deferred=1,
        candidates_rejected=0,
        candidates_failed=0,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    candidate = DiscoveryCandidate(
        discovery_run_id=run.id,
        source=DiscoverySource.HACKER_NEWS,
        source_identifier="hn:resolver-length",
        raw_name="Resolver Length",
        raw_description="Resolver Length is hiring",
        normalized_name="Resolver Length",
        normalized_description="Resolver Length is hiring",
        status=DiscoveryCandidateStatus.NORMALIZED,
        decision=DiscoveryDecision.DEFERRED,
        deferred_reason="requires_company_domain_enrichment",
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate


def test_long_company_enrichment_resolver_values_can_be_inserted(db_session):
    candidate = _candidate(db_session)
    repo = CompanyEnrichmentAttemptRepository(db_session)

    for resolver in (
        CompanyEnrichmentResolver.OTHER,
        CompanyEnrichmentResolver.YCOMBINATOR_PROFILE,
        CompanyEnrichmentResolver.ASHBY_PUBLIC_JOB_BOARD,
        CompanyEnrichmentResolver.WEB_SEARCH_COMPANY_IDENTITY,
    ):
        attempt = repo.create_attempt(
            CompanyEnrichmentAttempt(
                discovery_candidate_id=candidate.id,
                status=CompanyEnrichmentStatus.PENDING,
                resolver=resolver,
                reason=f"test {resolver.value}",
            )
        )

        assert attempt.resolver == resolver
        assert repo.get_by_id(attempt.id).resolver == resolver
