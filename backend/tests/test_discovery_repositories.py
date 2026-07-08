from app.models.discovery_candidate import DiscoveryCandidate
from app.models.discovery_evidence import DiscoveryEvidence
from app.models.discovery_run import DiscoveryRun
from app.repositories.discovery_candidate_repository import DiscoveryCandidateRepository
from app.repositories.discovery_evidence_repository import DiscoveryEvidenceRepository
from app.repositories.discovery_run_repository import DiscoveryRunRepository
from app.utils.enums import DiscoveryCandidateStatus, DiscoveryRunStatus, DiscoverySource


def test_discovery_repositories_create_and_list_records(db_session):
    run_repo = DiscoveryRunRepository(db_session)
    candidate_repo = DiscoveryCandidateRepository(db_session)
    evidence_repo = DiscoveryEvidenceRepository(db_session)

    run = run_repo.create_run(
        DiscoveryRun(
            source=DiscoverySource.MANUAL,
            status=DiscoveryRunStatus.PENDING,
            candidates_found=0,
            candidates_normalized=0,
            companies_created=0,
            companies_matched=0,
            candidates_rejected=0,
            candidates_failed=0,
        )
    )
    candidate = candidate_repo.create_candidate(
        DiscoveryCandidate(
            discovery_run_id=run.id,
            source=DiscoverySource.MANUAL,
            source_identifier="manual-acme",
            raw_name="Acme AI",
            status=DiscoveryCandidateStatus.DISCOVERED,
        )
    )
    evidence_repo.create_evidence(
        DiscoveryEvidence(
            discovery_candidate_id=candidate.id,
            evidence_type="source_listing",
            source_url="https://example.com/acme",
        )
    )

    assert run_repo.count_runs() == 1
    assert candidate_repo.count_by_run(run.id) == 1
    assert len(evidence_repo.list_by_candidate(candidate.id)) == 1
