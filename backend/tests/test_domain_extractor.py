from app.enrichment.domain_extractor import (
    clean_enrichment_text,
    collect_candidate_domain_proposals,
    extract_email_domains_from_text,
    extract_urls_from_text,
    is_allowed_company_domain,
    is_valid_hostname,
    normalize_domain_proposal,
)
from app.models.discovery_candidate import DiscoveryCandidate
from app.utils.enums import DiscoveryCandidateStatus, DiscoveryDecision, DiscoverySource


def test_extracts_business_email_domain():
    assert extract_email_domains_from_text("Apply at jobs@getdexter.co") == [
        "getdexter.co"
    ]


def test_ignores_blocked_domains():
    assert is_allowed_company_domain("gmail.com") is False
    assert is_allowed_company_domain("jobs.ashbyhq.com") is False
    assert is_allowed_company_domain("ycombinator.com") is False
    assert is_allowed_company_domain("github.com") is False
    assert is_allowed_company_domain("microsoft.github.io") is False


def test_extracts_first_party_url():
    assert extract_urls_from_text("See https://getdexter.co/jobs")[0] == (
        "https://getdexter.co/jobs"
    )


def test_decodes_html_encoded_slash_url_before_extraction():
    urls = extract_urls_from_text(
        "See https:&#x2F;&#x2F;www.ycombinator.com&#x2F;companies&#x2F;dexter"
    )

    assert urls == ["https://www.ycombinator.com/companies/dexter"]
    assert normalize_domain_proposal(urls[0]) == "ycombinator.com"
    assert is_allowed_company_domain("ycombinator.com") is False


def test_decodes_common_html_entities():
    text = clean_enrichment_text(
        "<p>Go to https:&#47;&#47;example.com?a=1&amp;b=2 &quot;now&quot;</p>"
    )

    assert "https://example.com?a=1&b=2" in text
    assert '"now"' in text


def test_invalid_hostnames_are_rejected():
    assert is_valid_hostname("ycombinator.com&") is False
    assert is_valid_hostname("example.com;") is False
    assert is_valid_hostname("exa mple.com") is False
    assert is_valid_hostname("example&#x2F;.com") is False
    assert is_valid_hostname("example..com") is False
    assert is_valid_hostname(".example.com") is False
    assert is_valid_hostname("good-domain.example") is True


def test_decoded_platform_urls_are_blocked():
    assert is_allowed_company_domain(
        normalize_domain_proposal("https:&#x2F;&#x2F;www.ycombinator.com&#x2F;companies")
    ) is False
    assert is_allowed_company_domain(
        normalize_domain_proposal("https:&#x2F;&#x2F;jobs.ashbyhq.com&#x2F;lago")
    ) is False
    assert is_allowed_company_domain(
        normalize_domain_proposal("https:&#x2F;&#x2F;github.com&#x2F;acme&#x2F;repo")
    ) is False
    assert is_allowed_company_domain("microsoft.github.io") is False


def test_collect_candidate_proposals_ignores_encoded_yc_url():
    candidate = DiscoveryCandidate(
        discovery_run_id="run",
        source=DiscoverySource.HACKER_NEWS,
        source_identifier="hn:1",
        raw_name="Dexter",
        raw_description=(
            "Apply at jobs@getdexter.co or see "
            "https:&#x2F;&#x2F;www.ycombinator.com&#x2F;companies&#x2F;dexter"
        ),
        status=DiscoveryCandidateStatus.NORMALIZED,
        decision=DiscoveryDecision.DEFERRED,
    )
    candidate.evidence = []

    proposals = collect_candidate_domain_proposals(candidate)

    assert [proposal.domain for proposal in proposals] == ["getdexter.co"]
