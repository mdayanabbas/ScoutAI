import pytest

from app.core.errors import NotFoundError
from app.services.company_page_service import CompanyPageService
from app.services.company_service import CompanyService
from app.utils.enums import PageType


def test_page_create_or_update_deduplicates_by_company_and_url(db_session):
    company = CompanyService(db_session).create_company(
        {"name": "Page Co", "website_url": "https://page.example"}
    )
    service = CompanyPageService(db_session)

    page = service.create_or_update_page(
        company.id,
        {
            "url": "https://www.page.example/careers/",
            "page_type": PageType.CAREERS,
            "title": "Careers",
        },
    )
    updated = service.create_or_update_page(
        company.id,
        {
            "url": "http://page.example/careers",
            "page_type": PageType.CAREERS,
            "title": "Jobs",
        },
    )

    assert updated.id == page.id
    assert updated.url == "page.example/careers"
    assert updated.title == "Jobs"
    assert service.count_company_pages(company.id) == 1


def test_page_service_missing_company_and_page_raise_not_found(db_session):
    service = CompanyPageService(db_session)

    with pytest.raises(NotFoundError):
        service.create_or_update_page("missing", {"url": "https://x.example"})

    with pytest.raises(NotFoundError):
        service.get_page("missing")
