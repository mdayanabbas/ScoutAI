from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.crawl_run import CrawlRun
from app.repositories.company_repository import CompanyRepository
from app.repositories.crawl_run_repository import CrawlRunRepository
from app.utils.enums import CrawlStatus


class CrawlRunService:
    def __init__(self, session: Session) -> None:
        self.company_repository = CompanyRepository(session)
        self.repository = CrawlRunRepository(session)

    def _require_company(self, company_id: str) -> None:
        if self.company_repository.get_by_id(company_id) is None:
            raise NotFoundError("Company not found")

    def _require_crawl_run(self, crawl_run_id: str) -> CrawlRun:
        crawl_run = self.repository.get_by_id(crawl_run_id)
        if crawl_run is None:
            raise NotFoundError("Crawl run not found")
        return crawl_run

    def create_crawl_run(self, company_id: str) -> CrawlRun:
        self._require_company(company_id)
        return self.repository.create_crawl_run(
            CrawlRun(company_id=company_id, status=CrawlStatus.PENDING)
        )

    def mark_running(self, crawl_run_id: str) -> CrawlRun:
        return self.repository.mark_running(self._require_crawl_run(crawl_run_id))

    def mark_success(
        self,
        crawl_run_id: str,
        pages_found: int | None = None,
        pages_crawled: int | None = None,
    ) -> CrawlRun:
        return self.repository.mark_success(
            self._require_crawl_run(crawl_run_id),
            pages_found=pages_found,
            pages_crawled=pages_crawled,
        )

    def mark_failed(self, crawl_run_id: str, error_message: str) -> CrawlRun:
        return self.repository.mark_failed(
            self._require_crawl_run(crawl_run_id), error_message
        )

    def list_company_runs(
        self, company_id: str, offset: int = 0, limit: int = 50
    ) -> list[CrawlRun]:
        self._require_company(company_id)
        return self.repository.list_by_company(company_id, offset=offset, limit=limit)

    def list_recent_runs(
        self, offset: int = 0, limit: int = 50, status: str | None = None
    ) -> list[CrawlRun]:
        return self.repository.list_recent(offset=offset, limit=limit, status=status)
