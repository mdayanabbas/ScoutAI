import pytest

from app.core.errors import ConflictError, NotFoundError
from app.schemas.company_watchlist import CompanyWatchlistCreate, CompanyWatchlistUpdate
from app.services.company_watchlist_service import CompanyWatchlistService

from company_watchlist_helpers import create_company, create_company_job, create_job_match


def test_service_create_by_company_id_populates_fields_and_duplicate_is_blocked(db_session):
    company = create_company(db_session)
    service = CompanyWatchlistService(db_session)

    item = service.create_watchlist_item(CompanyWatchlistCreate(company_id=company.id, priority="high"))

    assert item.company_id == company.id
    assert item.company_name == company.name
    assert item.company_domain == company.normalized_domain
    assert item.priority == "high"
    with pytest.raises(ConflictError):
        service.create_watchlist_item(CompanyWatchlistCreate(company_id=company.id))


def test_service_create_by_company_name_update_archive_and_stats(db_session):
    service = CompanyWatchlistService(db_session)
    item = service.create_watchlist_item(
        CompanyWatchlistCreate(company_name="New Startup", tags=["ai"], target_roles=["ML Engineer"])
    )

    updated = service.update_watchlist_item(item.id, CompanyWatchlistUpdate(priority="low", notes="Track later"))
    assert updated.priority == "low"
    assert updated.notes == "Track later"
    assert updated.target_roles == ["ML Engineer"]
    assert service.list_watchlist_items(tag="ai").total == 1
    assert service.get_stats().total == 1

    archived = service.archive_watchlist_item(item.id)
    assert archived.watch_status == "archived"
    assert service.list_watchlist_items().total == 0


def test_service_archived_duplicate_reactivates(db_session):
    service = CompanyWatchlistService(db_session)
    item = service.create_watchlist_item(CompanyWatchlistCreate(company_name="Tether"))
    service.archive_watchlist_item(item.id)

    reactivated = service.create_watchlist_item(CompanyWatchlistCreate(company_name="Tether", priority="high"))

    assert reactivated.id == item.id
    assert reactivated.watch_status == "watching"
    assert reactivated.priority == "high"


def test_service_watch_from_job_sets_target_role_and_jobs_endpoint(db_session):
    company = create_company(db_session)
    job = create_company_job(db_session, company, title="Machine Learning Engineer")
    create_job_match(db_session, job)
    service = CompanyWatchlistService(db_session)

    item = service.watch_company_from_job(job.id)
    jobs = service.list_jobs_for_item(item.id, recommended_only=True)

    assert item.company_id == company.id
    assert "ai_engineer" in item.target_roles
    assert jobs.total == 1
    assert jobs.jobs[0].title == "Machine Learning Engineer"
    assert jobs.jobs[0].match_tier == "strong_match"


def test_service_missing_company_job_and_item_return_not_found(db_session):
    service = CompanyWatchlistService(db_session)

    with pytest.raises(NotFoundError):
        service.create_watchlist_item(CompanyWatchlistCreate(company_id="missing"))
    with pytest.raises(NotFoundError):
        service.watch_company_from_job("missing")
    with pytest.raises(NotFoundError):
        service.get_watchlist_item("missing")

