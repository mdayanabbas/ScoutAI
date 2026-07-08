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


def test_hiring_language_with_first_party_domain_is_valid():
    raw = RawStartupCandidate(
        source_identifier="hn:123",
        name="Acme AI",
        website_url="https://acme.ai/careers",
        description="Acme AI is hiring backend engineers",
        raw_payload={
            "feed": "jobs",
            "type": "job",
            "url_classification": {
                "url_type": "first_party",
                "original_url": "https://acme.ai/careers",
                "first_party_url": "https://acme.ai/careers",
                "is_first_party_company_domain": True,
            },
        },
    )

    result = validate_candidate(raw, normalize_candidate(raw))

    assert result.valid is True


def test_hiring_language_with_ashby_slug_is_valid():
    raw = RawStartupCandidate(
        source_identifier="hn:124",
        name="Lago",
        description="Lago is hiring engineers",
        raw_payload={
            "feed": "jobs",
            "type": "job",
            "url_classification": {
                "url_type": "ashby_job",
                "platform": "ashby",
                "external_company_slug": "lago",
                "external_url": "https://jobs.ashbyhq.com/lago",
            },
        },
    )

    result = validate_candidate(raw, normalize_candidate(raw))

    assert result.valid is True


def test_hiring_language_with_reliable_company_name_is_valid():
    raw = RawStartupCandidate(
        source_identifier="hn:125",
        name="TinyAgent",
        description="TinyAgent is hiring engineers",
        raw_payload={"feed": "jobs", "type": "job"},
    )

    result = validate_candidate(raw, normalize_candidate(raw))

    assert result.valid is True


def test_generic_stealth_job_without_identity_is_rejected():
    raw = RawStartupCandidate(
        source_identifier="hn:126",
        name="Stealth startup",
        description="Stealth startup is hiring engineers",
        raw_payload={"feed": "jobs", "type": "job"},
    )

    result = validate_candidate(raw, normalize_candidate(raw))

    assert result.valid is False
    assert result.reason == "job_post_without_company_identity"
