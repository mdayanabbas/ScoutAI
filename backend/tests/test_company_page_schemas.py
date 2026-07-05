from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.company_page import (
    CompanyPageCreate,
    CompanyPageListItem,
    CompanyPageRead,
    CompanyPageUpdate,
)


class CompanyPageObj:
    id = "page-1"
    company_id = "company-1"
    url = "https://acme.ai"
    page_type = "unknown"
    title = "Acme"
    raw_text = "Long text"
    html_hash = None
    status_code = 200
    content_length = 100
    last_crawled_at = None
    created_at = datetime.now(timezone.utc)
    updated_at = None


def test_company_page_create_requires_url():
    with pytest.raises(ValidationError):
        CompanyPageCreate()


def test_company_page_update_allows_partial_update():
    assert CompanyPageUpdate(title="New").title == "New"


def test_company_page_read_supports_from_attributes():
    assert CompanyPageRead.model_validate(CompanyPageObj()).raw_text == "Long text"


def test_company_page_list_item_excludes_raw_text():
    item = CompanyPageListItem.model_validate(CompanyPageObj())
    assert "raw_text" not in item.model_dump()
