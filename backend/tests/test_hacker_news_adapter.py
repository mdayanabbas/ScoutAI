from datetime import datetime, timezone

import pytest

from app.discovery.sources.hacker_news.adapter import HackerNewsDiscoveryAdapter
from app.discovery.sources.hacker_news.schemas import (
    HackerNewsDiscoveryRequest,
    HackerNewsItem,
)


class FakeHackerNewsClient:
    def __init__(self, items):
        self.items = items

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc_info):
        return None

    async def get_show_story_ids(self):
        return [1, 2, 3]

    async def get_job_story_ids(self):
        return [3, 4, 5]

    async def get_items(self, item_ids):
        return [self.items[item_id] for item_id in item_ids if item_id in self.items]


@pytest.mark.asyncio
async def test_adapter_combines_feeds_dedupes_and_returns_candidates():
    now = int(datetime.now(timezone.utc).timestamp())
    adapter = HackerNewsDiscoveryAdapter(
        client=FakeHackerNewsClient(
            {
                1: HackerNewsItem(id=1, type="story", title="Show HN: Acme - AI", url="https://acme.ai", time=now, score=5),
                2: HackerNewsItem(id=2, type="comment", title="comment", time=now),
                3: HackerNewsItem(id=3, type="story", title="TinyAgent is hiring", time=now, score=2),
                4: HackerNewsItem(id=4, type="story", title="DeadCo is hiring", dead=True, time=now),
                5: HackerNewsItem(id=5, type="story", title="LowScore is hiring", time=now, score=0),
            }
        )
    )

    candidates = await adapter.discover(
        HackerNewsDiscoveryRequest(limit=5, minimum_score=1)
    )

    assert [candidate.source_identifier for candidate in candidates] == ["hn:1", "hn:3"]
    assert candidates[0].website_url == "https://acme.ai"
    assert candidates[1].website_url is None
    assert candidates[0].raw_payload["feed"] == "show"
    assert adapter.skipped_item_count == 3


@pytest.mark.asyncio
async def test_adapter_excludes_items_without_website_when_configured():
    now = int(datetime.now(timezone.utc).timestamp())
    adapter = HackerNewsDiscoveryAdapter(
        client=FakeHackerNewsClient(
            {
                1: HackerNewsItem(id=1, type="story", title="TinyAgent is hiring", time=now, score=2),
            }
        )
    )

    candidates = await adapter.discover(
        HackerNewsDiscoveryRequest(
            feeds=["show"],
            limit=1,
            include_items_without_website=False,
        )
    )

    assert candidates == []
