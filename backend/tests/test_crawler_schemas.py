from datetime import datetime, timezone

from app.schemas.crawler import CrawlRunCreate, CrawlRunRead, CrawlRunUpdate


class CrawlRunObj:
    id = "crawl-1"
    company_id = "company-1"
    status = "pending"
    started_at = None
    finished_at = None
    pages_found = None
    pages_crawled = None
    error_message = None
    metadata_json = {"source": "manual"}
    created_at = datetime.now(timezone.utc)
    updated_at = None


def test_crawl_run_create_accepts_company_id():
    assert CrawlRunCreate(company_id="company-1").company_id == "company-1"


def test_crawl_run_update_allows_partial_update():
    assert CrawlRunUpdate(error_message="failed").error_message == "failed"


def test_crawl_run_read_supports_from_attributes():
    assert CrawlRunRead.model_validate(CrawlRunObj()).metadata == {"source": "manual"}
