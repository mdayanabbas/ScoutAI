from app.models.company import Company
from app.repositories.company_repository import CompanyRepository
from app.utils.enums import CompanySource, CompanyStage


def test_company_repository_create_lookup_list_count_update_delete(db_session):
    repo = CompanyRepository(db_session)
    company = repo.create_company(
        Company(
            name="Acme AI",
            website_url="https://acme.example",
            normalized_domain="acme.example",
            source=CompanySource.MANUAL,
            stage=CompanyStage.SEED,
            is_active=True,
        )
    )

    assert repo.get_by_id(company.id) == company
    assert repo.get_by_domain("acme.example") == company
    assert repo.get_by_website_url("https://acme.example") == company
    assert repo.list_companies(search="acme", source=CompanySource.MANUAL)[0] == company
    assert repo.count_companies(search="AI", stage=CompanyStage.SEED, is_active=True) == 1

    repo.update_company(company, {"name": "Acme Intelligence"})
    assert repo.get_by_id(company.id).name == "Acme Intelligence"

    repo.delete_company(company)
    assert repo.count_companies() == 0
