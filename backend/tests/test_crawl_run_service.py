import pytest

from app.core.errors import NotFoundError
from app.services.company_service import CompanyService
from app.services.crawl_run_service import CrawlRunService
from app.utils.enums import CrawlStatus


def test_crawl_run_status_transitions(db_session):
    company = CompanyService(db_session).create_company(
        {"name": "Crawl Co", "website_url": "https://crawl.example"}
    )
    service = CrawlRunService(db_session)
    crawl_run = service.create_crawl_run(
        company.id, {"metadata": {"source": "manual_test"}}
    )

    assert crawl_run.status == CrawlStatus.PENDING
    assert crawl_run.metadata_json == {"source": "manual_test"}
    assert service.list_company_runs(company.id) == [crawl_run]

    running = service.mark_running(crawl_run.id)
    assert running.status == CrawlStatus.RUNNING
    assert running.started_at is not None
    assert running.metadata_json == {"source": "manual_test"}

    success = service.mark_success(crawl_run.id, pages_found=3, pages_crawled=2)
    assert success.status == CrawlStatus.SUCCESS
    assert success.pages_found == 3
    assert success.pages_crawled == 2
    assert success.metadata_json == {"source": "manual_test"}

    failed = service.mark_failed(crawl_run.id, "failed")
    assert failed.status == CrawlStatus.FAILED
    assert failed.error_message == "failed"
    assert failed.metadata_json == {"source": "manual_test"}


def test_crawl_run_missing_company_or_run_raise_not_found(db_session):
    service = CrawlRunService(db_session)

    with pytest.raises(NotFoundError):
        service.create_crawl_run("missing")

    with pytest.raises(NotFoundError):
        service.mark_running("missing")
