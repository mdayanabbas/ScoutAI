from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.utils.enums import CompanySource, CompanyStage


CURRENT_YEAR = datetime.now().year


class CompanyBase(BaseModel):
    name: str
    website_url: str
    description: str | None = None
    country: str | None = None
    city: str | None = None
    stage: CompanyStage = CompanyStage.UNKNOWN
    source: CompanySource = CompanySource.OTHER
    employee_count_min: int | None = Field(default=None, ge=0)
    employee_count_max: int | None = Field(default=None, ge=0)
    founded_year: int | None = Field(default=None, ge=1800, le=CURRENT_YEAR)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_employee_range(self):
        if (
            self.employee_count_min is not None
            and self.employee_count_max is not None
            and self.employee_count_min > self.employee_count_max
        ):
            raise ValueError("employee_count_min must be <= employee_count_max")
        return self


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = None
    website_url: str | None = None
    description: str | None = None
    country: str | None = None
    city: str | None = None
    stage: CompanyStage | None = None
    source: CompanySource | None = None
    employee_count_min: int | None = Field(default=None, ge=0)
    employee_count_max: int | None = Field(default=None, ge=0)
    founded_year: int | None = Field(default=None, ge=1800, le=CURRENT_YEAR)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_employee_range(self):
        if (
            self.employee_count_min is not None
            and self.employee_count_max is not None
            and self.employee_count_min > self.employee_count_max
        ):
            raise ValueError("employee_count_min must be <= employee_count_max")
        return self


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    website_url: str | None = None
    normalized_domain: str
    created_at: datetime
    updated_at: datetime | None = None


class CompanyListItem(CompanyRead):
    pass
