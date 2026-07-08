from app.discovery.normalizer import normalize_candidate
from app.schemas.discovery import RawStartupCandidate


def test_candidate_name_and_text_are_normalized():
    normalized = normalize_candidate(
        RawStartupCandidate(
            source_identifier=" manual-acme ",
            name="  Acme   AI  ",
            website_url="https://www.acme.ai/",
            description="  AI   workflow   automation. ",
            country=" United   States ",
        )
    )

    assert normalized.source_identifier == "manual-acme"
    assert normalized.name == "Acme AI"
    assert normalized.website_url == "acme.ai"
    assert normalized.normalized_domain == "acme.ai"
    assert normalized.description == "AI workflow automation."
    assert normalized.country == "United States"
