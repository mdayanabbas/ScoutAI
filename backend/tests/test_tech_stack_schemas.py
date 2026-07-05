from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.tech_stack_item import (
    TechStackItemCreate,
    TechStackItemRead,
    TechStackItemUpdate,
)


class TechStackObj:
    id = "item-1"
    company_id = "company-1"
    name = "Python"
    category = "language"
    source = "website"
    confidence = 0.9
    created_at = datetime.now(timezone.utc)
    updated_at = None


def test_tech_stack_create_requires_name():
    with pytest.raises(ValidationError):
        TechStackItemCreate()


def test_tech_stack_update_allows_partial_update():
    assert TechStackItemUpdate(confidence=0.5).confidence == 0.5


def test_tech_stack_read_supports_from_attributes():
    assert TechStackItemRead.model_validate(TechStackObj()).company_id == "company-1"


def test_invalid_confidence_outside_range_fails():
    with pytest.raises(ValidationError):
        TechStackItemCreate(name="Python", confidence=1.5)
