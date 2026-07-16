import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.job import Job
from app.models.job_application_decision import JobApplicationDecision
from app.models.job_match import JobMatch
from app.models.job_matching_profile import JobMatchingProfile
from app.models.user_profile import UserProfile
from app.repositories.job_application_decision_repository import JobApplicationDecisionRepository
from app.repositories.job_match_repository import JobMatchRepository
from app.repositories.job_matching_profile_repository import JobMatchingProfileRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import UserProfileRepository
from app.schemas.application_prep import (
    ApplicationPrepListItem,
    ApplicationPrepRequest,
    ApplicationPrepResponse,
)
from app.utils.text import normalize_title

logger = logging.getLogger(__name__)


class ApplicationPrepService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.job_repository = JobRepository(session)
        self.user_profile_repository = UserProfileRepository(session)
        self.profile_repository = JobMatchingProfileRepository(session)
        self.match_repository = JobMatchRepository(session)
        self.decision_repository = JobApplicationDecisionRepository(session)

    def generate_for_job(self, job_id: str, request: ApplicationPrepRequest) -> ApplicationPrepResponse:
        job = self.job_repository.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job not found")
        user_profile, matching_profile = self._current_profiles()
        match = self._match_for(matching_profile, job.id)
        decision = self.decision_repository.get_by_job_and_user_profile(job.id, user_profile.id)
        response = self._build_response(job, user_profile, matching_profile, match, decision, request)
        if request.update_decision:
            decision = self._upsert_decision(job, user_profile, match, decision, response)
            response.decision_id = decision.id
            logger.info("Application prep decision updated", extra={"job_id": job.id, "decision_id": decision.id})
        logger.info("Application prep generated", extra={"job_id": job.id, "decision_id": response.decision_id})
        return response

    def generate_for_decision(self, decision_id: str, request: ApplicationPrepRequest) -> ApplicationPrepResponse:
        user_profile, matching_profile = self._current_profiles()
        decision = self.decision_repository.get_by_id(decision_id)
        if decision is None or decision.user_profile_id != user_profile.id:
            raise NotFoundError("Job application decision not found")
        job = self.job_repository.get_by_id(decision.job_id)
        if job is None:
            raise NotFoundError("Job not found")
        match = self._match_for(matching_profile, job.id)
        response = self._build_response(job, user_profile, matching_profile, match, decision, request)
        if request.update_decision:
            decision = self._upsert_decision(job, user_profile, match, decision, response)
            response.decision_id = decision.id
            logger.info("Application prep decision updated", extra={"job_id": job.id, "decision_id": decision.id})
        logger.info("Application prep generated", extra={"job_id": job.id, "decision_id": response.decision_id})
        return response

    def get_generated_for_job(self, job_id: str) -> ApplicationPrepResponse:
        job = self.job_repository.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job not found")
        user_profile, matching_profile = self._current_profiles()
        decision = self.decision_repository.get_by_job_and_user_profile(job.id, user_profile.id)
        if decision is None or not decision.fit_summary:
            raise NotFoundError("Application prep not generated yet")
        match = self._match_for(matching_profile, job.id)
        request = ApplicationPrepRequest(update_decision=False)
        return self._build_response(job, user_profile, matching_profile, match, decision, request, use_stored=True)

    def _current_profiles(self) -> tuple[UserProfile, JobMatchingProfile | None]:
        user_profile = self.user_profile_repository.get_first_profile()
        if user_profile is None:
            raise NotFoundError("User profile not found")
        return user_profile, self.profile_repository.get_by_user_profile_id(user_profile.id)

    def _match_for(self, profile: JobMatchingProfile | None, job_id: str) -> JobMatch | None:
        if profile is None:
            return None
        return self.match_repository.get_by_profile_and_job(profile.id, job_id)

    def _build_response(
        self,
        job: Job,
        user_profile: UserProfile,
        profile: JobMatchingProfile | None,
        match: JobMatch | None,
        decision: JobApplicationDecision | None,
        request: ApplicationPrepRequest,
        *,
        use_stored: bool = False,
    ) -> ApplicationPrepResponse:
        fit_summary = decision.fit_summary if use_stored and decision and decision.fit_summary else _fit_summary(job, profile, match)
        missing = _missing_information(job, match)
        concerns = _concerns(job, match, decision)
        next_action = decision.next_action if use_stored and decision and decision.next_action else _next_action(match, decision)
        resume_points = _resume_focus_points(job, profile) if request.include_resume_focus else []
        project_points = _project_talking_points(job)
        checklist = _checklist(job, match) if request.include_checklist else []
        cold_dm = _cold_dm_angle(job) if request.include_cold_dm_angle else None
        if use_stored and decision and decision.concerns:
            concerns = [ApplicationPrepListItem(label="Concern", value=item, reason="Stored application prep concern.") for item in decision.concerns]

        return ApplicationPrepResponse(
            job_id=job.id,
            decision_id=decision.id if decision else None,
            company_name=getattr(job.company, "name", None),
            title=job.title,
            match_tier=getattr(match, "match_tier", None),
            total_score=getattr(match, "total_score", None),
            remote_eligibility=getattr(match, "remote_eligibility", None),
            fit_summary=fit_summary,
            resume_focus_points=resume_points,
            project_talking_points=project_points,
            concerns=concerns,
            missing_information=missing,
            suggested_next_action=next_action,
            cold_dm_angle=cold_dm,
            application_checklist=checklist,
            generated_at=datetime.now(timezone.utc),
        )

    def _upsert_decision(
        self,
        job: Job,
        user_profile: UserProfile,
        match: JobMatch | None,
        decision: JobApplicationDecision | None,
        prep: ApplicationPrepResponse,
    ) -> JobApplicationDecision:
        values = {
            "fit_summary": prep.fit_summary,
            "concerns": [item.value for item in prep.concerns],
            "next_action": prep.suggested_next_action,
            "source_snapshot": _source_snapshot(job),
            "match_snapshot": _match_snapshot(match),
        }
        if decision is not None:
            if decision.next_action_due_at is None and _urgent_next_action(prep.suggested_next_action):
                values["next_action_due_at"] = datetime.now(timezone.utc) + timedelta(days=1)
            if not decision.priority:
                values["priority"] = _priority_for(match)
            if not decision.status:
                values["status"] = _status_for(match)
            return self.decision_repository.update(decision, values)

        now = datetime.now(timezone.utc)
        status = _status_for(match)
        decision = JobApplicationDecision(
            job_id=job.id,
            user_profile_id=user_profile.id,
            status=status,
            priority=_priority_for(match),
            decided_at=now,
            saved_at=now if status in {"saved", "needs_custom_resume"} else None,
            last_status_changed_at=now,
            **values,
        )
        return self.decision_repository.create(decision)


def _fit_summary(job: Job, profile: JobMatchingProfile | None, match: JobMatch | None) -> str:
    role = _role_label(job)
    remote = _remote_phrase(getattr(match, "remote_eligibility", None) or getattr(job, "remote_type", None))
    tier = getattr(match, "match_tier", None)
    skills = _overlap_labels(_profile_terms(profile), _job_terms(job))[:3]
    skill_phrase = f" with alignment around {', '.join(skills)}" if skills else ""
    experience = getattr(job, "experience_min", None)
    experience_phrase = " and acceptable experience expectations" if experience is None or experience <= 3 else " though the experience bar may need review"
    if tier in {"best_match", "strong_match"}:
        prefix = "Strong fit" if tier == "best_match" else "Good fit"
        return f"{prefix}: this is a {remote} {role} role{skill_phrase}{experience_phrase}."
    if tier in {"worth_checking", "stretch"}:
        return f"Potential fit: the role aligns with your target titles, but remote eligibility or experience expectations need verification before applying."
    return f"Potential fit: this {role} role may be worth reviewing if the requirements and remote eligibility match your profile."


def _resume_focus_points(job: Job, profile: JobMatchingProfile | None) -> list[ApplicationPrepListItem]:
    profile_terms = _profile_terms(profile)
    job_terms = _job_terms(job)
    overlap = _overlap_labels(profile_terms, job_terms)
    points: list[ApplicationPrepListItem] = []
    for term in overlap[:5]:
        points.append(ApplicationPrepListItem(label="Resume focus", value=f"Emphasize {term} experience.", reason="Present in both your profile and job evidence."))
    normalized = _all_text(job)
    if any(token in normalized for token in ("intern", "junior", "entry", "new grad")):
        points.append(ApplicationPrepListItem(label="Resume focus", value="Emphasize learning speed and shipped projects.", reason="The role appears entry-level or early-career friendly."))
    if not points and profile_terms:
        for term in list(profile_terms.values())[:3]:
            points.append(ApplicationPrepListItem(label="Resume focus", value=f"Highlight {term} where relevant.", reason="Present in your matching profile."))
    return points[:7]


def _project_talking_points(job: Job) -> list[ApplicationPrepListItem]:
    role = _role_key(job)
    if role in {"ai_engineer", "ml_engineer"}:
        values = ["production AI systems", "Python and ML workflows", "LLM evaluation and reliability"]
    elif role in {"forward_deployed_engineer", "developer_advocate"}:
        values = ["customer-facing technical problem-solving", "debugging ambiguous requirements", "clear technical communication"]
    else:
        values = ["backend APIs", "database-backed systems", "Docker and reliability habits"]
    return [ApplicationPrepListItem(label="Project talking point", value=value, reason="Safe profile-aligned talking point for this role type.") for value in values]


def _concerns(job: Job, match: JobMatch | None, decision: JobApplicationDecision | None) -> list[ApplicationPrepListItem]:
    concerns: list[ApplicationPrepListItem] = []
    if job.salary_min is None and job.salary_max is None:
        concerns.append(_item("Concern", "Salary not listed.", "Compensation is missing from the job record."))
    remote = getattr(match, "remote_eligibility", None)
    if remote in {None, "unknown", "remote_eligibility_unclear"}:
        concerns.append(_item("Concern", "Remote eligibility needs verification.", "Remote evidence is missing or unclear."))
    if not job.work_authorization:
        concerns.append(_item("Concern", "Work authorization not stated.", "The job record does not state authorization requirements."))
    if getattr(job, "experience_min", None) is not None and job.experience_min > 3:
        concerns.append(_item("Concern", "Experience requirement may be above profile.", "The minimum experience requirement is above the target range."))
    if getattr(match, "match_tier", None) == "stretch":
        concerns.append(_item("Concern", "Role is a stretch.", "The match tier is stretch."))
    if not job.apply_url and not job.job_url:
        concerns.append(_item("Concern", "Apply URL is missing.", "No application or source URL is available."))
    if match and getattr(match, "is_stale", False):
        concerns.append(_item("Concern", "Job score may be stale.", "The match was marked stale."))
    if decision and decision.status == "applied":
        concerns.append(_item("Concern", "Already applied.", "Track response instead of applying again."))
    return concerns[:8]


def _missing_information(job: Job, match: JobMatch | None) -> list[str]:
    missing = list(getattr(match, "missing_information_json", None) or [])
    checks = [
        ("salary", job.salary_min is None and job.salary_max is None),
        ("employment_type", not job.employment_type),
        ("work_authorization", not job.work_authorization),
        ("apply_url", not job.apply_url and not job.job_url),
        ("company_details", not getattr(job.company, "website_url", None) and not getattr(job.company, "description", None)),
        ("experience_range", job.experience_min is None and job.experience_max is None),
    ]
    for key, should_add in checks:
        if should_add and key not in missing:
            missing.append(key)
    return missing


def _next_action(match: JobMatch | None, decision: JobApplicationDecision | None) -> str:
    status = getattr(decision, "status", None)
    if status == "applied":
        return "Track response and follow up later if appropriate."
    if status == "needs_cold_dm":
        return "Find a founder or hiring manager and draft a short cold DM."
    if status == "needs_custom_resume":
        return "Update resume bullets for ML, Python and backend AI before applying."
    if getattr(match, "match_tier", None) == "best_match":
        return "Tailor resume and apply today."
    if getattr(match, "match_tier", None) == "strong_match":
        return "Prepare tailored resume and submit application."
    if getattr(match, "match_tier", None) == "unsuitable":
        return "Skip unless you want to keep it for reference."
    return "Review requirements, verify remote eligibility, then decide whether to apply."


def _cold_dm_angle(job: Job) -> str:
    role = _role_key(job)
    if role in {"ai_engineer", "ml_engineer"}:
        return "Lead with your interest in production ML/AI systems and mention a relevant AI/backend project."
    if role in {"forward_deployed_engineer", "developer_advocate"}:
        return "Lead with your ability to debug real customer problems and turn ambiguous requirements into working systems."
    return "Lead with your backend engineering experience and shipped project work."


def _checklist(job: Job, match: JobMatch | None) -> list[ApplicationPrepListItem]:
    items = [
        _item("Checklist", "Review job requirements.", "Confirm the role is still aligned before applying."),
        _item("Checklist", "Verify remote-from-India eligibility.", "Remote eligibility can affect whether applying is worthwhile."),
        _item("Checklist", "Tailor resume headline/summary.", "A targeted resume improves application quality."),
        _item("Checklist", "Emphasize relevant project bullets.", "Use the strongest overlapping job/profile evidence."),
        _item("Checklist", "Apply through source link.", "Use the canonical application URL when available."),
        _item("Checklist", "Save application status as applied.", "Keep tracking accurate after submitting."),
    ]
    if job.salary_min is None and job.salary_max is None:
        items.append(_item("Checklist", "Check compensation range if contacted.", "Salary is missing from the job record."))
    if not job.work_authorization:
        items.append(_item("Checklist", "Confirm international/India eligibility.", "Work authorization is missing."))
    if match and getattr(match, "is_stale", False):
        items.append(_item("Checklist", "Refresh score before applying.", "The match score may be stale."))
    return items


def _profile_terms(profile: JobMatchingProfile | None) -> dict[str, str]:
    if profile is None:
        return {}
    values: list[Any] = []
    values.extend(profile.skills_json or [])
    values.extend(profile.technologies_json or [])
    values.extend(profile.target_titles_json or [])
    terms: dict[str, str] = {}
    for item in values:
        label = item.get("name") if isinstance(item, dict) else str(item)
        key = normalize_title(label)
        if key:
            terms[key] = label
    return terms


def _job_terms(job: Job) -> set[str]:
    values: list[Any] = []
    values.extend(job.required_skills_json or [])
    values.extend(job.preferred_skills_json or [])
    values.extend(job.technologies_json or [])
    values.extend([job.title, job.role_category, job.description])
    text = " ".join(str(value or "") for value in values).lower()
    aliases = {
        "python": "python",
        "machine learning": "machine learning",
        "ml": "machine learning",
        "fastapi": "fastapi",
        "postgresql": "postgresql",
        "postgres": "postgresql",
        "docker": "docker",
        "aws": "aws",
        "llm": "llms",
        "llms": "llms",
        "backend": "backend development",
    }
    terms = {normalize_title(value) for value in values if value}
    for token, label in aliases.items():
        if token in text:
            terms.add(normalize_title(label))
    terms.discard("")
    return terms


def _overlap_labels(profile_terms: dict[str, str], job_terms: set[str]) -> list[str]:
    return [label for key, label in profile_terms.items() if key in job_terms]


def _role_key(job: Job) -> str:
    return str(getattr(job.role_category, "value", job.role_category) or "software_engineer")


def _role_label(job: Job) -> str:
    return _role_key(job).replace("_", " ").title()


def _remote_phrase(value: Any) -> str:
    text = str(getattr(value, "value", value) or "remote").replace("_", "-")
    if "work-from-anywhere" in text or "remote-worldwide" in text:
        return "work-from-anywhere"
    if "remote" in text:
        return "remote"
    return text


def _all_text(job: Job) -> str:
    return " ".join(str(value or "") for value in (job.title, job.seniority, job.description)).lower()


def _status_for(match: JobMatch | None) -> str:
    tier = getattr(match, "match_tier", None)
    if tier in {"best_match", "strong_match"}:
        return "needs_custom_resume"
    return "saved"


def _priority_for(match: JobMatch | None) -> str:
    tier = getattr(match, "match_tier", None)
    if tier == "best_match":
        return "high"
    if tier in {"strong_match", "worth_checking"}:
        return "medium"
    return "low"


def _urgent_next_action(value: str) -> bool:
    return "today" in value.lower()


def _source_snapshot(job: Job) -> dict[str, Any]:
    return {"job_url": job.job_url, "apply_url": job.apply_url, "source_platform": job.source_platform}


def _match_snapshot(match: JobMatch | None) -> dict[str, Any] | None:
    if match is None:
        return None
    return {"match_tier": match.match_tier, "total_score": match.total_score, "remote_eligibility": match.remote_eligibility}


def _item(label: str, value: str, reason: str) -> ApplicationPrepListItem:
    return ApplicationPrepListItem(label=label, value=value, reason=reason)
