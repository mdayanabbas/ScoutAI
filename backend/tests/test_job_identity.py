from app.jobs.job_identity import build_job_identity


def test_same_company_equivalent_urls_produce_same_identity():
    first = build_job_identity(
        company_id="company-1",
        job_url="https://www.9mothers.com:443/careers/?utm_source=hn",
        normalized_title="founding engineer",
    )
    second = build_job_identity(
        company_id="company-1",
        job_url="9mothers.com/careers",
        normalized_title="founding engineer",
    )

    assert first.identity_strategy == "company_and_canonical_url"
    assert first.identity_key == second.identity_key


def test_same_company_different_paths_are_distinct():
    first = build_job_identity(
        company_id="company-1",
        job_url="https://9mothers.com/careers",
        normalized_title="engineer",
    )
    second = build_job_identity(
        company_id="company-1",
        job_url="https://9mothers.com/jobs/backend",
        normalized_title="engineer",
    )

    assert first.identity_key != second.identity_key


def test_different_companies_with_same_title_are_distinct():
    first = build_job_identity(
        company_id="company-1",
        job_url=None,
        normalized_title="founding engineer",
    )
    second = build_job_identity(
        company_id="company-2",
        job_url=None,
        normalized_title="founding engineer",
    )

    assert first.identity_strategy == "company_and_title"
    assert first.identity_key != second.identity_key


def test_canonical_url_has_priority_over_title():
    identity = build_job_identity(
        company_id="company-1",
        job_url="https://9mothers.com/careers",
        normalized_title="founding engineer",
    )

    assert identity.identity_strategy == "company_and_canonical_url"
    assert "title" not in (identity.identity_key or "")


def test_missing_url_falls_back_to_company_and_title():
    identity = build_job_identity(
        company_id="company-1",
        job_url=None,
        normalized_title="founding engineer",
    )

    assert identity.identity_strategy == "company_and_title"
    assert identity.identity_key == "company:company-1:title:founding engineer"


def test_missing_company_is_insufficient_identity():
    identity = build_job_identity(
        company_id=None,
        job_url="https://9mothers.com/careers",
        normalized_title="founding engineer",
    )

    assert identity.identity_strategy == "insufficient_identity"
    assert identity.identity_key is None
