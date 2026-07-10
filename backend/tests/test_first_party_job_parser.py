import json

from app.jobs.enrichment.parsers.first_party_job_parser import FirstPartyJobParser


def _html(jobposting):
    return f"""
    <html><head>
      <meta property="og:site_name" content="Example">
      <script type="application/ld+json">{json.dumps(jobposting)}</script>
    </head><body><main><h1>Ignore Me</h1></main></body></html>
    """


def test_parser_extracts_json_ld_jobposting_fields():
    posting = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": "Senior Backend Engineer",
        "description": "<p>Build APIs with Python and PostgreSQL.</p><p>5+ years required.</p>",
        "datePosted": "2026-01-02T00:00:00Z",
        "employmentType": "FULL_TIME",
        "hiringOrganization": {"name": "Example", "sameAs": "https://example.com"},
        "jobLocationType": "TELECOMMUTE",
        "baseSalary": {"currency": "USD", "value": {"minValue": 120000, "maxValue": 180000, "unitText": "YEAR"}},
        "skills": ["Python", "PostgreSQL", "Python"],
        "url": "https://example.com/careers/backend-engineer?utm_source=hn",
    }

    result = FirstPartyJobParser().parse(
        _html(posting),
        source_url="https://example.com/careers/backend-engineer",
        canonical_url="https://example.com/careers/backend-engineer",
        company_name="Example",
        company_domain="example.com",
    )

    assert result.success is True
    assert result.title.value == "Senior Backend Engineer"
    assert result.role_category.value == "backend_engineer"
    assert result.remote_type.value == "remote_worldwide"
    assert result.employment_type.value == "full_time"
    assert result.salary_min.value == 120000
    assert result.salary_max.value == 180000
    assert result.salary_currency.value == "USD"
    assert result.experience_min.value == 5
    assert result.published_at.value.isoformat().startswith("2026-01-02")
    assert "PostgreSQL" in result.technologies.value
    assert "raw_html" not in result.evidence


def test_parser_handles_graph_malformed_listing_and_identity_mismatch():
    graph = {
        "@graph": [
            {"@type": "Organization", "name": "Example"},
            {"@type": "JobPosting", "title": "Backend Engineer", "hiringOrganization": {"name": "Example"}},
        ]
    }
    graph_result = FirstPartyJobParser().parse(_html(graph), source_url="https://example.com/jobs/backend", canonical_url="https://example.com/jobs/backend", company_name="Example", company_domain="example.com")
    assert graph_result.success is True

    listing = """
    <script type="application/ld+json">{"@type":"JobPosting","title":"Backend Engineer"}</script>
    <script type="application/ld+json">{"@type":"JobPosting","title":"Account Executive"}</script>
    """
    listing_result = FirstPartyJobParser().parse(listing, source_url="https://example.com/careers", canonical_url="https://example.com/careers", company_name="Example", company_domain="example.com")
    assert listing_result.success is False
    assert listing_result.reason == "first_party_listing_page_requires_expansion"

    malformed = '<script type="application/ld+json">{bad</script><h1>Backend Engineer</h1><main>Build things.</main>'
    malformed_result = FirstPartyJobParser().parse(malformed, source_url="https://example.com/jobs/backend", canonical_url="https://example.com/jobs/backend", company_name="Example", company_domain="example.com")
    assert malformed_result.success is True

    mismatch = FirstPartyJobParser().parse(_html({"@type": "JobPosting", "title": "Backend Engineer", "hiringOrganization": {"name": "Other Co"}}), source_url="https://example.com/jobs/backend", canonical_url="https://example.com/jobs/backend", company_name="Example", company_domain="example.com")
    assert mismatch.reason == "first_party_company_identity_mismatch"


def test_parser_listing_page_and_slug_fallback():
    listing = "<html><body><h1>Open positions</h1><a>Backend Engineer</a><a>Account Executive</a><a>Product Designer</a></body></html>"
    result = FirstPartyJobParser().parse(listing, source_url="https://example.com/careers", canonical_url="https://example.com/careers", company_name="Example", company_domain="example.com")
    assert result.success is False
    assert result.reason == "first_party_listing_page_requires_expansion"

    slug = FirstPartyJobParser().parse("<html><body><main>We need someone excellent.</main></body></html>", source_url="https://example.com/careers/backend-engineer", canonical_url="https://example.com/careers/backend-engineer", company_name="Example", company_domain="example.com")
    assert slug.title.value == "Backend Engineer"
    assert slug.title.confidence == 0.65

