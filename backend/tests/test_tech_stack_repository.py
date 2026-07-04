from app.models.company import Company
from app.models.tech_stack_item import TechStackItem
from app.repositories.company_repository import CompanyRepository
from app.repositories.tech_stack_repository import TechStackRepository


def test_tech_stack_repository_create_lookup_list_update_delete(db_session):
    company = CompanyRepository(db_session).create_company(
        Company(name="Stack Co", normalized_domain="stack.example")
    )
    repo = TechStackRepository(db_session)
    item = repo.create_item(
        TechStackItem(
            company_id=company.id,
            name="Python",
            category="language",
            source="website",
            confidence=0.9,
        )
    )

    assert repo.get_by_id(item.id) == item
    assert repo.get_by_company_and_name(company.id, "Python", source="website") == item
    assert repo.list_by_company(company.id) == [item]

    repo.update_item(item, {"confidence": 1.0})
    assert repo.get_by_id(item.id).confidence == 1.0

    repo.delete_item(item)
    assert repo.list_by_company(company.id) == []
