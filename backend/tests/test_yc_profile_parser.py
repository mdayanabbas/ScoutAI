from app.enrichment.yc_profile_parser import parse_yc_company_profile


def test_parser_extracts_explicit_official_website_link():
    html = """
    <html><body>
      <h1>Infracost</h1>
      <a href="https://www.infracost.io">Website</a>
    </body></html>
    """

    result = parse_yc_company_profile(
        html, "https://www.ycombinator.com/companies/infracost"
    )

    assert result.resolved is True
    assert result.proposed_domain == "infracost.io"
    assert result.confidence == 0.95


def test_parser_extracts_current_top_profile_domain_anchor():
    html = """
    <main>
      <nav>
        <a href="/companies/infracost">Company</a>
        <a href="/companies/infracost/jobs">Jobs</a>
        <a href="/companies/infracost/news">News</a>
      </nav>
      <section class="company-header">
        <h1>Infracost</h1>
        <a href="https://infracost.io">https://infracost.io</a>
      </section>
      <p>Cloud cost tooling.</p>
      <section><h2>Active Founders</h2></section>
    </main>
    """

    result = parse_yc_company_profile(
        html, "https://www.ycombinator.com/companies/infracost"
    )

    assert result.resolved is True
    assert result.proposed_website_url == "https://infracost.io"
    assert result.proposed_domain == "infracost.io"
    assert result.confidence == 0.99
    assert result.evidence["extraction_strategy"] == "yc_header_official_website"


def test_parser_ignores_embedded_non_website_urls_before_header_anchor():
    html = """
    <script id="__NEXT_DATA__" type="application/json">
      {
        "props": {
          "pageProps": {
            "company": {
              "name": "Infracost",
              "url": "https://www.ycombinator.com/companies/infracost"
            },
            "news": [
              {"url": "https://techcrunch.com/infracost-funding"},
              {"url": "https://www.forbes.com/infracost"}
            ],
            "founders": [
              {"url": "https://www.linkedin.com/in/founder"}
            ]
          }
        }
      }
    </script>
    <main>
      <header>
        <h1>Infracost</h1>
        <a href="https://infracost.io">https://infracost.io</a>
      </header>
      <section><h2>Active Founders</h2></section>
    </main>
    """

    result = parse_yc_company_profile(
        html, "https://www.ycombinator.com/companies/infracost"
    )

    assert result.resolved is True
    assert result.proposed_domain == "infracost.io"
    assert result.evidence["extraction_strategy"] == "yc_header_official_website"


def test_parser_excludes_yc_global_chrome_from_company_domain_ranking():
    html = """
    <header class="global-nav">
      <a href="https://startupschool.org?utm_source=yc">Startup School</a>
      <a href="https://www.workatastartup.com">Work at a Startup</a>
      <a href="https://www.ycombinator.com/companies">Startup Directory</a>
    </header>
    <main>
      <section class="company-header">
        <h1>Nox Metals</h1>
        <a href="https://noxmetals.co/">https://noxmetals.co/</a>
      </section>
      <section class="founders">
        <a href="https://x.com/founder">X</a>
        <a href="https://linkedin.com/in/founder">LinkedIn</a>
      </section>
      <section class="company-description">
        <a href="http://noxmetals.co">More about Nox Metals</a>
        <a href="https://youtube.com/watch?v=123">Video</a>
      </section>
    </main>
    <footer class="global-footer">
      <a href="https://www.ycombinator.com/legal">Legal</a>
      <a href="https://startupschool.org">Startup School</a>
    </footer>
    """

    result = parse_yc_company_profile(
        html, "https://www.ycombinator.com/companies/nox-metals"
    )

    assert result.resolved is True
    assert result.proposed_domain == "noxmetals.co"
    assert result.evidence["extraction_strategy"] == "yc_header_official_website"
    assert result.evidence["ambiguity_candidate_domains"] == ["noxmetals.co"]
    rejected = result.evidence["rejected_candidates"]
    assert any(
        item["normalized_domain"] == "startupschool.org"
        and item["rejection_reason"] in {"yc_global_navigation", "yc_ecosystem_link"}
        for item in rejected
    )
    assert not any(
        item["normalized_domain"] == "workatastartup.com"
        and item["rejection_reason"] is None
        for item in rejected
    )


def test_parser_keeps_conflicting_company_header_domains_ambiguous():
    html = """
    <main>
      <section class="company-header">
        <h1>Acme</h1>
        <a href="https://first.example">first.example</a>
        <a href="https://second.example">second.example</a>
      </section>
    </main>
    """

    result = parse_yc_company_profile(
        html, "https://www.ycombinator.com/companies/acme"
    )

    assert result.resolved is False
    assert result.reason == "ambiguous_yc_profile_domains"


def test_parser_extracts_hazel_current_profile_anchor_with_noise():
    html = """
    <main>
      <header>
        <h1>Hazel</h1>
        <a href="https://hazelai.com">hazelai.com</a>
      </header>
      <section>
        <h2>Active Founders</h2>
        <a href="https://www.linkedin.com/in/founder">Founder LinkedIn</a>
      </section>
      <section>
        <h2>News</h2>
        <a href="https://techcrunch.com/hazel-funding">Funding news</a>
      </section>
    </main>
    """

    result = parse_yc_company_profile(
        html, "https://www.ycombinator.com/companies/hazel-2"
    )

    assert result.resolved is True
    assert result.proposed_domain == "hazelai.com"
    rejected_reasons = {
        item["rejection_reason"] for item in result.evidence["rejected_candidates"]
    }
    assert "social_platform" in rejected_reasons
    assert "news_article" in rejected_reasons


def test_parser_extracts_website_from_structured_metadata():
    html = """
    <script type="application/ld+json">
      {"@type": "Organization", "name": "Hazel", "website": "https://hazel.co"}
    </script>
    """

    result = parse_yc_company_profile(
        html, "https://www.ycombinator.com/companies/hazel-2"
    )

    assert result.resolved is True
    assert result.proposed_domain == "hazel.co"
    assert result.confidence == 0.99


def test_parser_ignores_internal_and_social_links():
    html = """
    <a href="https://www.ycombinator.com/companies/infracost">YC</a>
    <a href="https://github.com/infracost/infracost">GitHub</a>
    <a href="https://www.linkedin.com/company/infracost">LinkedIn</a>
    <a href="https://x.com/infracost">X</a>
    <a href="https://jobs.ashbyhq.com/infracost">Jobs</a>
    """

    result = parse_yc_company_profile(
        html, "https://www.ycombinator.com/companies/infracost"
    )

    assert result.resolved is False
    assert result.reason == "yc_official_website_missing"


def test_parser_handles_html_entities_and_malformed_html():
    html = '<a href="https:&#x2F;&#x2F;manufact.ai">Website'

    result = parse_yc_company_profile(
        html, "https://www.ycombinator.com/companies/manufact"
    )

    assert result.resolved is True
    assert result.proposed_domain == "manufact.ai"


def test_parser_returns_ambiguity_for_conflicting_domains():
    html = """
    <a href="https://first.example">Website</a>
    <a href="https://second.example">Homepage</a>
    """

    result = parse_yc_company_profile(
        html, "https://www.ycombinator.com/companies/acme"
    )

    assert result.resolved is False
    assert result.reason == "ambiguous_yc_profile_domains"


def test_parser_consolidates_same_root_domain_and_prefers_root_url():
    html = """
    <main>
      <header>
        <h1>Proliferate</h1>
        <a href="https://docs.proliferate.com">https://docs.proliferate.com</a>
        <a href="https://proliferate.com/waitlist">Website</a>
        <a href="https://proliferate.com">https://proliferate.com</a>
      </header>
      <section><h2>Active Founders</h2></section>
    </main>
    """

    result = parse_yc_company_profile(
        html, "https://www.ycombinator.com/companies/proliferate"
    )

    assert result.resolved is True
    assert result.proposed_website_url == "https://proliferate.com"
    assert result.proposed_domain == "proliferate.com"


def test_parser_rejects_news_and_ats_links_without_guessing():
    html = """
    <main>
      <header>
        <h1>Acme</h1>
      </header>
      <section>
        <a href="https://jobs.ashbyhq.com/acme">Jobs</a>
        <a href="https://techcrunch.com/acme-launch">Launch post</a>
      </section>
    </main>
    """

    result = parse_yc_company_profile(
        html, "https://www.ycombinator.com/companies/acme"
    )

    assert result.resolved is False
    assert result.reason == "yc_official_website_missing"
    rejected_reasons = {
        item["rejection_reason"] for item in result.evidence["rejected_candidates"]
    }
    assert {"ats_or_job_link", "news_article"}.issubset(rejected_reasons)
