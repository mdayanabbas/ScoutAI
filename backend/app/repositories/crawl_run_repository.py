from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.crawl_run import CrawlRun
from app.repositories.base import BaseRepository
from app.utils.enums import CrawlStatus


class CrawlRunRepository(BaseRepository[CrawlRun]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, CrawlRun)

    def list_by_company(
        self, company_id: str, offset: int = 0, limit: int = 50
    ) -> list[CrawlRun]:
        stmt = (
            select(CrawlRun)
            .where(CrawlRun.company_id == company_id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def list_recent(
        self,
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> list[CrawlRun]:
        stmt = select(CrawlRun)
        if status is not None:
            stmt = stmt.where(CrawlRun.status == status)
        stmt = stmt.order_by(CrawlRun.created_at.desc()).offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def create_crawl_run(self, crawl_run: CrawlRun) -> CrawlRun:
        return self.create(crawl_run)

    def update_crawl_run(
        self, crawl_run: CrawlRun, data: dict[str, Any]
    ) -> CrawlRun:
        return self.update(crawl_run, data)

    def mark_running(self, crawl_run: CrawlRun) -> CrawlRun:
        crawl_run.status = CrawlStatus.RUNNING
        crawl_run.started_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(crawl_run)
        return crawl_run

    def mark_success(
        self,
        crawl_run: CrawlRun,
        pages_found: int | None = None,
        pages_crawled: int | None = None,
    ) -> CrawlRun:
        crawl_run.status = CrawlStatus.SUCCESS
        crawl_run.finished_at = datetime.now(timezone.utc)
        if pages_found is not None:
            crawl_run.pages_found = pages_found
        if pages_crawled is not None:
            crawl_run.pages_crawled = pages_crawled
        self.session.commit()
        self.session.refresh(crawl_run)
        return crawl_run

    def mark_failed(self, crawl_run: CrawlRun, error_message: str) -> CrawlRun:
        crawl_run.status = CrawlStatus.FAILED
        crawl_run.finished_at = datetime.now(timezone.utc)
        crawl_run.error_message = error_message
        self.session.commit()
        self.session.refresh(crawl_run)
        return crawl_run
