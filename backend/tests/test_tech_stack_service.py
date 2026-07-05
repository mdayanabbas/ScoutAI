import pytest

from app.core.errors import NotFoundError
from app.services.company_service import CompanyService
from app.services.tech_stack_service import TechStackService


def test_tech_stack_create_or_update_deduplicates(db_session):
    company = CompanyService(db_session).create_company(
        {"name": "Stack Co", "website_url": "https://stack.example"}
    )
    service = TechStackService(db_session)

    item = service.create_or_update_item(
        company.id,
        {"name": "  Python  ", "source": "website", "confidence": 0.5},
    )
    updated = service.create_or_update_item(
        company.id,
        {
            "name": "Python",
            "source": "website",
            "category": "language",
            "confidence": 0.9,
        },
    )

    assert updated.id == item.id
    assert updated.name == "Python"
    assert updated.category == "language"
    assert updated.confidence == 0.9
    assert service.list_company_tech_stack(company.id) == [updated]


def test_tech_stack_missing_company_and_item_raise_not_found(db_session):
    service = TechStackService(db_session)

    with pytest.raises(NotFoundError):
        service.create_or_update_item("missing", {"name": "Python"})

    with pytest.raises(NotFoundError):
        service.delete_item("missing")
