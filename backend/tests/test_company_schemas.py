from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate


class CompanyObj:
    id = "company-1"
    name = "Acme AI"
    website_url = "https://acme.ai"
    normalized_domain = "acme.ai"
    description = None
    country = None
    city = None
    stage = "unknown"
    source = "other"
    employee_count_min = None
    employee_count_max = None
    founded_year = None
    is_active = True
    created_at = datetime.now(timezone.utc)
    updated_at = None


def test_company_create_requires_name_and_website_url():
    with pytest.raises(ValidationError):
        CompanyCreate(name="Acme AI")


def test_company_update_allows_partial_update():
    assert CompanyUpdate(name="New Name").name == "New Name"


def test_company_read_supports_from_attributes():
    assert CompanyRead.model_validate(CompanyObj()).normalized_domain == "acme.ai"


def test_invalid_employee_count_range_fails():
    with pytest.raises(ValidationError):
        CompanyCreate(
            name="Acme AI",
            website_url="https://acme.ai",
            employee_count_min=10,
            employee_count_max=5,
        )
