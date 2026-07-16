import logging
from datetime import datetime, timezone
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
from app.repositories.resume_repository import ResumeRepository
from app.schemas.application_packet import (
    ApplicationPacketItem,
    ApplicationPacketRequest,
    ApplicationPacketResponse,
    ApplicationPacketSection,
)
from app.schemas.application_prep import ApplicationPrepRequest
from app.services.application_prep_service import ApplicationPrepService
from app.utils.text import normalize_title

logger = logging.getLogger(__name__)


class ApplicationPacketService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.job_repository = JobRepository(session)
        self.user_profile_repository = UserProfileRepository(session)
        self.profile_repository = JobMatchingProfileRepository(session)
        self.match_repository = JobMatchRepository(session)
        self.decision_repository = JobApplicationDecisionRepository(session)
        self.resume_repository = ResumeRepository(session)
        self.prep_service = ApplicationPrepService(session)

    def generate_for_job(self, job_id: str, request: ApplicationPacketRequest) -> ApplicationPacketResponse:
        job = self.job_repository.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job not found")
        user_profile, profile = self._current_profiles()
        match = self._match_for(profile, job.id)
        decision = self.decision_repository.get_by_job_and_user_profile(job.id, user_profile.id)
        resume = self.resume_repository.get_active_for_user_profile(user_profile.id)
        packet = self._build_packet(job, profile, match, decision, request, resume)
        if request.update_decision:
            decision = self._upsert_decision(job, user_profile, match, decision, packet)
            packet.decision_id = decision.id
            logger.info("Application packet decision updated", extra={"job_id": job.id, "decision_id": decision.id})
        logger.info("Application packet generated", extra={"job_id": job.id, "decision_id": packet.decision_id, "resume_used": packet.resume_used})
        return packet

    def generate_for_decision(self, decision_id: str, request: ApplicationPacketRequest) -> ApplicationPacketResponse:
        user_profile, profile = self._current_profiles()
        decision = self.decision_repository.get_by_id(decision_id)
        if decision is None or decision.user_profile_id != user_profile.id:
            raise NotFoundError("Job application decision not found")
        job = self.job_repository.get_by_id(decision.job_id)
        if job is None:
            raise NotFoundError("Job not found")
        match = self._match_for(profile, job.id)
        resume = self.resume_repository.get_active_for_user_profile(user_profile.id)
        packet = self._build_packet(job, profile, match, decision, request, resume)
        if request.update_decision:
            decision = self._upsert_decision(job, user_profile, match, decision, packet)
            packet.decision_id = decision.id
            logger.info("Application packet decision updated", extra={"job_id": job.id, "decision_id": decision.id})
        logger.info("Application packet generated", extra={"job_id": job.id, "decision_id": packet.decision_id, "resume_used": packet.resume_used})
        return packet

    def _current_profiles(self) -> tuple[UserProfile, JobMatchingProfile | None]:
        user_profile = self.user_profile_repository.get_first_profile()
        if user_profile is None:
            raise NotFoundError("User profile not found")
        return user_profile, self.profile_repository.get_by_user_profile_id(user_profile.id)

    def _match_for(self, profile: JobMatchingProfile | None, job_id: str) -> JobMatch | None:
        if profile is None:
            return None
        return self.match_repository.get_by_profile_and_job(profile.id, job_id)

    def _build_packet(
        self,
        job: Job,
        profile: JobMatchingProfile | None,
        match: JobMatch | None,
        decision: JobApplicationDecision | None,
        request: ApplicationPacketRequest,
        resume: Any | None = None,
    ) -> ApplicationPacketResponse:
        prep = self.prep_service.generate_for_job(
            job.id,
            ApplicationPrepRequest(update_decision=False),
        )
        resume_context = _resume_context(job, resume)
        positioning = _application_positioning(job, profile, match, resume_context)
        resume_focus = _resume_focus(job, profile, match)
        risks = _risks_to_verify(job, match)
        if not resume_context["resume_used"]:
            risks.append(_item("Risk", "No active resume uploaded; packet is based on profile and job evidence only.", "Upload an active resume to make packet evidence more specific."))
        else:
            risks.extend(resume_context["resume_gaps"])
        return ApplicationPacketResponse(
            job_id=job.id,
            decision_id=decision.id if decision else None,
            company_name=getattr(job.company, "name", None),
            title=job.title,
            role_category=_role_key(job),
            match_tier=getattr(match, "match_tier", None),
            total_score=getattr(match, "total_score", None),
            remote_eligibility=getattr(match, "remote_eligibility", None),
            resume_id=resume_context["resume_id"],
            resume_used=resume_context["resume_used"],
            resume_match_summary=resume_context["summary"],
            resume_strengths=resume_context["resume_strengths"],
            resume_gaps=resume_context["resume_gaps"],
            resume_bullet_sources=resume_context["resume_bullet_sources"],
            application_positioning=positioning,
            resume_focus=resume_focus,
            resume_bullet_suggestions=_resume_bullets(job, profile, resume_context) if request.include_resume_bullets else [],
            project_evidence_to_use=_project_evidence(job),
            cover_note_outline=_cover_note_outline(job, profile, match) if request.include_cover_note_outline else None,
            cold_dm_outline=_cold_dm_outline(job) if request.include_cold_dm_outline else None,
            application_checklist=_application_checklist(job, match) if request.include_checklist else [],
            risks_to_verify=risks if request.include_risk_review else [],
            suggested_apply_plan=_apply_plan(match),
            generated_at=datetime.now(timezone.utc),
        )

    def _upsert_decision(
        self,
        job: Job,
        user_profile: UserProfile,
        match: JobMatch | None,
        decision: JobApplicationDecision | None,
        packet: ApplicationPacketResponse,
    ) -> JobApplicationDecision:
        next_action = packet.suggested_apply_plan[0].value if packet.suggested_apply_plan else "Review packet and decide whether to apply."
        values: dict[str, Any] = {
            "fit_summary": packet.application_positioning,
            "concerns": [item.value for item in packet.risks_to_verify],
            "next_action": next_action,
            "source_snapshot": {"job_url": job.job_url, "apply_url": job.apply_url, "source_platform": job.source_platform},
            "match_snapshot": _match_snapshot(match),
        }
        if decision is not None:
            safe_values: dict[str, Any] = {
                "source_snapshot": values["source_snapshot"],
                "match_snapshot": values["match_snapshot"],
            }
            generated_markers = ("Position this application", "Strong fit:", "Good fit:", "Potential fit:")
            if not decision.fit_summary or decision.fit_summary.startswith(generated_markers):
                safe_values["fit_summary"] = values["fit_summary"]
            if not decision.concerns:
                safe_values["concerns"] = values["concerns"]
            if not decision.next_action or decision.next_action in {
                "Tailor resume and apply today.",
                "Prepare tailored resume and submit application.",
                "Review requirements, verify remote eligibility, then decide whether to apply.",
            }:
                safe_values["next_action"] = values["next_action"]
            if not decision.priority:
                safe_values["priority"] = _priority_for(match)
            return self.decision_repository.update(decision, safe_values)

        status = _status_for(match)
        now = datetime.now(timezone.utc)
        return self.decision_repository.create(
            JobApplicationDecision(
                job_id=job.id,
                user_profile_id=user_profile.id,
                status=status,
                priority=_priority_for(match),
                decided_at=now,
                saved_at=now if status in {"saved", "needs_custom_resume"} else None,
                last_status_changed_at=now,
                **values,
            )
        )


def _application_positioning(job: Job, profile: JobMatchingProfile | None, match: JobMatch | None, resume_context: dict[str, Any] | None = None) -> str:
    role = _role_key(job)
    resume_context = resume_context or {}
    resume_strengths = [item.value for item in resume_context.get("resume_strengths", [])]
    if resume_context.get("resume_used") and resume_strengths:
        phrase = ", ".join(resume_strengths[:4])
        return f"Position this application around your {phrase} evidence shown in the uploaded resume."
    supported = _overlap_labels(_profile_terms(profile), _job_terms(job))
    skill_phrase = ", ".join(supported[:4])
    if role in {"ml_engineer", "ai_engineer"}:
        base = "junior ML engineering, Python, backend AI systems, and ability to learn quickly in a remote team"
    elif role == "forward_deployed_engineer":
        base = "customer-facing engineering, debugging ambiguous problems, deployment ownership, and communication"
    else:
        base = "backend software engineering, APIs, databases, reliability, and shipped projects"
    if skill_phrase:
        return f"Position this application around {base}, especially {skill_phrase}."
    return f"Position this application around {base}."


def _resume_focus(job: Job, profile: JobMatchingProfile | None, match: JobMatch | None) -> list[ApplicationPacketItem]:
    if profile is None or match is None:
        return []
    points: list[ApplicationPacketItem] = []
    labels = _overlap_labels(_profile_terms(profile), _job_terms(job))
    for label in labels[:5]:
        points.append(_item("Resume focus", f"Put {label} evidence near the top.", "Supported by both profile and job evidence."))
    text = _job_text(job)
    if any(token in text for token in ("intern", "junior", "entry", "new grad")):
        points.append(_item("Resume focus", "Emphasize learning speed, projects and ownership.", "Role appears internship or entry-level friendly."))
    if "remote" in text:
        points.append(_item("Resume focus", "Mention async collaboration and self-directed execution.", "The job appears remote or distributed."))
    return _dedupe_items(points)[:8]


def _resume_bullets(job: Job, profile: JobMatchingProfile | None, resume_context: dict[str, Any] | None = None) -> list[ApplicationPacketItem]:
    resume_context = resume_context or {}
    if resume_context.get("resume_used"):
        items = list(resume_context.get("resume_bullet_sources", []))
        for gap in resume_context.get("resume_gaps", [])[:3]:
            items.append(_item("Resume gap", f"Consider adding evidence for {gap.value} if you have it.", "Gap detected between job requirements and uploaded resume."))
        if items:
            return items[:8]
    terms = set(_overlap_labels(_profile_terms(profile), _job_terms(job)))
    bullets = [
        ("Built backend APIs for AI workflows using Python and FastAPI, with structured outputs and validation.", {"Python", "FastAPI"}),
        ("Implemented LLM-powered workflow steps with fallback handling, evaluation checks and traceable execution.", {"LLMs"}),
        ("Designed PostgreSQL-backed services for tracking jobs, decisions and workflow state.", {"PostgreSQL"}),
        ("Improved reliability in [project name] by adding deterministic validation, tests and explicit failure handling, measured by [metric].", set()),
        ("Containerized and operated backend services with Docker for repeatable local and production workflows.", {"Docker"}),
        ("Integrated [model/provider] into [project name] with clear error handling and measurable [latency/reliability improvement].", {"LLMs"}),
    ]
    items: list[ApplicationPacketItem] = []
    for value, required in bullets:
        if not required or required & terms:
            items.append(_item("Resume bullet", value, "Template suggestion; adapt only if true for your project history."))
    return items[:8]


def _project_evidence(job: Job) -> list[ApplicationPacketItem]:
    role = _role_key(job)
    values = ["job matching / discovery platform", "database-backed workflow tracking", "evaluation and reliability"]
    if role in {"ai_engineer", "ml_engineer"}:
        values = ["AI workflow systems", "LLM orchestration", "evaluation and reliability"]
    elif role == "software_engineer":
        values = ["backend APIs", "database-backed workflow tracking", "remote-ready engineering process"]
    elif role == "forward_deployed_engineer":
        values = ["remote-ready engineering process", "backend APIs", "debugging ambiguous workflows"]
    return [_item("Project evidence", value, "Safe project category; use an actual project only if it exists in your history.") for value in values[:6]]


def _cover_note_outline(job: Job, profile: JobMatchingProfile | None, match: JobMatch | None) -> ApplicationPacketSection:
    role = _role_key(job)
    if role in {"ai_engineer", "ml_engineer"}:
        opening = "Lead with interest in production ML systems and remote engineering."
        proof = "Mention Python, backend AI workflows, LLM integration and tested product systems."
    else:
        opening = "Lead with interest in backend engineering and practical product delivery."
        proof = "Mention APIs, databases, reliability work and shipped projects."
    return ApplicationPacketSection(
        title="Cover Note Outline",
        items=[
            _item("Opening angle", opening, "Tailored to role category."),
            _item("Why this role", f"Reference the {job.title} role and company problem space.", "Uses the job title without inventing details."),
            _item("Relevant proof", proof, "Uses profile/job-aligned evidence."),
            _item("Remote fit", "Mention remote collaboration, ownership and clear written updates.", "Useful for remote roles."),
            _item("Closing", "Ask for consideration and point to your most relevant project or portfolio.", "Short outline, not a full cover letter."),
        ],
    )


def _cold_dm_outline(job: Job) -> ApplicationPacketSection:
    return ApplicationPacketSection(
        title="Cold DM Outline",
        items=[
            _item("Who to contact", "Founder, engineering manager, ML lead or recruiter.", "No names are invented or scraped."),
            _item("Opening hook", f"Reference the {job.title} role and remote fit.", "Uses known job title only."),
            _item("Proof point", "Mention the closest AI/backend/project evidence from your packet.", "Keeps the message grounded."),
            _item("Why now", "Connect your current job search to the role requirements.", "Short context for outreach."),
            _item("Soft ask", "Ask whether your AI/backend project background could be relevant for the role.", "Avoids a full generated DM."),
        ],
    )


def _application_checklist(job: Job, match: JobMatch | None) -> list[ApplicationPacketItem]:
    items = [
        "Review role requirements carefully.",
        "Verify remote-from-India eligibility.",
        "Tailor resume summary/title.",
        "Move relevant projects higher.",
        "Add or adjust 3-5 relevant bullets.",
        "Apply through the job/source link.",
        "Save status as applied after submission.",
    ]
    if job.salary_min is None and job.salary_max is None:
        items.append("Compensation not listed; clarify if contacted.")
    if not job.work_authorization:
        items.append("Confirm international/India eligibility.")
    if getattr(match, "is_stale", False):
        items.append("Refresh match score before applying.")
    if not job.apply_url and not job.job_url:
        items.append("Find valid application link before applying.")
    if any(token in _job_text(job) for token in ("intern", "junior", "entry")):
        items.append("Emphasize learning speed, projects and practical implementation.")
    if _role_key(job) == "forward_deployed_engineer":
        items.append("Prepare a story about debugging an ambiguous customer/problem scenario.")
    return [_item("Checklist", value, "Application packet checklist item.") for value in items]


def _risks_to_verify(job: Job, match: JobMatch | None) -> list[ApplicationPacketItem]:
    risks: list[ApplicationPacketItem] = []
    remote = getattr(match, "remote_eligibility", None)
    if remote in {None, "unknown", "remote_eligibility_unclear"}:
        risks.append(_item("Risk", "Remote eligibility not explicit.", "Remote status is missing or unclear."))
    if not job.work_authorization:
        risks.append(_item("Risk", "Work authorization unclear.", "Authorization requirements are not stated."))
    if job.salary_min is None and job.salary_max is None:
        risks.append(_item("Risk", "Salary not listed.", "Compensation is missing but not a blocker."))
    if job.experience_min is not None and job.experience_min > 3:
        risks.append(_item("Risk", "Experience may be above profile.", "Minimum experience is above the target range."))
    if job.job_url and any(host in job.job_url for host in ("himalayas.app", "remotive.com", "weworkremotely.com")):
        risks.append(_item("Risk", "Third-party job board link.", "Application source may redirect."))
    if not getattr(job.company, "website_url", None) and not getattr(job.company, "description", None):
        risks.append(_item("Risk", "Company details limited.", "Company profile has limited stored details."))
    if getattr(match, "is_stale", False):
        risks.append(_item("Risk", "Job score stale.", "Refresh score before applying."))
    if len(job.title.split()) <= 2:
        risks.append(_item("Risk", "Role title broad/generic.", "Broad titles may need extra requirement review."))
    return risks


def _apply_plan(match: JobMatch | None) -> list[ApplicationPacketItem]:
    tier = getattr(match, "match_tier", None)
    if tier in {"best_match", "strong_match"}:
        steps = [
            "Tailor resume toward ML/Python/backend AI.",
            "Apply through the official source link.",
            "Mark job as applied in ScoutAI.",
            "Optionally prepare a short cold DM to the hiring team.",
        ]
    elif tier in {"worth_checking", "stretch"}:
        steps = [
            "Verify experience and remote eligibility.",
            "Tailor resume toward the closest matching skills.",
            "Apply only if requirements look flexible.",
            "Track status as applied or skipped.",
        ]
    elif tier == "unsuitable":
        steps = [
            "Review why it was marked unsuitable.",
            "Skip unless there is a special reason to keep it.",
            "Archive or mark not interested.",
        ]
    else:
        steps = [
            "Review available job details.",
            "Verify remote eligibility and requirements.",
            "Tailor resume only if the role remains relevant.",
        ]
    return [_item(f"Step {index + 1}", value, "Suggested deterministic apply plan.") for index, value in enumerate(steps)]


def _status_for(match: JobMatch | None) -> str:
    tier = getattr(match, "match_tier", None)
    if tier in {"best_match", "strong_match"}:
        return "needs_custom_resume"
    if tier == "unsuitable":
        return "not_interested"
    return "saved"


def _priority_for(match: JobMatch | None) -> str:
    tier = getattr(match, "match_tier", None)
    if tier == "best_match":
        return "high"
    if tier in {"strong_match", "worth_checking"}:
        return "medium"
    return "low"


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
    values: list[Any] = [
        job.title,
        job.role_category,
        *(job.required_skills_json or []),
        *(job.preferred_skills_json or []),
        *(job.technologies_json or []),
    ]
    text = f"{_job_text(job)} {' '.join(str(value or '') for value in values)}"
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
    terms = {normalize_title(str(value)) for value in values if value}
    for token, label in aliases.items():
        if token in text:
            terms.add(normalize_title(label))
    terms.discard("")
    return terms


def _resume_context(job: Job, resume: Any | None) -> dict[str, Any]:
    if resume is None or resume.parse_status != "parsed":
        return {
            "resume_id": getattr(resume, "id", None),
            "resume_used": False,
            "summary": "No active parsed resume is available.",
            "resume_strengths": [],
            "resume_gaps": [],
            "resume_bullet_sources": [],
        }
    resume_terms = _resume_terms(resume)
    job_terms = _job_terms(job)
    overlap = sorted(job_terms & resume_terms)
    missing = sorted(job_terms - resume_terms)
    strengths = [
        _item("Resume strength", _label_from_key(term, resume), "Present in uploaded resume and relevant to this job.")
        for term in overlap[:8]
    ]
    gaps = [
        _item("Resume gap", _display_term(term), "Job signal not found in uploaded resume.")
        for term in missing[:6]
        if term not in {"software engineer", "ai engineer", "ml engineer"}
    ]
    text = " ".join(
        str(value or "")
        for value in (
            resume.raw_text,
            " ".join(resume.skills_json or []),
            " ".join(resume.technologies_json or []),
        )
    ).lower()
    if "remote" not in text and "async" not in text:
        gaps.append(_item("Resume gap", "remote collaboration", "Remote work evidence was not found in uploaded resume."))
    if _role_key(job) in {"ai_engineer", "ml_engineer"} and not ({"llms", "machine learning"} & resume_terms):
        gaps.append(_item("Resume gap", "ML or LLM evidence", "AI role but uploaded resume has limited ML/LLM signal."))
    if {"aws", "docker", "kubernetes"} & job_terms and not ({"aws", "docker", "kubernetes"} & resume_terms):
        gaps.append(_item("Resume gap", "deployment or cloud evidence", "Job asks for deployment/cloud skills not found in uploaded resume."))
    bullets = [
        _item("Resume bullet", f"Emphasize {item.value} work from your uploaded resume.", "Resume-supported packet suggestion.")
        for item in strengths[:5]
    ]
    summary = (
        f"Uploaded resume overlaps with {', '.join(item.value for item in strengths[:4])}."
        if strengths
        else "Uploaded resume was parsed, but no direct job-skill overlap was detected."
    )
    return {
        "resume_id": resume.id,
        "resume_used": True,
        "summary": summary,
        "resume_strengths": strengths,
        "resume_gaps": _dedupe_items(gaps)[:8],
        "resume_bullet_sources": bullets,
    }


def _resume_terms(resume: Any) -> set[str]:
    terms: set[str] = set()
    for value in (resume.skills_json or []) + (resume.technologies_json or []):
        key = normalize_title(str(value))
        if key:
            terms.add(key)
    for project in resume.projects_json or []:
        if isinstance(project, dict):
            text = " ".join(str(project.get(key, "")) for key in ("title", "text"))
        else:
            text = str(project)
        for key in _text_terms(text):
            terms.add(key)
    return terms


def _text_terms(text: str) -> set[str]:
    lowered = text.lower()
    aliases = {
        "python": "python",
        "fastapi": "fastapi",
        "postgresql": "postgresql",
        "postgres": "postgresql",
        "docker": "docker",
        "kubernetes": "kubernetes",
        "aws": "aws",
        "llm": "llms",
        "llms": "llms",
        "machine learning": "machine learning",
    }
    return {normalize_title(label) for token, label in aliases.items() if token in lowered}


def _label_from_key(term: str, resume: Any) -> str:
    for value in (resume.skills_json or []) + (resume.technologies_json or []):
        if normalize_title(str(value)) == term:
            return str(value)
    return _display_term(term)


def _display_term(term: str) -> str:
    return {
        "llms": "LLMs",
        "postgresql": "PostgreSQL",
        "fastapi": "FastAPI",
        "aws": "AWS",
    }.get(term, term.title())


def _overlap_labels(profile_terms: dict[str, str], job_terms: set[str]) -> list[str]:
    return [label for key, label in profile_terms.items() if key in job_terms]


def _role_key(job: Job) -> str:
    return str(getattr(job.role_category, "value", job.role_category) or "software_engineer")


def _job_text(job: Job) -> str:
    return " ".join(str(value or "") for value in (job.title, job.seniority, job.description)).lower()


def _match_snapshot(match: JobMatch | None) -> dict[str, Any] | None:
    if match is None:
        return None
    return {"match_tier": match.match_tier, "total_score": match.total_score, "remote_eligibility": match.remote_eligibility}


def _item(label: str, value: str, reason: str) -> ApplicationPacketItem:
    return ApplicationPacketItem(label=label, value=value, reason=reason)


def _dedupe_items(items: list[ApplicationPacketItem]) -> list[ApplicationPacketItem]:
    seen: set[str] = set()
    deduped: list[ApplicationPacketItem] = []
    for item in items:
        if item.value in seen:
            continue
        seen.add(item.value)
        deduped.append(item)
    return deduped
