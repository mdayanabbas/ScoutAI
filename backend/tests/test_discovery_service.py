import pytest

from app.discovery.adapters.manual import ManualDiscoveryAdapter
from app.schemas.discovery import ManualDiscoveryRequest, RawStartupCandidate
from app.services.company_service import CompanyService
from app.services.discovery_service import DiscoveryService
from app.utils.enums import DiscoveryCandidateStatus, DiscoveryDecision, DiscoveryRunStatus


def _candidate(
    source_identifier: str,
    name: str = "Acme AI",
    website_url: str | None = "https://www.acme.ai/",
) -> RawStartupCandidate:
    return RawStartupCandidate(
        source_identifier=source_identifier,
        name=name,
        website_url=website_url,
        description="AI workflow automation.",
        evidence=[
            {
                "evidence_type": "source_listing",
                "source_url": f"https://example.com/{source_identifier}",
                "title": name,
                "excerpt": "Startup listing.",
            }
        ],
        raw_payload={"source_note": "manual"},
    )


@pytest.mark.asyncio
async def test_manual_discovery_creates_company_and_persists_evidence(db_session):
    service = DiscoveryService(db_session)

    result = await service.run_manual_discovery(
        ManualDiscoveryRequest(candidates=[_candidate("manual-acme")])
    )

    assert result.run.status == DiscoveryRunStatus.SUCCESS
    assert result.run.companies_created == 1
    candidate = result.candidates[0]
    assert candidate.status == DiscoveryCandidateStatus.INGESTED
    assert candidate.decision == DiscoveryDecision.CREATED_COMPANY
    assert candidate.normalized_domain == "acme.ai"
    assert candidate.raw_payload == {"source_note": "manual"}
    assert candidate.evidence[0].source_url == "https://example.com/manual-acme"


@pytest.mark.asyncio
async def test_manual_discovery_matches_existing_company_domain(db_session):
    CompanyService(db_session).create_company(
        {"name": "Acme Existing", "website_url": "https://acme.ai"}
    )

    result = await DiscoveryService(db_session).run_manual_discovery(
        ManualDiscoveryRequest(candidates=[_candidate("manual-acme")])
    )

    assert result.run.status == DiscoveryRunStatus.SUCCESS
    assert result.run.companies_matched == 1
    assert result.run.companies_created == 0
    assert result.candidates[0].decision == DiscoveryDecision.MATCHED_EXISTING_COMPANY


@pytest.mark.asyncio
async def test_duplicate_domain_within_same_run_is_detected(db_session):
    result = await DiscoveryService(db_session).run_manual_discovery(
        ManualDiscoveryRequest(
            candidates=[
                _candidate("manual-acme-1"),
                _candidate("manual-acme-2", name="Acme Duplicate"),
            ]
        )
    )

    assert result.run.status == DiscoveryRunStatus.PARTIAL_SUCCESS
    assert result.run.companies_created == 1
    assert result.run.candidates_rejected == 1
    duplicate = [c for c in result.candidates if c.status == "duplicate"][0]
    assert duplicate.rejection_reason == "duplicate_candidate_in_run"


@pytest.mark.asyncio
async def test_mixed_valid_and_invalid_candidates_produce_partial_success(db_session):
    result = await DiscoveryService(db_session).run_manual_discovery(
        ManualDiscoveryRequest(
            candidates=[
                _candidate("manual-acme"),
                _candidate("manual-bad", name="Bad", website_url="not a domain"),
            ]
        )
    )

    assert result.run.status == DiscoveryRunStatus.PARTIAL_SUCCESS
    assert result.run.companies_created == 1
    assert result.run.candidates_rejected == 1


@pytest.mark.asyncio
async def test_complete_adapter_failure_marks_run_failed(db_session, monkeypatch):
    async def fail_discover(self, request):
        raise RuntimeError("adapter unavailable")

    monkeypatch.setattr(ManualDiscoveryAdapter, "discover", fail_discover)

    result = await DiscoveryService(db_session).run_manual_discovery(
        ManualDiscoveryRequest(candidates=[_candidate("manual-acme")])
    )

    assert result.run.status == DiscoveryRunStatus.FAILED
    assert result.run.error_message == "adapter unavailable"


@pytest.mark.asyncio
async def test_candidate_without_domain_is_rejected_for_ingestion(db_session):
    result = await DiscoveryService(db_session).run_manual_discovery(
        ManualDiscoveryRequest(candidates=[_candidate("manual-no-site", website_url=None)])
    )

    assert result.run.status == DiscoveryRunStatus.FAILED
    assert result.candidates[0].status == DiscoveryCandidateStatus.REJECTED
    assert result.candidates[0].rejection_reason == "missing_normalized_domain"
