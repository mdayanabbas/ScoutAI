from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class WWRFeedDefinition:
    name: str
    feed_type: str
    feed_url: str
    enabled: bool = True
    priority: int = 0


@dataclass(frozen=True)
class WWRFeedMetadata:
    title: str | None = None
    link: str | None = None
    description: str | None = None
    last_build_date: datetime | None = None
    language: str | None = None
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True)
class WWRFeedItem:
    guid: str | None
    title: str | None
    link: str | None
    published_at: datetime | None
    description_html: str | None
    description_text: str | None
    categories: list[str] = field(default_factory=list)
    company_name: str | None = None
    role_title: str | None = None
    region_text: str | None = None
    employment_type: str | None = None
    salary_text: str | None = None
    source_feed: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WWRParseFailure:
    item_index: int
    guid: str | None = None
    validation_paths: list[str] = field(default_factory=list)
    reason: str = "malformed_item"


@dataclass(frozen=True)
class WWRFeedParseResult:
    metadata: WWRFeedMetadata
    items: list[WWRFeedItem] = field(default_factory=list)
    malformed_items: list[WWRParseFailure] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WWRFeedResponse:
    success: bool
    feed: WWRFeedDefinition
    body: bytes | None = None
    status_code: int | None = None
    reason: str | None = None
    not_modified: bool = False
    etag: str | None = None
    last_modified: str | None = None
    response_size: int | None = None
