import logging
from datetime import datetime, timedelta, timezone

from app.discovery.adapters.base import StartupSourceAdapter
from app.discovery.sources.hacker_news.client import HackerNewsClient
from app.discovery.sources.hacker_news.parser import (
    build_candidate_description,
    build_hacker_news_evidence,
    extract_candidate_name,
    is_candidate_item,
)
from app.discovery.url_classifier import classify_candidate_url
from app.discovery.sources.hacker_news.schemas import (
    HackerNewsDiscoveryRequest,
    HackerNewsItem,
)
from app.schemas.discovery import RawStartupCandidate
from app.utils.enums import DiscoverySource

logger = logging.getLogger(__name__)


class HackerNewsDiscoveryAdapter(StartupSourceAdapter):
    source = DiscoverySource.HACKER_NEWS

    def __init__(self, client: HackerNewsClient | None = None) -> None:
        self.client = client or HackerNewsClient()
        self.fetched_item_count = 0
        self.skipped_item_count = 0

    async def discover(
        self, request: object | None = None
    ) -> list[RawStartupCandidate]:
        if not isinstance(request, HackerNewsDiscoveryRequest):
            raise ValueError("HackerNewsDiscoveryAdapter requires HackerNewsDiscoveryRequest")

        logger.info(
            "Hacker News discovery adapter started",
            extra={"feeds": request.feeds, "limit": request.limit},
        )
        item_ids_by_feed = await self._get_item_ids_by_feed(request)
        selected = self._select_balanced_item_ids(item_ids_by_feed, request.limit)
        feed_by_id = {item_id: feed for feed, item_ids in selected for item_id in item_ids}
        item_ids = [item_id for _feed, item_ids in selected for item_id in item_ids]

        async with self.client:
            items = await self.client.get_items(item_ids)

        self.fetched_item_count = len(items)
        candidates: list[RawStartupCandidate] = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=request.lookback_days)
        for item in items:
            feed = feed_by_id.get(item.id)
            if not self._is_within_lookback(item, cutoff):
                self.skipped_item_count += 1
                continue
            if not is_candidate_item(item, request):
                self.skipped_item_count += 1
                continue
            candidate = self._to_candidate(item, feed)
            if candidate is None:
                self.skipped_item_count += 1
                continue
            candidates.append(candidate)

        logger.info(
            "Hacker News discovery adapter completed",
            extra={
                "items_fetched": self.fetched_item_count,
                "items_skipped": self.skipped_item_count,
                "candidates_produced": len(candidates),
            },
        )
        return candidates

    async def _get_item_ids_by_feed(
        self, request: HackerNewsDiscoveryRequest
    ) -> dict[str, list[int]]:
        async with self.client:
            result: dict[str, list[int]] = {}
            if "show" in request.feeds:
                result["show"] = await self.client.get_show_story_ids()
            if "jobs" in request.feeds:
                result["jobs"] = await self.client.get_job_story_ids()
        logger.info(
            "Hacker News item IDs retrieved",
            extra={f"{feed}_ids": len(ids) for feed, ids in result.items()},
        )
        if not result or all(len(ids) == 0 for ids in result.values()):
            raise RuntimeError("No Hacker News feed item IDs could be retrieved")
        return result

    def _select_balanced_item_ids(
        self, item_ids_by_feed: dict[str, list[int]], limit: int
    ) -> list[tuple[str, list[int]]]:
        feeds = list(item_ids_by_feed)
        selected: dict[str, list[int]] = {feed: [] for feed in feeds}
        seen: set[int] = set()
        while len(seen) < limit:
            progressed = False
            for feed in feeds:
                while item_ids_by_feed[feed]:
                    item_id = item_ids_by_feed[feed].pop(0)
                    if item_id in seen:
                        continue
                    selected[feed].append(item_id)
                    seen.add(item_id)
                    progressed = True
                    break
                if len(seen) >= limit:
                    break
            if not progressed:
                break
        return [(feed, ids) for feed, ids in selected.items()]

    def _to_candidate(
        self, item: HackerNewsItem, feed: str | None
    ) -> RawStartupCandidate | None:
        classification = classify_candidate_url(item.url)
        name = extract_candidate_name(item) or self._name_from_external_slug(
            classification.external_company_slug
        )
        if not name:
            return None
        evidence = build_hacker_news_evidence(item, feed)
        raw_payload = {
            "id": item.id,
            "type": item.type,
            "by": item.by,
            "time": item.time,
            "title": item.title,
            "url": item.url,
            "text": item.text,
            "score": item.score,
            "descendants": item.descendants,
            "feed": feed,
            "url_classification": classification.model_dump(),
        }
        return RawStartupCandidate(
            source_identifier=f"hn:{item.id}",
            name=name,
            website_url=classification.first_party_url,
            description=build_candidate_description(item),
            country=None,
            evidence=[evidence],
            raw_payload=raw_payload,
        )

    def _is_within_lookback(self, item: HackerNewsItem, cutoff: datetime) -> bool:
        if item.time is None:
            return True
        return datetime.fromtimestamp(item.time, timezone.utc) >= cutoff

    def _name_from_external_slug(self, slug: str | None) -> str | None:
        if not slug:
            return None
        return " ".join(part.capitalize() for part in slug.replace("_", "-").split("-") if part)
