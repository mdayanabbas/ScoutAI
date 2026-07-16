import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.job import Job
from app.models.job_application_decision import JobApplicationDecision
from app.models.job_match import JobMatch
from app.models.job_matching_profile import JobMatchingProfile
from app.models.resume import Resume
from app.models.user_profile import UserProfile
from app.repositories.job_application_decision_repository import JobApplicationDecisionRepository
from app.repositories.job_match_repository import JobMatchRepository
from app.repositories.job_matching_profile_repository import JobMatchingProfileRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import UserProfileRepository
from app.repositories.resume_repository import ResumeRepository
from app.schemas.resume_improvement import (
    ResumeBulletSuggestion,
    ResumeImprovementItem,
    ResumeImprovementRequest,
    ResumeImprovementResponse,
    ResumeSectionSuggestion,
    ResumeSkillGapSuggestion,
)
from app.utils.text import normalize_title

logger = logging.getLogger(__name__)


class ResumeImprovementService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.job_repository = JobRepository(session)
        self.user_profile_repository = UserProfileRepository(session)
        self.profile_repository = JobMatchingProfileRepository(session)
        self.match_repository = JobMatchRepository(session)
        self.resume_repository = ResumeRepository(session)
        self.decision_repository = JobApplicationDecisionRepository(session)

    def generate_for_job(self, job_id: str, request: ResumeImprovementRequest) -> ResumeImprovementResponse:
        job = self.job_repository.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job not found")
        user_profile, profile = self._current_profiles()
        match = self._match_for(profile, job.id)
        decision = self.decision_repository.get_by_job_and_user_profile(job.id, user_profile.id)
        resume = self.resume_repository.get_active_for_user_profile(user_profile.id)
        response = self._build_response(job, profile, match, decision, resume, request)
        if request.update_decision:
            decision = self._upsert_decision(job, user_profile, match, decision, response)
            response.decision_id = decision.id
            logger.info("Resume improvement decision updated", extra={"job_id": job.id, "decision_id": decision.id})
        logger.info("Resume improvement generated", extra={"job_id": job.id, "resume_used": response.resume_used})
        return response

    def generate_for_decision(self, decision_id: str, request: ResumeImprovementRequest) -> ResumeImprovementResponse:
        user_profile, profile = self._current_profiles()
        decision = self.decision_repository.get_by_id(decision_id)
        if decision is None or decision.user_profile_id != user_profile.id:
            raise NotFoundError("Job application decision not found")
        job = self.job_repository.get_by_id(decision.job_id)
        if job is None:
            raise NotFoundError("Job not found")
        match = self._match_for(profile, job.id)
        resume = self.resume_repository.get_active_for_user_profile(user_profile.id)
        response = self._build_response(job, profile, match, decision, resume, request)
        if request.update_decision:
            decision = self._upsert_decision(job, user_profile, match, decision, response)
            response.decision_id = decision.id
            logger.info("Resume improvement decision updated", extra={"job_id": job.id, "decision_id": decision.id})
        logger.info("Resume improvement generated", extra={"job_id": job.id, "resume_used": response.resume_used})
        return response

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
        profile: JobMatchingProfile | None,
        match: JobMatch | None,
        decision: JobApplicationDecision | None,
        resume: Resume | None,
        request: ResumeImprovementRequest,
    ) -> ResumeImprovementResponse:
        resume_used = bool(resume and resume.parse_status == "parsed")
        resume_terms = _resume_terms(resume) if resume_used else set()
        profile_terms = _profile_terms(profile)
        required = _skill_source_map(job, "required")
        preferred = _skill_source_map(job, "preferred")
        inferred = _inferred_skill_map(job)
        job_skill_sources = {**inferred, **preferred, **required}
        found = sorted(term for term in job_skill_sources if term in resume_terms)
        missing = sorted(term for term in job_skill_sources if term not in resume_terms)
        section_suggestions = _section_suggestions(job, resume, resume_used, found, missing) if request.include_section_suggestions else []
        bullet_suggestions = _bullet_suggestions(job, resume_terms, profile_terms, job_skill_sources) if request.include_bullet_suggestions else []
        skill_gap_suggestions = _skill_gap_suggestions(job_skill_sources, resume_terms, profile_terms) if request.include_skill_gap_suggestions else []
        project_suggestions = _project_suggestions(job, resume) if request.include_project_reordering else []
        remote_suggestions = _remote_suggestions(job, resume, match) if request.include_remote_fit_suggestions else []
        risks = _risks(job, resume, resume_used, missing, match)
        summary = _summary(resume_used, found, missing, match)
        next_action = _next_action(resume_used, missing, match, decision)
        if not resume_used:
            logger.info("Resume improvement generated without active resume", extra={"job_id": job.id})
        return ResumeImprovementResponse(
            job_id=job.id,
            decision_id=decision.id if decision else None,
            resume_id=resume.id if resume else None,
            resume_used=resume_used,
            company_name=getattr(job.company, "name", None),
            title=job.title,
            match_tier=getattr(match, "match_tier", None),
            total_score=getattr(match, "total_score", None),
            remote_eligibility=getattr(match, "remote_eligibility", None),
            improvement_summary=summary,
            section_suggestions=section_suggestions,
            bullet_suggestions=bullet_suggestions,
            skill_gap_suggestions=skill_gap_suggestions,
            project_reordering_suggestions=project_suggestions,
            remote_fit_suggestions=remote_suggestions,
            risks=risks,
            suggested_next_action=next_action,
            generated_at=datetime.now(timezone.utc),
        )

    def _upsert_decision(
        self,
        job: Job,
        user_profile: UserProfile,
        match: JobMatch | None,
        decision: JobApplicationDecision | None,
        response: ResumeImprovementResponse,
    ) -> JobApplicationDecision:
        preserved_statuses = {"applied", "skipped", "not_interested", "archived", "rejected", "offer", "interviewing"}
        target_status = "needs_custom_resume" if getattr(match, "match_tier", None) in {"best_match", "strong_match"} else "saved"
        values: dict[str, Any] = {
            "source_snapshot": {"job_url": job.job_url, "apply_url": job.apply_url, "source_platform": job.source_platform},
            "match_snapshot": _match_snapshot(match),
        }
        if decision is None:
            now = datetime.now(timezone.utc)
            return self.decision_repository.create(
                JobApplicationDecision(
                    job_id=job.id,
                    user_profile_id=user_profile.id,
                    status=target_status,
                    priority="high" if target_status == "needs_custom_resume" else "medium",
                    fit_summary=response.improvement_summary,
                    concerns=[item.suggestion for item in response.risks],
                    next_action=response.suggested_next_action,
                    decided_at=now,
                    saved_at=now if target_status in {"saved", "needs_custom_resume"} else None,
                    last_status_changed_at=now,
                    **values,
                )
            )
        safe_values = values.copy()
        if decision.status not in preserved_statuses and decision.status != target_status:
            safe_values["status"] = target_status
            safe_values["last_status_changed_at"] = datetime.now(timezone.utc)
        if not decision.fit_summary:
            safe_values["fit_summary"] = response.improvement_summary
        if not decision.concerns:
            safe_values["concerns"] = [item.suggestion for item in response.risks]
        generated_next_actions = (
            "Update resume bullets",
            "Upload an active resume",
            "Skip or archive",
            "Do not rewrite",
        )
        if not decision.next_action or decision.next_action.startswith(generated_next_actions):
            safe_values["next_action"] = response.suggested_next_action
        return self.decision_repository.update(decision, safe_values)


def _skill_source_map(job: Job, source: str) -> dict[str, str]:
    values = job.required_skills_json if source == "required" else job.preferred_skills_json
    return {normalize_title(str(value)): source for value in values or [] if normalize_title(str(value))}


def _inferred_skill_map(job: Job) -> dict[str, str]:
    text = " ".join(str(value or "") for value in (job.title, job.role_category, job.description)).lower()
    aliases = {
        "python": "python",
        "fastapi": "fastapi",
        "postgresql": "postgresql",
        "postgres": "postgresql",
        "docker": "docker",
        "aws": "aws",
        "llm": "llms",
        "machine learning": "machine learning",
        "ml": "machine learning",
        "react": "react",
        "typescript": "typescript",
    }
    inferred = {normalize_title(str(value)): "preferred" for value in job.technologies_json or [] if normalize_title(str(value))}
    for token, label in aliases.items():
        if token in text:
            inferred[normalize_title(label)] = "inferred"
    if _role_key(job) in {"ai_engineer", "ml_engineer"}:
        inferred.setdefault("machine learning", "inferred")
        inferred.setdefault("llms", "inferred")
    return inferred


def _resume_terms(resume: Resume | None) -> set[str]:
    if resume is None:
        return set()
    terms = {normalize_title(str(value)) for value in (resume.skills_json or []) + (resume.technologies_json or []) if normalize_title(str(value))}
    for item in (resume.projects_json or []) + (resume.experience_json or []):
        text = _entry_text(item).lower()
        for token, label in {
            "python": "python",
            "fastapi": "fastapi",
            "postgresql": "postgresql",
            "postgres": "postgresql",
            "docker": "docker",
            "aws": "aws",
            "llm": "llms",
            "machine learning": "machine learning",
            "remote": "remote collaboration",
            "async": "remote collaboration",
        }.items():
            if token in text:
                terms.add(normalize_title(label))
    return terms


def _profile_terms(profile: JobMatchingProfile | None) -> set[str]:
    if profile is None:
        return set()
    values: list[Any] = []
    values.extend(profile.skills_json or [])
    values.extend(profile.technologies_json or [])
    result: set[str] = set()
    for item in values:
        label = item.get("name") if isinstance(item, dict) else str(item)
        key = normalize_title(label)
        if key:
            result.add(key)
    return result


def _section_suggestions(job: Job, resume: Resume | None, resume_used: bool, found: list[str], missing: list[str]) -> list[ResumeSectionSuggestion]:
    suggestions = [
        ResumeSectionSuggestion(
            section="Summary",
            action="tailor",
            suggestion=f"Add a short line positioning yourself for the {job.title} role using only accurate AI/backend evidence.",
            reason="A targeted summary helps the reviewer connect your resume to this job quickly.",
            priority="medium" if resume_used else "low",
        ),
        ResumeSectionSuggestion(
            section="Technical Skills",
            action="clarify",
            suggestion="Keep job-matching technologies visible near the top.",
            reason="Recruiters scan the skills section before reading project details.",
            priority="high" if missing else "medium",
        ),
    ]
    if not _resume_projects(resume):
        suggestions.append(
            ResumeSectionSuggestion(
                section="Projects",
                action="add_or_clarify",
                suggestion="Add or clarify a projects section with your strongest AI/backend project.",
                reason="No parsed project evidence was detected.",
                priority="high",
            )
        )
    else:
        suggestions.append(
            ResumeSectionSuggestion(
                section="Projects",
                action="reorder",
                suggestion="Move the most relevant AI/backend project higher before applying.",
                reason="Project order should make job-relevant evidence visible.",
                priority="medium",
            )
        )
    if found:
        suggestions.append(
            ResumeSectionSuggestion(
                section="Experience",
                action="strengthen",
                suggestion=f"Add implementation-focused bullets around {', '.join(_display(term) for term in found[:3])}.",
                reason="These are already supported by parsed resume evidence.",
                priority="medium",
            )
        )
    return suggestions[:6]


def _bullet_suggestions(job: Job, resume_terms: set[str], profile_terms: set[str], job_skill_sources: dict[str, str]) -> list[ResumeBulletSuggestion]:
    templates = [
        ("Projects", "Built [project name] using Python and FastAPI to support AI workflow automation, validation and traceable execution.", {"python", "fastapi"}),
        ("Projects", "Implemented database-backed workflow tracking with PostgreSQL and SQLAlchemy for [project/use case].", {"postgresql"}),
        ("Projects", "Integrated LLM providers with fallback handling, structured outputs and deterministic quality checks.", {"llms"}),
        ("Experience", "Improved reliability by adding tests, validation and explicit failure handling across [feature/module].", set()),
        ("Projects", "Built a remote-job matching workflow that ingests, filters and scores jobs against user preferences.", set()),
        ("Projects", "Containerized [service/project] with Docker for repeatable local development and deployment.", {"docker"}),
    ]
    items: list[ResumeBulletSuggestion] = []
    relevant = set(job_skill_sources) | profile_terms | resume_terms
    for section, template, required in templates:
        if required and not (required & relevant):
            continue
        supported = bool(required and required <= resume_terms)
        items.append(
            ResumeBulletSuggestion(
                target_section=section,
                bullet_template=template,
                supported_by_resume=supported,
                supporting_evidence=", ".join(_display(term) for term in sorted(required & resume_terms)) or None,
                caution=None if supported else "Add only if this reflects your real project experience.",
            )
        )
    return items[:8]


def _skill_gap_suggestions(job_skill_sources: dict[str, str], resume_terms: set[str], profile_terms: set[str]) -> list[ResumeSkillGapSuggestion]:
    suggestions: list[ResumeSkillGapSuggestion] = []
    for skill, source in sorted(job_skill_sources.items()):
        found = skill in resume_terms
        if found:
            suggestion = f"Keep {_display(skill)} visible near the top because it matches the role."
            caution = None
        elif skill in profile_terms:
            suggestion = f"Resume parser did not detect {_display(skill)}. Add evidence if you have used it."
            caution = "Add only if true."
        else:
            suggestion = f"Review whether {_display(skill)} is required before applying."
            caution = "Do not add this unless it reflects real experience."
        suggestions.append(
            ResumeSkillGapSuggestion(
                skill=_display(skill),
                found_in_resume=found,
                required_or_preferred=source,
                suggestion=suggestion,
                caution=caution,
            )
        )
    return suggestions[:12]


def _project_suggestions(job: Job, resume: Resume | None) -> list[ResumeImprovementItem]:
    projects = _resume_projects(resume)
    if not projects:
        return [
            ResumeImprovementItem(
                category="projects",
                suggestion="Add or clarify projects section with your strongest AI/backend project.",
                reason="No parsed projects were detected.",
                priority="high",
                evidence=None,
                caution="Use an actual project only.",
            )
        ]
    first = projects[0]
    return [
        ResumeImprovementItem(
            category="projects",
            suggestion=f"Move or keep '{first}' high if it is the closest match for this role.",
            reason="Detected resume project titles can anchor application bullets.",
            priority="medium",
            evidence=first,
            caution="Do not rename or exaggerate the project.",
        ),
        ResumeImprovementItem(
            category="projects",
            suggestion=f"Add job-relevant keywords from {job.title} to project bullets where accurate.",
            reason="Project bullets should make the match easy to scan.",
            priority="medium",
            caution="Add only truthful keywords.",
        ),
    ]


def _remote_suggestions(job: Job, resume: Resume | None, match: JobMatch | None) -> list[ResumeImprovementItem]:
    remote_signal = str(getattr(job, "remote_type", "") or "").startswith("remote") or getattr(match, "remote_eligibility", None) in {"work_from_anywhere", "remote_india_eligible"}
    if not remote_signal:
        return []
    resume_entries = ((resume.projects_json or []) + (resume.experience_json or [])) if resume else []
    text = " ".join(_entry_text(item) for item in resume_entries).lower()
    has_remote = "remote" in text or "async" in text or "documentation" in text
    return [
        ResumeImprovementItem(
            category="remote_fit",
            suggestion="Mention async collaboration, independent ownership or written documentation if true.",
            reason="Remote-friendly roles benefit from visible collaboration evidence.",
            priority="medium",
            evidence="remote/async signal detected" if has_remote else None,
            caution=None if has_remote else "Add remote collaboration evidence only if true.",
        )
    ]


def _risks(job: Job, resume: Resume | None, resume_used: bool, missing: list[str], match: JobMatch | None) -> list[ResumeImprovementItem]:
    risks: list[ResumeImprovementItem] = []
    if not resume_used:
        risks.append(_risk("resume", "No active parsed resume is available.", "Upload and activate a resume.", "high"))
    for skill in missing[:5]:
        risks.append(_risk("skill_gap", f"{_display(skill)} not found in resume.", "Core or inferred job skill was not detected.", "high"))
    if _role_key(job) in {"ai_engineer", "ml_engineer"} and resume_used and not ({"machine learning", "llms"} & _resume_terms(resume)):
        risks.append(_risk("ml_ai", "ML/AI evidence not found in resume.", "AI role needs visible ML/LLM evidence.", "high"))
    if resume_used and not _resume_projects(resume):
        risks.append(_risk("projects", "No projects detected in resume.", "Project evidence is important for early-career applications.", "high"))
    if resume_used and not (resume.links_json or []):
        risks.append(_risk("links", "No links detected in resume.", "Portfolio, GitHub or LinkedIn links can support project claims.", "low"))
    if getattr(match, "is_stale", False):
        risks.append(_risk("match", "Job score may be stale.", "Refresh scoring before final application.", "medium"))
    if not job.work_authorization:
        risks.append(_risk("application", "Work authorization unclear.", "Verify eligibility before applying.", "medium"))
    if job.salary_min is None and job.salary_max is None:
        risks.append(_risk("application", "Salary not listed.", "Compensation is missing but not a resume issue.", "low"))
    return risks[:10]


def _summary(resume_used: bool, found: list[str], missing: list[str], match: JobMatch | None) -> str:
    if not resume_used:
        return "No active resume is available, so these suggestions are based only on your profile and the job. Upload a resume for accurate gap analysis."
    if missing and len(missing) >= max(2, len(found)):
        return "Your resume needs stronger evidence for the job's core requirements before applying."
    if found:
        return f"Your resume already supports parts of this role through {', '.join(_display(term) for term in found[:4])}. Improve it by making the most relevant evidence more visible."
    if getattr(match, "match_tier", None) in {"best_match", "strong_match"}:
        return "This role scores well, but parsed resume evidence should be made clearer before applying."
    return "Use these suggestions to make your resume evidence easier to scan before applying."


def _next_action(resume_used: bool, missing: list[str], match: JobMatch | None, decision: JobApplicationDecision | None) -> str:
    if decision and decision.status in {"applied", "interviewing", "offer"}:
        return "Do not rewrite application unless you need follow-up material."
    if getattr(match, "match_tier", None) == "unsuitable":
        return "Skip or archive unless you intentionally want to keep this as a stretch reference."
    if not resume_used:
        return "Upload an active resume before generating final application materials."
    if missing:
        return "Update resume bullets for ML/Python/backend AI evidence, then apply."
    return "Review suggested bullets, tailor the resume lightly, then apply."


def _updatable_generated(value: Any) -> bool:
    if not value:
        return True
    return False


def _risk(category: str, suggestion: str, reason: str, priority: str) -> ResumeImprovementItem:
    return ResumeImprovementItem(category=category, suggestion=suggestion, reason=reason, priority=priority)


def _resume_projects(resume: Resume | None) -> list[str]:
    if resume is None:
        return []
    result = []
    for item in resume.projects_json or []:
        if isinstance(item, dict):
            value = item.get("title") or item.get("name") or item.get("text")
        else:
            value = item
        if value:
            result.append(str(value))
    return result


def _entry_text(item: Any) -> str:
    if isinstance(item, dict):
        return " ".join(str(value or "") for value in item.values())
    return str(item or "")


def _role_key(job: Job) -> str:
    return str(getattr(job.role_category, "value", job.role_category) or "software_engineer")


def _display(term: str) -> str:
    return {
        "llms": "LLMs",
        "fastapi": "FastAPI",
        "postgresql": "PostgreSQL",
        "aws": "AWS",
    }.get(term, term.title())


def _match_snapshot(match: JobMatch | None) -> dict[str, Any] | None:
    if match is None:
        return None
    return {
        "match_tier": match.match_tier,
        "total_score": match.total_score,
        "remote_eligibility": match.remote_eligibility,
    }
