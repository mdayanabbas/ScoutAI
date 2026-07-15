from app.discovery.sources.remotive.models import RemotiveJobPayload
from app.discovery.sources.remotive.parser import RemotiveJobParser


def _payload(**overrides):
    data = {
        "id": 1,
        "url": "https://remotive.com/remote-jobs/software-dev/ai-engineer-123?utm_source=x",
        "title": "AI Engineer",
        "company_name": "Remote AI Co",
        "category": "Software Development",
        "job_type": "full-time",
        "publication_date": "2026-07-14T10:00:00",
        "candidate_required_location": "Worldwide",
        "salary": "$80k - $120k yearly",
        "description": "<p>Build GenAI systems.</p><script>bad()</script>",
    }
    data.update(overrides)
    return RemotiveJobPayload.model_validate(data)


def test_parser_sanitizes_description_normalizes_fields_and_url():
    parsed = RemotiveJobParser().parse(_payload(description="<p>Build GenAI systems Â£</p><img src=x>"))

    assert parsed.source_item_id == "1"
    assert parsed.title == "AI Engineer"
    assert parsed.company_name == "Remote AI Co"
    assert "bad()" not in (parsed.description or "")
    assert parsed.source_url == "https://remotive.com/remote-jobs/software-dev/ai-engineer-123"
    assert parsed.employment_type == "full_time"
    assert parsed.salary_min == 80000
    assert parsed.salary_max == 120000
    assert parsed.salary_currency == "USD"
    assert parsed.published_at is not None


def test_parser_accepts_missing_optional_salary_and_rejects_external_url():
    parsed = RemotiveJobParser().parse(_payload(url="https://example.com/job", salary=None))

    assert parsed.source_url is None
    assert parsed.salary_text is None
    assert parsed.salary_min is None


def test_parser_invalid_publication_date_produces_warning_and_contract_normalizes():
    parsed = RemotiveJobParser().parse(_payload(publication_date="not a date", job_type="freelance"))

    assert parsed.published_at is None
    assert parsed.warnings == ["publication_date:invalid_publication_date"]
    assert parsed.employment_type == "contract"
