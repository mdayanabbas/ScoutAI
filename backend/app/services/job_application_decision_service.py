from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.job_application_decision import JobApplicationDecision
from app.repositories.job_application_decision_repository import JobApplicationDecisionRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import UserProfileRepository
from app.schemas.job_application_decision import (
    JobApplicationDecisionCreate,
    JobApplicationDecisionListItemRead,
    JobApplicationDecisionListRead,
    JobApplicationDecisionStatusCountsRead,
    JobApplicationDecisionUpdate,
)


class JobApplicationDecisionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = JobApplicationDecisionRepository(session)
        self.job_repository = JobRepository(session)
        self.user_profile_repository = UserProfileRepository(session)

    def create_or_update_for_job(self, job_id: str, data: JobApplicationDecisionCreate) -> JobApplicationDecision:
        job = self.job_repository.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job not found")
        user_profile = self._current_user_profile()
        existing = self.repository.get_by_job_and_user_profile(job.id, user_profile.id)
        values = {
            "status": data.status.value,
            "notes": data.notes,
            "decided_at": datetime.now(timezone.utc),
            "archived_at": datetime.now(timezone.utc) if data.status.value == "archived" else None,
        }
        if existing is not None:
            return self.repository.update(existing, values)
        return self.repository.create(
            JobApplicationDecision(
                job_id=job.id,
                user_profile_id=user_profile.id,
                **values,
            )
        )

    def get_for_job(self, job_id: str) -> JobApplicationDecision:
        if self.job_repository.get_by_id(job_id) is None:
            raise NotFoundError("Job not found")
        user_profile = self._current_user_profile()
        decision = self.repository.get_by_job_and_user_profile(job_id, user_profile.id)
        if decision is None:
            raise NotFoundError("Job application decision not found")
        return decision

    def update_decision(self, decision_id: str, data: JobApplicationDecisionUpdate) -> JobApplicationDecision:
        decision = self._get_current_decision(decision_id)
        values = data.model_dump(exclude_unset=True)
        if "status" in values and values["status"] is not None:
            status = values["status"].value
            values["status"] = status
            values["decided_at"] = datetime.now(timezone.utc)
            values["archived_at"] = datetime.now(timezone.utc) if status == "archived" else None
        return self.repository.update(decision, values)

    def archive_decision(self, decision_id: str) -> JobApplicationDecision:
        decision = self._get_current_decision(decision_id)
        now = datetime.now(timezone.utc)
        return self.repository.update(decision, {"status": "archived", "archived_at": now, "decided_at": now})

    def delete_decision(self, decision_id: str) -> None:
        decision = self._get_current_decision(decision_id)
        self.repository.delete(decision)

    def list_decisions(
        self,
        *,
        status: str | None = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> JobApplicationDecisionListRead:
        user_profile = self._current_user_profile()
        decisions = self.repository.list_for_user_profile(
            user_profile.id,
            status=status,
            include_archived=include_archived,
            limit=limit,
            offset=offset,
        )
        total = self.repository.count_for_user_profile(
            user_profile.id,
            status=status,
            include_archived=include_archived,
        )
        return JobApplicationDecisionListRead(
            items=[_list_item(decision) for decision in decisions],
            total=total,
            limit=limit,
            offset=offset,
        )

    def status_counts(self) -> JobApplicationDecisionStatusCountsRead:
        user_profile = self._current_user_profile()
        counts = self.repository.status_counts(user_profile.id)
        return JobApplicationDecisionStatusCountsRead(
            interested=counts.get("interested", 0),
            applied=counts.get("applied", 0),
            dismissed=counts.get("dismissed", 0),
            archived=counts.get("archived", 0),
            total=sum(counts.values()),
        )

    def _current_user_profile(self):
        user_profile = self.user_profile_repository.get_first_profile()
        if user_profile is None:
            raise NotFoundError("User profile not found")
        return user_profile

    def _get_current_decision(self, decision_id: str) -> JobApplicationDecision:
        user_profile = self._current_user_profile()
        decision = self.repository.get_by_id(decision_id)
        if decision is None or decision.user_profile_id != user_profile.id:
            raise NotFoundError("Job application decision not found")
        return decision


def _list_item(decision: JobApplicationDecision) -> JobApplicationDecisionListItemRead:
    job = decision.job
    return JobApplicationDecisionListItemRead(
        id=decision.id,
        job_id=decision.job_id,
        user_profile_id=decision.user_profile_id,
        status=decision.status,
        notes=decision.notes,
        decided_at=decision.decided_at,
        archived_at=decision.archived_at,
        created_at=decision.created_at,
        updated_at=decision.updated_at,
        job_title=getattr(job, "title", None),
        company_id=getattr(job, "company_id", None),
    )
