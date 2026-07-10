from app.jobs.enrichment.parsers.ycombinator_job_parser import (
    YCombinatorJobParser,
    classify_role_category,
)

URL = "https://www.ycombinator.com/companies/hazel-2/jobs/3epPWgu-full-stack-engineer-ts-sci"


def _html(title="Full Stack Engineer (TS/SCI)", labels="", description="About the role\nBuild important systems."):
    return f"""
    <html>
      <head><meta property="og:title" content="{title} at Hazel | Y Combinator"></head>
      <body>
        <nav>YC Home Recommended Jobs</nav>
        <main>
          <h1>{title}</h1>
          <dl>{labels}</dl>
          <section><h2>About the role</h2><p>{description}</p></section>
          <aside><h3>Related jobs</h3><p>Marketing Lead</p></aside>
        </main>
      </body>
    </html>
    """


def test_parser_prefers_jobposting_title_and_fields():
    html = """
    <script type="application/ld+json">
    {
      "@type": "JobPosting",
      "title": "Founding Product Engineer",
      "description": "<p>About the role</p><p>Build product with customers.</p>",
      "employmentType": "Full-time",
      "datePosted": "2026-07-01T00:00:00Z",
      "skills": ["TypeScript", "React", "TypeScript"],
      "baseSalary": {"currency":"USD","value":{"minValue":130000,"maxValue":250000}},
      "url": "https://www.ycombinator.com/companies/proliferate/jobs/abc-founding-product-engineer"
    }
    </script>
    <h1>Open Roles</h1>
    """

    result = YCombinatorJobParser().parse(html, source_url=URL, canonical_url=URL)

    assert result.success is True
    assert result.title.value == "Founding Product Engineer"
    assert result.title.confidence == 1.0
    assert result.role_category.value == "product_engineer"
    assert result.employment_type.value == "full_time"
    assert result.required_skills.value == ["TypeScript", "React"]
    assert result.salary_min.value == 130000
    assert result.salary_max.value == 250000
    assert result.published_at.value.isoformat().startswith("2026-07-01")


def test_parser_extracts_h1_ignores_related_jobs_and_preserves_punctuation():
    labels = """
      <dt>Job type</dt><dd>Full-time</dd>
      <dt>Experience</dt><dd>6+ years</dd>
      <dt>Visa</dt><dd>US citizen/visa only</dd>
      <dt>Skills</dt><dd>Amazon Web Services (AWS), PostgreSQL, C++</dd>
      <dt>Location</dt><dd>New York, NY / Remote</dd>
      <dt>Compensation</dt><dd>$130K - $250K + 0.50% - 2.00%</dd>
    """

    result = YCombinatorJobParser().parse(_html(labels=labels), source_url=URL, canonical_url=URL)

    assert result.title.value == "Full Stack Engineer (TS/SCI)"
    assert result.role_category.value == "full_stack_engineer"
    assert result.description.value.count("Marketing Lead") == 0
    assert result.experience_min.value == 6
    assert result.seniority.value == "senior"
    assert result.remote_type.value == "remote_worldwide"
    assert result.salary_min.value == 130000
    assert result.salary_max.value == 250000
    assert result.equity_mentioned.value is True
    assert result.visa_sponsorship.value == "restricted"
    assert result.required_skills.value == ["Amazon Web Services (AWS)", "PostgreSQL", "C++"]


def test_parser_salary_and_experience_variants():
    cases = [
        ("€60k–€100k", 60000, 100000, "EUR"),
        ("£80,000 - £110,000", 80000, 110000, "GBP"),
        ("$120,000", 120000, 120000, "USD"),
    ]
    for salary, expected_min, expected_max, currency in cases:
        html = _html(labels=f"<dt>Compensation</dt><dd>{salary}</dd><dt>Experience</dt><dd>Any (new grads ok)</dd>")
        result = YCombinatorJobParser().parse(html, source_url=URL, canonical_url=URL)
        assert result.salary_min.value == expected_min
        assert result.salary_max.value == expected_max
        assert result.salary_currency.value == currency
        assert result.experience_min.value == 0


def test_parser_preserves_salary_text_when_numeric_parse_fails():
    html = _html(labels="<dt>Compensation</dt><dd>Competitive</dd>")

    result = YCombinatorJobParser().parse(html, source_url=URL, canonical_url=URL)

    assert result.salary_text.value == "Competitive"
    assert result.salary_min is None
    assert "salary_text_not_numeric" in result.warnings


def test_slug_fallback_has_low_confidence_and_untrustworthy_empty_page_is_unresolved():
    fallback = YCombinatorJobParser().parse("", source_url=URL, canonical_url=URL)
    weak = YCombinatorJobParser().parse("<html></html>", source_url=URL, canonical_url=URL)

    assert fallback.success is False
    assert weak.title.value == "Full Stack Engineer Ts Sci"
    assert weak.title.confidence == 0.7
    assert weak.success is False


def test_role_classification_current_examples():
    assert classify_role_category("Full Stack Engineer (TS/SCI)") == "full_stack_engineer"
    assert classify_role_category("Founding Product Engineer") == "product_engineer"
    assert classify_role_category("Founding Account Executive") == "sales"
    assert classify_role_category("Marketing Lead") == "marketing"
    assert classify_role_category("Developer Advocate & Partnerships (DevRel)") == "developer_advocate"
    assert classify_role_category("Office Champion") == "other"
