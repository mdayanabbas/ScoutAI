from datetime import timezone

from app.discovery.sources.hacker_news.parser import (
    build_hacker_news_evidence,
    clean_hacker_news_html,
    extract_candidate_name,
    extract_candidate_website,
)
from app.discovery.sources.hacker_news.schemas import HackerNewsItem


def test_extracts_company_from_show_hn_title():
    item = HackerNewsItem(id=1, type="story", title="Show HN: Acme - AI automation")

    assert extract_candidate_name(item) == "Acme"


def test_extracts_company_from_is_hiring_title():
    item = HackerNewsItem(id=2, type="story", title="TinyAgent (YC S26) is hiring")

    assert extract_candidate_name(item) == "TinyAgent"


def test_extracts_company_from_role_at_company_title():
    item = HackerNewsItem(id=3, type="story", title="Backend Engineer at Acme")

    assert extract_candidate_name(item) == "Acme"


def test_cleans_html_text():
    assert clean_hacker_news_html("<p>Hello&nbsp;world</p><script>x()</script>") == "Hello world"


def test_creates_hacker_news_evidence_with_utc_timestamp():
    item = HackerNewsItem(
        id=42,
        type="story",
        by="pg",
        time=1_700_000_000,
        title="Show HN: Acme - AI automation",
        text="<p>Acme builds tools.</p>",
        score=12,
        descendants=3,
    )

    evidence = build_hacker_news_evidence(item, "show")

    assert evidence.evidence_type == "launch_post"
    assert evidence.source_url == "https://news.ycombinator.com/item?id=42"
    assert evidence.published_at is not None
    assert evidence.published_at.tzinfo == timezone.utc
    assert evidence.metadata["hacker_news_item_id"] == 42


def test_ignores_hacker_news_url_as_company_website():
    item = HackerNewsItem(
        id=4,
        type="story",
        title="Show HN: Acme",
        url="https://news.ycombinator.com/item?id=4",
    )

    assert extract_candidate_website(item) is None
