from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TechStackItemBase(BaseModel):
    name: str
    category: str | None = None
    source: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class TechStackItemCreate(TechStackItemBase):
    pass


class TechStackItemUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    source: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class TechStackItemRead(TechStackItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    created_at: datetime
    updated_at: datetime | None = None
