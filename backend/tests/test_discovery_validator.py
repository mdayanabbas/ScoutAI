from app.discovery.normalizer import normalize_candidate
from app.discovery.validator import validate_candidate
from app.schemas.discovery import RawStartupCandidate


def test_invalid_candidate_is_rejected_for_bad_domain():
    raw = RawStartupCandidate(
        source_identifier="bad-url",
        name="Bad URL",
        website_url="not a domain",
    )

    result = validate_candidate(raw, normalize_candidate(raw))

    assert result.valid is False
    assert result.reason == "invalid_normalized_domain"


def test_candidate_without_website_can_pass_validation():
    raw = RawStartupCandidate(source_identifier="no-site", name="No Site AI")

    result = validate_candidate(raw, normalize_candidate(raw))

    assert result.valid is True
