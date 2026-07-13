from types import SimpleNamespace

from app.matching.job_actionability import JobActionabilityValidator


def validate(**kwargs):
    values = {
        "job_url": None,
        "apply_url": None,
        "status": "active",
        "enrichment_status": "enriched",
        "source_platform": None,
    }
    values.update(kwargs)
    return JobActionabilityValidator().validate(SimpleNamespace(**values))


def test_malformed_and_missing_urls_are_rejected():
    malformed = validate(job_url="bjasvhcjhv")
    missing = validate()

    assert malformed.actionable is False
    assert malformed.status == "invalid"
    assert "job_url_malformed_job_url" in malformed.reasons
    assert missing.actionable is False


def test_valid_job_or_apply_url_is_actionable():
    job_url = validate(job_url="https://www.ycombinator.com/companies/example/jobs/123-engineer")
    apply_url = validate(apply_url="https://jobs.ashbyhq.com/example/posting-id")

    assert job_url.actionable is True
    assert job_url.valid_job_url is True
    assert apply_url.actionable is True
    assert apply_url.valid_apply_url is True


def test_unsafe_urls_and_inactive_jobs_are_rejected():
    localhost = validate(job_url="http://localhost:8000/job")
    private_ip = validate(job_url="http://10.0.0.2/job")
    inactive = validate(job_url="https://company.com/careers/backend-engineer", status="inactive")

    assert localhost.actionable is False
    assert private_ip.actionable is False
    assert inactive.actionable is False
    assert inactive.status == "closed"


def test_not_enriched_with_valid_url_is_unverified_not_rejected():
    result = validate(
        job_url="https://company.com/careers/backend-engineer",
        enrichment_status="not_enriched",
    )

    assert result.actionable is True
    assert result.status == "unverified"
    assert result.valid_job_url is True
