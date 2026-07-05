import pytest

from app.core.errors import ConflictError, NotFoundError
from app.services.company_service import CompanyService


def test_company_creation_normalizes_domain(db_session):
    service = CompanyService(db_session)

    company = service.create_company(
        {"name": "Acme AI", "website_url": "https://www.acme.ai/"}
    )

    assert company.website_url == "acme.ai"
    assert company.normalized_domain == "acme.ai"
    assert service.get_company_by_domain("https://www.acme.ai") == company


def test_duplicate_company_domain_raises_conflict(db_session):
    service = CompanyService(db_session)
    service.create_company({"name": "Acme AI", "website_url": "https://acme.ai"})

    with pytest.raises(ConflictError):
        service.create_company(
            {"name": "Acme Again", "website_url": "http://www.acme.ai/"}
        )


def test_missing_company_raises_not_found(db_session):
    service = CompanyService(db_session)

    with pytest.raises(NotFoundError):
        service.get_company("missing")


def test_company_update_and_delete(db_session):
    service = CompanyService(db_session)
    company = service.create_company(
        {"name": "Old", "website_url": "https://old.example"}
    )

    updated = service.update_company(company.id, {"name": "New"})
    assert updated.name == "New"
    assert service.count_companies(search="New") == 1

    service.delete_company(company.id)
    assert service.count_companies() == 0
