from app.models.company import Company
from app.models.crawl_run import CrawlRun
from app.repositories.company_repository import CompanyRepository
from app.repositories.crawl_run_repository import CrawlRunRepository
from app.utils.enums import CrawlStatus


def test_crawl_run_repository_create_list_and_status_transitions(db_session):
    company = CompanyRepository(db_session).create_company(
        Company(name="Crawl Co", normalized_domain="crawl.example")
    )
    repo = CrawlRunRepository(db_session)
    crawl_run = repo.create_crawl_run(
        CrawlRun(company_id=company.id, status=CrawlStatus.PENDING)
    )

    assert repo.get_by_id(crawl_run.id) == crawl_run
    assert repo.list_by_company(company.id) == [crawl_run]
    assert repo.list_recent(status=CrawlStatus.PENDING) == [crawl_run]

    repo.mark_running(crawl_run)
    assert crawl_run.status == CrawlStatus.RUNNING
    assert crawl_run.started_at is not None

    repo.mark_success(crawl_run, pages_found=3, pages_crawled=2)
    assert crawl_run.status == CrawlStatus.SUCCESS
    assert crawl_run.finished_at is not None
    assert crawl_run.pages_found == 3
    assert crawl_run.pages_crawled == 2

    repo.mark_failed(crawl_run, "boom")
    assert crawl_run.status == CrawlStatus.FAILED
    assert crawl_run.error_message == "boom"
