from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import PageType


class CompanyPageBase(BaseModel):
    url: str
    page_type: PageType = PageType.UNKNOWN
    title: str | None = None
    raw_text: str | None = None
    html_hash: str | None = None
    status_code: int | None = Field(default=None, ge=100, le=599)
    content_length: int | None = Field(default=None, ge=0)
    last_crawled_at: datetime | None = None


class CompanyPageCreate(CompanyPageBase):
    pass


class CompanyPageUpdate(BaseModel):
    url: str | None = None
    page_type: PageType | None = None
    title: str | None = None
    raw_text: str | None = None
    html_hash: str | None = None
    status_code: int | None = Field(default=None, ge=100, le=599)
    content_length: int | None = Field(default=None, ge=0)
    last_crawled_at: datetime | None = None


class CompanyPageRead(CompanyPageBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    created_at: datetime
    updated_at: datetime | None = None


class CompanyPageListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    url: str
    page_type: PageType
    title: str | None = None
    html_hash: str | None = None
    status_code: int | None = None
    content_length: int | None = None
    last_crawled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
