from app.discovery.sources.we_work_remotely.models import WWRFeedDefinition
from app.discovery.sources.we_work_remotely.parser import WeWorkRemotelyRSSParser


FEED = WWRFeedDefinition(
    name="Remote Programming Jobs",
    feed_type="programming",
    feed_url="https://weworkremotely.com/categories/remote-programming-jobs.rss",
)


def _rss(items: str) -> bytes:
    return f"""<?xml version="1.0"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Remote Programming Jobs</title>
    <link>https://weworkremotely.com/categories/remote-programming-jobs</link>
    <description>Remote jobs</description>
    <lastBuildDate>Tue, 14 Jul 2026 10:00:00 GMT</lastBuildDate>
    <language>en</language>
    {items}
  </channel>
</rss>""".encode()


def test_parser_extracts_namespaced_content_and_normalized_title_parts():
    body = _rss(
        """
        <item>
          <guid>wwr-ai-1</guid>
          <title>Remote AI Co: Junior AI Engineer</title>
          <link>https://weworkremotely.com/remote-jobs/remote-ai-junior-ai-engineer?utm_source=rss</link>
          <pubDate>Tue, 14 Jul 2026 09:00:00 GMT</pubDate>
          <category>Programming</category>
          <content:encoded><![CDATA[
            <p>Anywhere in the World</p>
            <p>Full-Time</p>
            <p>$80K - $120K</p>
          ]]></content:encoded>
        </item>
        """
    )

    result = WeWorkRemotelyRSSParser().parse(body, feed=FEED)

    assert result.warnings == []
    assert len(result.items) == 1
    item = result.items[0]
    assert item.company_name == "Remote AI Co"
    assert item.role_title == "Junior AI Engineer"
    assert item.link == "https://weworkremotely.com/remote-jobs/remote-ai-junior-ai-engineer"
    assert item.employment_type == "full_time"
    assert item.salary_text == "$80K - $120K"


def test_parser_isolates_invalid_item_links():
    body = _rss(
        """
        <item>
          <guid>bad-link</guid>
          <title>Remote AI Co: AI Engineer</title>
          <link>https://example.com/not-wwr</link>
          <description>Remote worldwide</description>
        </item>
        <item>
          <guid>good-link</guid>
          <title>Remote AI Co: Backend Engineer</title>
          <link>https://weworkremotely.com/remote-jobs/remote-ai-backend-engineer</link>
          <description>Remote worldwide</description>
        </item>
        """
    )

    result = WeWorkRemotelyRSSParser().parse(body, feed=FEED)

    assert [item.guid for item in result.items] == ["good-link"]
    assert result.malformed_items[0].guid == "bad-link"
    assert result.malformed_items[0].reason == "invalid_link"


def test_parser_rejects_unsafe_or_malformed_xml():
    unsafe = b"<!DOCTYPE rss [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><rss />"
    result = WeWorkRemotelyRSSParser().parse(unsafe, feed=FEED)
    assert result.warnings == ["wwr_unsafe_xml"]

    malformed = WeWorkRemotelyRSSParser().parse(b"<rss><channel>", feed=FEED)
    assert malformed.warnings == ["wwr_invalid_xml"]
