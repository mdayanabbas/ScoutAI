from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.utils.enums import CrawlStatus


class CrawlRunCreate(BaseModel):
    company_id: str
    metadata: dict[str, Any] | None = None


class CrawlRunUpdate(BaseModel):
    status: CrawlStatus | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    pages_found: int | None = None
    pages_crawled: int | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None


class CrawlRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    status: CrawlStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    pages_found: int | None = None
    pages_crawled: int | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @field_validator("metadata", mode="before")
    @classmethod
    def ignore_non_dict_metadata(cls, value: Any) -> dict[str, Any] | None:
        return value if isinstance(value, dict) or value is None else None


class CrawlRunListItem(CrawlRunRead):
    pass
