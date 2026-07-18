from app.jobs.job_source_detector import (
    JobSourceDetector,
    compare_registrable_domains,
    normalize_job_url,
    parse_ashby_careers_query_url,
    parse_ashby_job_url,
    parse_yc_job_url,
)
from app.utils.enums import JobSourceType


def test_generic_normalization_canonicalizes_safe_public_urls():
    normalized = normalize_job_url(
        " HTTPS://WWW.ExampleCareers.com:443/jobs//Founding-Engineer/?utm_source=hn&foo=bar#apply "
    )

    assert normalized.valid is True
    assert normalized.canonical_url == "https://examplecareers.com/jobs/Founding-Engineer?foo=bar"
    assert normalized.normalized_domain == "examplecareers.com"
    assert normalized.evidence == {"stripped_query_params": ["utm_source"]}


def test_normalization_rejects_unsafe_or_unsupported_urls():
    assert normalize_job_url("javascript:alert(1)").reason == "unsupported_scheme"
    assert normalize_job_url("https://user:pass@examplecareers.com/jobs").reason == "embedded_credentials"
    assert normalize_job_url("http://127.0.0.1/jobs").reason == "unsafe_host"
    assert normalize_job_url("https://localhost/jobs").reason == "unsafe_host"


def test_yc_job_url_detection_extracts_identifiers_and_canonicalizes_host():
    result = JobSourceDetector().detect(
        "ycombinator.com/companies/hazel-2/jobs/3epPWgu-full-stack-engineer-ts-sci"
    )

    assert result.source_type == JobSourceType.YCOMBINATOR_JOB
    assert result.supported is True
    assert result.provider == "ycombinator"
    assert result.company_slug == "hazel-2"
    assert result.job_identifier == "3epPWgu"
    assert result.canonical_url == (
        "https://www.ycombinator.com/companies/hazel-2/jobs/"
        "3epPWgu-full-stack-engineer-ts-sci"
    )


def test_yc_company_and_auth_pages_are_not_supported_job_pages():
    company = JobSourceDetector().detect("https://www.ycombinator.com/companies/hazel-2")
    auth = JobSourceDetector().detect("https://www.ycombinator.com/auth/login")

    assert company.supported is False
    assert company.source_type == JobSourceType.GENERIC_EXTERNAL_JOB_PAGE
    assert auth.supported is False


def test_yc_different_job_ids_remain_distinct():
    first = parse_yc_job_url("https://www.ycombinator.com/companies/acme/jobs/abc123-engineer")
    second = parse_yc_job_url("https://www.ycombinator.com/companies/acme/jobs/xyz789-engineer")

    assert first is not None and second is not None
    assert first.canonical_url != second.canonical_url


def test_ashby_board_and_posting_detection():
    board = JobSourceDetector().detect("https://jobs.ashbyhq.com/lago/")
    posting = JobSourceDetector().detect(
        "https://jobs.ashbyhq.com/supabase/2d6f1234?utm_campaign=x"
    )

    assert board.source_type == JobSourceType.ASHBY_JOB_BOARD
    assert board.board_slug == "lago"
    assert board.job_identifier is None
    assert board.reason == "ashby_board_requires_job_matching"
    assert board.evidence == {"board_level": True, "exact_posting": False}
    assert posting.board_slug == "supabase"
    assert posting.job_identifier == "2d6f1234"
    assert posting.canonical_url == "https://jobs.ashbyhq.com/supabase/2d6f1234"
    assert posting.evidence == {"board_level": False, "exact_posting": True}


def test_ashby_careers_query_detection_extracts_jid_without_board_slug():
    parsed = parse_ashby_careers_query_url("https://www.ashbyhq.com/careers?ashby_jid=posting_123&utm_source=hn")
    result = JobSourceDetector().detect("https://www.ashbyhq.com/careers?ashby_jid=posting_123&utm_source=hn")

    assert parsed is not None
    assert parsed.job_identifier == "posting_123"
    assert parsed.board_slug == ""
    assert parsed.canonical_url == "https://ashbyhq.com/careers?ashby_jid=posting_123"
    assert result.source_type == JobSourceType.ASHBY_JOB_BOARD
    assert result.provider == "ashby"
    assert result.supported is False
    assert result.job_identifier == "posting_123"
    assert result.board_slug is None
    assert result.reason == "ashby_board_slug_missing"
    assert result.evidence == {
        "classification": "ashby_careers_query",
        "ashby_jid": "posting_123",
        "exact_posting": True,
        "board_level": False,
    }


def test_ashby_different_posting_ids_remain_distinct():
    first = parse_ashby_job_url("https://jobs.ashbyhq.com/acme/posting-one")
    second = parse_ashby_job_url("https://jobs.ashbyhq.com/acme/posting-two")

    assert first is not None and second is not None
    assert first.canonical_url != second.canonical_url


def test_first_party_detection_uses_registrable_domain():
    detector = JobSourceDetector()

    root = detector.detect("https://9mothers.com/careers", company_domain="9mothers.com")
    www = detector.detect("https://www.9mothers.com/jobs/backend", company_domain="9mothers.com")
    careers = detector.detect("https://careers.9mothers.com/openings/123", company_domain="9mothers.com")
    unrelated = detector.detect("https://jobs.example-ats.com/9mothers", company_domain="9mothers.com")
    suffix_attack = detector.detect("https://9mothers.com.evil.test/jobs", company_domain="9mothers.com")

    assert root.source_type == JobSourceType.FIRST_PARTY_JOB_PAGE
    assert www.is_first_party is True
    assert careers.is_first_party is True
    assert unrelated.source_type == JobSourceType.GENERIC_EXTERNAL_JOB_PAGE
    assert suffix_attack.is_first_party is False


def test_compare_registrable_domains_handles_subdomains():
    assert compare_registrable_domains("careers.9mothers.com", "9mothers.com") is True
    assert compare_registrable_domains("company-name.medium.com", "company-name.com") is False
