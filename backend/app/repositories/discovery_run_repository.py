from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.discovery_run import DiscoveryRun
from app.repositories.base import BaseRepository
from app.utils.enums import DiscoveryRunStatus, DiscoverySource


class DiscoveryRunRepository(BaseRepository[DiscoveryRun]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DiscoveryRun)

    def create_run(self, run: DiscoveryRun) -> DiscoveryRun:
        return self.create(run)

    def list_runs(
        self,
        offset: int = 0,
        limit: int = 50,
        source: DiscoverySource | None = None,
        status: DiscoveryRunStatus | None = None,
    ) -> list[DiscoveryRun]:
        stmt = self._build_list_query(source=source, status=status)
        stmt = stmt.order_by(DiscoveryRun.created_at.desc()).offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def count_runs(
        self,
        source: DiscoverySource | None = None,
        status: DiscoveryRunStatus | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(
            self._build_list_query(source=source, status=status).subquery()
        )
        return self.session.scalar(stmt) or 0

    def _build_list_query(
        self,
        source: DiscoverySource | None = None,
        status: DiscoveryRunStatus | None = None,
    ):
        stmt = select(DiscoveryRun)
        if source is not None:
            stmt = stmt.where(DiscoveryRun.source == source)
        if status is not None:
            stmt = stmt.where(DiscoveryRun.status == status)
        return stmt

    def mark_running(self, run: DiscoveryRun) -> DiscoveryRun:
        return self.update(
            run,
            {
                "status": DiscoveryRunStatus.RUNNING,
                "started_at": datetime.now(timezone.utc),
            },
        )

    def mark_success(self, run: DiscoveryRun, counters: dict[str, Any]) -> DiscoveryRun:
        return self._mark_finished(run, DiscoveryRunStatus.SUCCESS, counters)

    def mark_partial_success(
        self, run: DiscoveryRun, counters: dict[str, Any]
    ) -> DiscoveryRun:
        return self._mark_finished(run, DiscoveryRunStatus.PARTIAL_SUCCESS, counters)

    def mark_failed(
        self,
        run: DiscoveryRun,
        error_message: str,
        counters: dict[str, Any] | None = None,
    ) -> DiscoveryRun:
        values = dict(counters or {})
        values.update(
            {
                "status": DiscoveryRunStatus.FAILED,
                "finished_at": datetime.now(timezone.utc),
                "error_message": error_message,
            }
        )
        return self.update(run, values)

    def _mark_finished(
        self,
        run: DiscoveryRun,
        status: DiscoveryRunStatus,
        counters: dict[str, Any],
    ) -> DiscoveryRun:
        values = dict(counters)
        values.update({"status": status, "finished_at": datetime.now(timezone.utc)})
        return self.update(run, values)
