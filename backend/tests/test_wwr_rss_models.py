from datetime import datetime, timezone

from app.discovery.sources.we_work_remotely.models import (
    WWRFeedDefinition,
    WWRFeedItem,
    WWRFeedMetadata,
    WWRFeedParseResult,
    WWRFeedResponse,
    WWRParseFailure,
)


def test_wwr_feed_models_hold_safe_structured_data():
    feed = WWRFeedDefinition(
        name="Remote Programming Jobs",
        feed_type="programming",
        feed_url="https://weworkremotely.com/categories/remote-programming-jobs.rss",
    )
    published_at = datetime(2026, 7, 14, tzinfo=timezone.utc)
    item = WWRFeedItem(
        guid="wwr-1",
        title="Remote AI Co: Junior AI Engineer",
        link="https://weworkremotely.com/remote-jobs/remote-ai-junior-ai-engineer",
        published_at=published_at,
        description_html="<p>Anywhere in the World</p>",
        description_text="Anywhere in the World",
        company_name="Remote AI Co",
        role_title="Junior AI Engineer",
        source_feed="programming",
    )
    failure = WWRParseFailure(1, "bad", ["link"], "invalid_link")
    parsed = WWRFeedParseResult(
        metadata=WWRFeedMetadata(title="Remote Programming Jobs"),
        items=[item],
        malformed_items=[failure],
    )
    response = WWRFeedResponse(True, feed, body=b"<rss />", status_code=200, etag='"abc"')

    assert parsed.items[0].company_name == "Remote AI Co"
    assert parsed.malformed_items[0].reason == "invalid_link"
    assert response.feed.feed_type == "programming"
    assert response.etag == '"abc"'
