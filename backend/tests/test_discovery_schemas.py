from app.schemas.discovery import (
    DiscoveryEvidenceInput,
    ManualDiscoveryRequest,
    RawStartupCandidate,
)


def test_manual_discovery_request_defaults():
    request = ManualDiscoveryRequest(
        candidates=[
            RawStartupCandidate(
                source_identifier="manual-acme",
                name="Acme AI",
                website_url="https://acme.ai",
            )
        ]
    )

    assert request.metadata is None
    assert request.candidates[0].evidence == []


def test_discovery_evidence_accepts_metadata_field():
    evidence = DiscoveryEvidenceInput(
        evidence_type="source_listing",
        source_url="https://example.com/acme",
        metadata={"rank": 1},
    )

    assert evidence.metadata == {"rank": 1}
