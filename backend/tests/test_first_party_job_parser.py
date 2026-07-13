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


def test_parser_extracts_experience_from_structured_description_and_qualifications():
    parser = FirstPartyJobParser()
    plus = parser.parse(
        _html({
            "@type": "JobPosting",
            "title": "Backend Engineer",
            "description": "<p>Build APIs with Python and PostgreSQL.</p><p>5+ years required.</p>",
            "hiringOrganization": {"name": "Example"},
        }),
        source_url="https://example.com/careers/backend-engineer",
        canonical_url="https://example.com/careers/backend-engineer",
        company_name="Example",
        company_domain="example.com",
    )
    assert plus.experience_min.value == 5
    assert plus.experience_max is None

    ranged = parser.parse(
        _html({
            "@type": "JobPosting",
            "title": "Backend Engineer",
            "description": "<p>3-5 years of experience building APIs.</p>",
            "hiringOrganization": {"name": "Example"},
        }),
        source_url="https://example.com/careers/backend-engineer",
        canonical_url="https://example.com/careers/backend-engineer",
        company_name="Example",
        company_domain="example.com",
    )
    assert ranged.experience_min.value == 3
    assert ranged.experience_max.value == 5

    zero = parser.parse(
        _html({
            "@type": "JobPosting",
            "title": "Junior Backend Engineer",
            "description": "<p>0-2 years of experience.</p>",
            "hiringOrganization": {"name": "Example"},
        }),
        source_url="https://example.com/careers/junior-backend-engineer",
        canonical_url="https://example.com/careers/junior-backend-engineer",
        company_name="Example",
        company_domain="example.com",
    )
    assert zero.experience_min.value == 0
    assert zero.experience_max.value == 2

    explicit = parser.parse(
        _html({
            "@type": "JobPosting",
            "title": "Backend Engineer",
            "experienceRequirements": "7+ years required.",
            "description": "<p>3-5 years of experience.</p>",
            "hiringOrganization": {"name": "Example"},
        }),
        source_url="https://example.com/careers/backend-engineer",
        canonical_url="https://example.com/careers/backend-engineer",
        company_name="Example",
        company_domain="example.com",
    )
    assert explicit.experience_min.value == 7
    assert explicit.experience_max is None


def test_parser_does_not_treat_unrelated_dates_as_experience():
    result = FirstPartyJobParser().parse(
        _html({
            "@type": "JobPosting",
            "title": "Backend Engineer",
            "description": "<p>Copyright 2020-2024 Example. Posted 2026-01-02.</p>",
            "hiringOrganization": {"name": "Example"},
        }),
        source_url="https://example.com/careers/backend-engineer",
        canonical_url="https://example.com/careers/backend-engineer",
        company_name="Example",
        company_domain="example.com",
    )
    assert result.experience_min is None
    assert result.experience_max is None


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
    assert slug.success is True
    assert slug.title.value == "Backend Engineer"
    assert slug.title.confidence == 0.65
    assert slug.title.source == "url_slug"


def test_parser_slug_fallback_edges():
    parser = FirstPartyJobParser()
    structured = parser.parse(
        _html({"@type": "JobPosting", "title": "Senior Backend Engineer", "hiringOrganization": {"name": "Example"}}),
        source_url="https://example.com/careers/backend-engineer",
        canonical_url="https://example.com/careers/backend-engineer",
        company_name="Example",
        company_domain="example.com",
    )
    slug = parser.parse("<html><body><main>We need someone excellent.</main></body></html>", source_url="https://example.com/careers/founding-ai-engineer", canonical_url="https://example.com/careers/founding-ai-engineer", company_name="Example", company_domain="example.com")
    careers = parser.parse("<html><body><main>We need someone excellent.</main></body></html>", source_url="https://example.com/careers", canonical_url="https://example.com/careers", company_name="Example", company_domain="example.com")
    openings = parser.parse("<html><body><main>We need someone excellent.</main></body></html>", source_url="https://example.com/openings", canonical_url="https://example.com/openings", company_name="Example", company_domain="example.com")
    numeric = parser.parse("<html><body><main>We need someone excellent.</main></body></html>", source_url="https://example.com/careers/12345", canonical_url="https://example.com/careers/12345", company_name="Example", company_domain="example.com")

    assert slug.title.value == "Founding AI Engineer"
    assert careers.title is None
    assert openings.title is None
    assert numeric.title is None
    assert slug.title.confidence < structured.title.confidence


def test_parser_preserves_meaningful_skill_units_without_fragments():
    html = """
    <html><body><main>
      <h1>Developer Advocate</h1>
      <p>Preferred qualifications:</p>
      <ul>
        <li>Hands-on experience with MCP</li>
        <li>co-marketing with developer-facing teams</li>
        <li>React/Next.js</li>
        <li>AuthN/AuthZ</li>
        <li>CI/CD</li>
      </ul>
    </main></body></html>
    """

    result = FirstPartyJobParser().parse(
        html,
        source_url="https://example.com/careers/developer-advocate",
        canonical_url="https://example.com/careers/developer-advocate",
        company_name="Example",
        company_domain="example.com",
    )

    assert "Hands-on experience with MCP" in result.preferred_skills.value
    assert "co-marketing with developer-facing teams" in result.preferred_skills.value
    assert "React/Next.js" in result.preferred_skills.value
    assert "Hands" not in result.preferred_skills.value
    assert "co" not in result.preferred_skills.value

