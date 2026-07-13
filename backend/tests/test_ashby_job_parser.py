from app.jobs.enrichment.parsers.ashby_job_parser import (
    AshbyJobParser,
    parse_ashby_posting_identifier,
)
from app.jobs.enrichment.providers.ashby_models import AshbyPublicJobPosting


def test_parser_maps_structured_ashby_posting():
    posting = AshbyPublicJobPosting(
        id="abc123",
        title="Senior Backend Engineer",
        location="New York, NY",
        secondary_locations=["Remote"],
        department="Engineering",
        team="Platform",
        is_listed=True,
        is_remote=True,
        workplace_type="Remote",
        employment_type="FullTime",
        description_plain="Build APIs with Python, PostgreSQL, and Kubernetes. 5+ years required.",
        published_at="2026-01-02T00:00:00Z",
        job_url="https://jobs.ashbyhq.com/lago/abc123?utm_source=hn",
        apply_url="https://jobs.ashbyhq.com/lago/abc123/application",
        compensation={"summary": "$130K - $250K + 0.50% - 2.00%"},
    )

    result = AshbyJobParser().parse_posting(posting, board_slug="lago")

    assert result.success is True
    assert result.title.value == "Senior Backend Engineer"
    assert result.description.value.startswith("Build APIs")
    assert result.role_category.value == "backend_engineer"
    assert result.remote_type.value == "remote_worldwide"
    assert result.employment_type.value == "full_time"
    assert result.experience_min.value == 5
    assert result.salary_min.value == 130000
    assert result.salary_max.value == 250000
    assert result.salary_currency.value == "USD"
    assert result.equity_mentioned.value is True
    assert result.job_url.value == "https://jobs.ashbyhq.com/lago/abc123"
    assert "description_html" not in result.evidence
    assert "PostgreSQL" in result.technologies.value


def test_parser_prefers_plain_description_and_safely_converts_html():
    plain = AshbyPublicJobPosting(
        id="plain",
        title="Developer Advocate",
        description_plain="Plain description",
        description_html="<script>bad()</script><p>HTML description</p>",
    )
    html = AshbyPublicJobPosting(
        id="html",
        title="Developer Advocate",
        description_html="<script>bad()</script><p>HTML description</p>",
    )

    assert AshbyJobParser().parse_posting(plain, board_slug="lago").description.value == "Plain description"
    assert AshbyJobParser().parse_posting(html, board_slug="lago").description.value == "HTML description"


def test_parse_ashby_posting_identifier_supports_equivalent_urls():
    assert parse_ashby_posting_identifier("https://jobs.ashbyhq.com/lago/abc123") == "abc123"
    assert parse_ashby_posting_identifier("https://jobs.ashbyhq.com/lago") is None


def test_parser_repairs_text_and_strips_apply_suffix():
    posting = AshbyPublicJobPosting(
        id="abc123",
        title="Electrical Engineer, Staff Apply",
        location="Remote",
        description_plain="YouÃ¢â‚¬â„¢ll build hardware tools with Docker.",
        job_url="https://jobs.ashbyhq.com/lago/abc123?utm_source=hn",
    )

    result = AshbyJobParser().parse_posting(posting, board_slug="lago")

    assert result.title.value == "Electrical Engineer, Staff"
    assert result.description.value == "You\u2019ll build hardware tools with Docker."
    assert result.role_category.value == "other"
    assert result.job_url.value == "https://jobs.ashbyhq.com/lago/abc123"
