import json

from app.jobs.expansion.first_party_listing_parser import FirstPartyListingParser


def parse(html: str):
    return FirstPartyListingParser().parse(
        html,
        source_url="https://example.com/careers",
        canonical_url="https://example.com/careers",
        company_name="Example",
        company_domain="example.com",
    )


def test_multiple_json_ld_jobpostings_extracted_and_deduped():
    posting = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": "Backend Engineer",
        "identifier": {"value": "be-1"},
        "url": "https://example.com/careers/backend-engineer",
        "employmentType": "FULL_TIME",
        "jobLocation": {"address": {"addressLocality": "Remote"}},
        "hiringOrganization": {"name": "Example", "sameAs": "https://example.com"},
        "description": "<p>Build APIs.</p>",
    }
    html = f"""
    <script type="application/ld+json">{json.dumps([posting, posting, {**posting, "title": "Product Manager", "identifier": {"value": "pm-1"}, "url": "https://example.com/careers/product-manager"}])}</script>
    """

    result = parse(html)

    assert result.listing_detected is True
    assert result.parser_strategy == "json_ld_jobposting"
    assert [item.title for item in result.candidates] == ["Backend Engineer", "Product Manager"]
    assert all("description" not in item.structured_data for item in result.candidates if item.structured_data)


def test_company_mismatched_posting_rejected():
    html = """
    <script type="application/ld+json">
    {"@type":"JobPosting","title":"Backend Engineer","url":"https://example.com/jobs/backend","hiringOrganization":{"name":"Other Co","sameAs":"https://other.com"}}
    </script>
    """

    result = parse(html)

    assert result.listing_detected is False
    assert result.candidates[0].rejection_reason == "first_party_listing_company_mismatch"


def test_semantic_cards_pair_title_with_correct_url_and_ignore_nav_footer():
    html = """
    <nav><a href="/careers">Backend Engineer</a></nav>
    <main>
      <article><h3>Backend Engineer</h3><p>Location: Remote</p><a href="/careers/backend-engineer">Details</a></article>
      <article><h3>Account Executive</h3><p>Department: Sales</p><a href="/careers/account-executive">Details</a></article>
    </main>
    <footer><a href="/careers/product-manager">Product Manager</a></footer>
    """

    result = parse(html)

    accepted = [item for item in result.candidates if not item.rejection_reason]
    assert result.listing_detected is True
    assert [(item.title, item.canonical_url) for item in accepted] == [
        ("Backend Engineer", "https://example.com/careers/backend-engineer"),
        ("Account Executive", "https://example.com/careers/account-executive"),
    ]


def test_blocked_paths_use_exact_segments_not_role_slug_substrings():
    html = """
    <main>
      <article><h3>Account Executive</h3><a href="/careers/account-executive">Details</a></article>
      <article><h3>Account Manager</h3><a href="/jobs/account-manager">Details</a></article>
      <article><h3>Auth Engineer</h3><a href="/careers/auth-engineer">Details</a></article>
      <article><h3>Backend Engineer</h3><a href="/account">Details</a></article>
      <article><h3>Frontend Engineer</h3><a href="/account/settings">Details</a></article>
    </main>
    """

    result = parse(html)
    by_title = {item.title: item for item in result.candidates}

    assert by_title["Account Executive"].rejection_reason is None
    assert by_title["Account Manager"].rejection_reason is None
    assert by_title["Auth Engineer"].rejection_reason is None
    assert by_title["Backend Engineer"].rejection_reason == "blocked_path"
    assert by_title["Frontend Engineer"].rejection_reason == "blocked_path"


def test_listing_titles_strip_terminal_action_labels_only():
    html = """
    <main>
      <article><h3>R&D Test Engineer, Senior Apply</h3><a href="/careers/test-engineer">Details</a></article>
      <article><h3>Electrical Engineer, Staff Apply Now</h3><a href="/careers/electrical-engineer">Details</a></article>
      <article><h3>Applied Scientist</h3><a href="/careers/applied-scientist">Details</a></article>
      <article><h3>Application Engineer</h3><a href="/careers/application-engineer">Details</a></article>
    </main>
    """

    result = parse(html)
    titles = [item.title for item in result.candidates if not item.rejection_reason]

    assert "R&D Test Engineer, Senior" in titles
    assert "Electrical Engineer, Staff" in titles
    assert "Applied Scientist" in titles
    assert "Application Engineer" in titles


def test_generic_parent_suffix_attack_and_external_ats_rejections():
    html = """
    <main>
      <a href="/careers">Open Roles</a>
      <a href="https://example.com.evil.test/careers/backend">Backend Engineer</a>
      <a href="https://boards.greenhouse.io/example/jobs/1">Frontend Engineer</a>
      <a href="https://jobs.ashbyhq.com/example/abc123">ML Engineer</a>
    </main>
    """

    result = parse(html)

    by_title = {item.title: item for item in result.candidates}
    assert "Open Roles" not in by_title
    assert by_title["Backend Engineer"].rejection_reason == "domain_mismatch"
    assert by_title["Frontend Engineer"].rejection_reason == "external_ats_provider_not_supported"
    assert by_title["ML Engineer"].canonical_url == "https://jobs.ashbyhq.com/example/abc123"
    assert by_title["ML Engineer"].rejection_reason is None


def test_unrelated_page_not_classified_as_listing():
    html = """
    <main><h1>Customers</h1><a href="/blog/founder-story">Founder Story</a><a href="/privacy">Privacy</a></main>
    """

    result = parse(html)

    assert result.listing_detected is False
    assert result.reason == "first_party_listing_no_roles"
