from app.models.company_watchlist import CompanyWatchlistItem
from app.repositories.company_watchlist_repository import CompanyWatchlistRepository

from company_watchlist_helpers import create_company, create_company_job, create_job_match


def test_repository_create_get_list_update_archive_delete_and_duplicates(db_session):
    company = create_company(db_session)
    repo = CompanyWatchlistRepository(db_session)

    item = repo.create(
        CompanyWatchlistItem(
            company_id=company.id,
            company_name=company.name,
            company_domain=company.normalized_domain,
            normalized_company_name="tether",
            normalized_domain=company.normalized_domain,
            watch_status="watching",
            priority="high",
            remote_interest="unknown",
            junior_friendliness_signal="unknown",
        )
    )

    assert repo.get_by_id(item.id).company_id == company.id
    assert repo.count_items() == 1
    assert repo.list_items()[0].id == item.id
    assert repo.find_active_duplicate(
        company_id=company.id,
        normalized_company_name="tether",
        normalized_domain=company.normalized_domain,
    ).id == item.id

    updated = repo.update(item, {"priority": "low"})
    assert updated.priority == "low"
    archived = repo.archive(updated)
    assert archived.watch_status == "archived"
    assert repo.list_items() == []
    assert len(repo.list_items(include_archived=True)) == 1
    repo.delete(archived)
    assert repo.get_by_id(item.id) is None


def test_repository_stats_and_jobs_for_company(db_session):
    company = create_company(db_session)
    job = create_company_job(db_session, company)
    create_job_match(db_session, job)
    repo = CompanyWatchlistRepository(db_session)
    item = repo.create(
        CompanyWatchlistItem(
            company_id=company.id,
            company_name=company.name,
            company_domain=company.normalized_domain,
            normalized_company_name="tether",
            normalized_domain=company.normalized_domain,
            watch_status="watching",
            priority="high",
            remote_interest="unknown",
            junior_friendliness_signal="unknown",
        )
    )

    assert repo.count_jobs_for_company(item) == 1
    assert repo.count_recommended_jobs_for_company(item) == 1
    assert repo.get_latest_job_for_company(item).id == job.id
    rows = repo.list_jobs_for_watchlist_item(item, recommended_only=True)
    assert rows[0][0].id == job.id
    assert rows[0][1].match_tier == "strong_match"
    stats = repo.get_stats()
    assert stats["total"] == 1
    assert stats["with_recommended_jobs"] == 1

