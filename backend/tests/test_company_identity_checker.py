from app.enrichment.company_identity_checker import (
    HomepageMetadata,
    check_company_identity,
    extract_homepage_metadata,
)


def test_exact_company_title_matches():
    result = check_company_identity("Supabase", HomepageMetadata(url="https://supabase.com", title="Supabase"))

    assert result.matched
    assert "title" in result.matched_signals


def test_legal_suffix_differences_match():
    result = check_company_identity(
        "Lago",
        HomepageMetadata(url="https://getlago.com", title="Lago Inc."),
    )

    assert result.matched


def test_unrelated_company_with_same_partial_name_fails():
    result = check_company_identity(
        "Lago",
        HomepageMetadata(url="https://example.com", title="Lagoon Analytics"),
    )

    assert not result.matched


def test_matching_json_ld_organization_name_succeeds():
    metadata = extract_homepage_metadata(
        """
        <html><head>
        <script type="application/ld+json">
        {"@type": "Organization", "name": "Supabase Inc."}
        </script>
        </head><body></body></html>
        """,
        "https://supabase.com",
    )

    result = check_company_identity("Supabase", metadata)

    assert result.matched
    assert "json_ld_organization_name" in result.matched_signals


def test_conflicting_title_and_organization_name_remains_unresolved():
    result = check_company_identity(
        "Supabase",
        HomepageMetadata(
            url="https://example.com",
            title="Example Cloud",
            organization_names=("Example Cloud LLC",),
        ),
    )

    assert not result.matched
    assert result.reason == "homepage_identity_mismatch"
