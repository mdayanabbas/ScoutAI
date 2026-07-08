from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import get_settings
from app.schemas.discovery import DiscoveryCandidateRead, DiscoveryRunRead

HackerNewsFeed = Literal["show", "jobs"]


class HackerNewsItem(BaseModel):
    id: int
    type: str | None = None
    by: str | None = None
    time: int | None = None
    title: str | None = None
    url: str | None = None
    text: str | None = None
    score: int | None = None
    descendants: int | None = None
    deleted: bool = False
    dead: bool = False


class HackerNewsDiscoveryRequest(BaseModel):
    model_config = ConfigDict(validate_default=True)

    feeds: list[HackerNewsFeed] = Field(default_factory=lambda: ["show", "jobs"])
    limit: int = Field(default_factory=lambda: get_settings().HACKER_NEWS_DEFAULT_LIMIT)
    lookback_days: int = Field(
        default_factory=lambda: get_settings().HACKER_NEWS_DEFAULT_LOOKBACK_DAYS
    )
    minimum_score: int | None = Field(default=None, ge=0)
    include_items_without_website: bool = True
    metadata: dict[str, Any] | None = None

    @field_validator("feeds")
    @classmethod
    def validate_feeds(cls, value: list[HackerNewsFeed]) -> list[HackerNewsFeed]:
        if not value:
            raise ValueError("at least one feed is required")
        return value

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, value: int) -> int:
        max_limit = get_settings().HACKER_NEWS_MAX_LIMIT
        if value < 1 or value > max_limit:
            raise ValueError(f"limit must be between 1 and {max_limit}")
        return value

    @field_validator("lookback_days")
    @classmethod
    def validate_lookback_days(cls, value: int) -> int:
        if value < 1 or value > 365:
            raise ValueError("lookback_days must be between 1 and 365")
        return value


class HackerNewsDiscoveryResponse(BaseModel):
    run: DiscoveryRunRead
    candidates: list[DiscoveryCandidateRead]
    fetched_item_count: int
    skipped_item_count: int
