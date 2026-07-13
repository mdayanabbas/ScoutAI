from datetime import datetime, timedelta, timezone

from app.discovery.sources.himalayas.models import HimalayasJobPayload
from app.discovery.sources.himalayas.parser import HimalayasJobParser


def _payload(**kwargs):
    values = {
        "title": "AI Engineer",
        "companyName": "Remote AI Co",
        "companySlug": "remote-ai",
        "employmentType": "Full Time",
        "seniority": ["Entry-level"],
        "locationRestrictions": [],
        "description": "<p>Build LLM systems with Python. 1+ years experience.</p><script>x()</script>",
        "applicationLink": "https://himalayas.app/companies/remote-ai/jobs/ai-engineer",
        "guid": "job-1",
        "pubDate": 1783824000000,
        "minSalary": 100000,
        "maxSalary": 140000,
        "currency": "USD",
        "salaryPeriod": "yearly",
    }
    values.update(kwargs)
    return HimalayasJobPayload.model_validate(values)


def test_parser_accepts_worldwide_and_india_remote_roles():
    worldwide = HimalayasJobParser().parse(_payload())
    india = HimalayasJobParser().parse(_payload(locationRestrictions=[{"alpha2": "IN", "name": "India"}], guid="job-2"))

    assert worldwide.accepted is True
    assert worldwide.remote_eligibility == "work_from_anywhere"
    assert worldwide.salary_min == 100000
    assert "<script" not in worldwide.description
    assert india.accepted is True
    assert india.remote_eligibility == "remote_india_eligible"


def test_parser_rejects_country_restricted_unrelated_senior_and_expired_jobs():
    parser = HimalayasJobParser()
    us_only = parser.parse(_payload(locationRestrictions=[{"alpha2": "US", "name": "United States"}]))
    sales = parser.parse(_payload(title="Sales Engineer"))
    senior = parser.parse(_payload(title="Senior Software Engineer", seniority="Senior"))
    expired = parser.parse(_payload(expiryDate=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat()))

    assert us_only.rejection_reason == "rejected_country_restriction"
    assert sales.rejection_reason == "rejected_role"
    assert senior.rejection_reason == "rejected_seniority"
    assert expired.rejection_reason == "rejected_expired"


def test_parser_preserves_non_annual_salary_as_text_only():
    parsed = HimalayasJobParser().parse(_payload(salaryPeriod="hourly", minSalary=50, maxSalary=80))

    assert parsed.salary_min is None
    assert parsed.salary_max is None
    assert parsed.salary_text == "USD 50 - 80 / hourly"


def test_parser_handles_missing_restrictions_and_multi_seniority():
    parsed = HimalayasJobParser().parse(_payload(locationRestrictions=None, seniority=["Entry-level", "Mid-level"]))

    assert parsed.accepted is True
    assert parsed.remote_eligibility == "remote_eligibility_unclear"
    assert parsed.seniority == "Entry-level, Mid-level"


def test_parser_invalid_expiry_warns_without_rejecting():
    parsed = HimalayasJobParser().parse(_payload(expiryDate="12345"))

    assert parsed.accepted is True
    assert "expiry_at:timestamp_invalid" in parsed.warnings
