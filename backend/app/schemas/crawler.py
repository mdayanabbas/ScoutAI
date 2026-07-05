from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

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

    @model_validator(mode="before")
    @classmethod
    def map_metadata_json(cls, value: Any) -> Any:
        if isinstance(value, dict):
            if "metadata" not in value and "metadata_json" in value:
                value["metadata"] = value["metadata_json"]
            return value

        if hasattr(value, "metadata_json"):
            return {
                "id": value.id,
                "company_id": value.company_id,
                "status": value.status,
                "started_at": value.started_at,
                "finished_at": value.finished_at,
                "pages_found": value.pages_found,
                "pages_crawled": value.pages_crawled,
                "error_message": value.error_message,
                "metadata": value.metadata_json,
                "created_at": value.created_at,
                "updated_at": value.updated_at,
            }
        return value


class CrawlRunListItem(CrawlRunRead):
    pass


class CrawlRunMarkSuccessRequest(BaseModel):
    pages_found: int | None = Field(default=None, ge=0)
    pages_crawled: int | None = Field(default=None, ge=0)


class CrawlRunMarkFailedRequest(BaseModel):
    error_message: str = Field(min_length=1)
