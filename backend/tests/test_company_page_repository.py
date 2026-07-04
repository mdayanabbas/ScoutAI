from app.models.company import Company
from app.models.company_page import CompanyPage
from app.repositories.company_page_repository import CompanyPageRepository
from app.repositories.company_repository import CompanyRepository
from app.utils.enums import PageType


def test_company_page_repository_create_lookup_list_count(db_session):
    company = CompanyRepository(db_session).create_company(
        Company(name="Page Co", normalized_domain="page.example")
    )
    repo = CompanyPageRepository(db_session)
    page = repo.create_page(
        CompanyPage(
            company_id=company.id,
            url="https://page.example/careers",
            page_type=PageType.CAREERS,
            title="Careers",
        )
    )

    assert repo.get_by_id(page.id) == page
    assert repo.get_by_company_and_url(company.id, "https://page.example/careers") == page
    assert repo.list_by_company(company.id, page_type=PageType.CAREERS) == [page]
    assert repo.count_by_company(company.id, page_type=PageType.CAREERS) == 1

    repo.update_page(page, {"title": "Jobs"})
    assert repo.get_by_id(page.id).title == "Jobs"

    repo.delete_page(page)
    assert repo.count_by_company(company.id) == 0
