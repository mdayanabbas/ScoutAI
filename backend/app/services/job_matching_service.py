import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.matching.remote_eligibility import REMOTE_PRIORITY, RemoteEligibilityClassifier
from app.matching.role_matcher import TargetRoleMatcher
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.job_matching_profile import JobMatchingProfile
from app.repositories.job_match_repository import JobMatchRepository
from app.repositories.job_matching_profile_repository import JobMatchingProfileRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import UserProfileRepository
from app.utils.enums import JobStatus
from app.utils.text import normalize_title

logger = logging.getLogger(__name__)

SCORING_VERSION = "job-match-v1"


@dataclass(frozen=True)
class ScoredJob:
    data: dict[str, Any]
    action: str
    explanation: str


@dataclass(frozen=True)
class BatchScoreResult:
    jobs_examined: int = 0
    jobs_scored: int = 0
    jobs_created: int = 0
    jobs_updated: int = 0
    jobs_failed: int = 0
    eligible: int = 0
    stretch: int = 0
    uncertain: int = 0
    unsuitable: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    results: list[dict[str, Any]] = field(default_factory=list)

    @property
    def duration_ms(self) -> int:
        return int((self.finished_at - self.started_at).total_seconds() * 1000)


class JobMatchingService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.job_repository = JobRepository(session)
        self.user_profile_repository = UserProfileRepository(session)
        self.profile_repository = JobMatchingProfileRepository(session)
        self.match_repository = JobMatchRepository(session)
        self.remote_classifier = RemoteEligibilityClassifier()
        self.role_matcher = TargetRoleMatcher()

    def current_profile(self) -> JobMatchingProfile:
        user_profile = self.user_profile_repository.get_first_profile()
        if user_profile is None:
            raise NotFoundError("User profile not found")
        profile = self.profile_repository.get_by_user_profile_id(user_profile.id)
        if profile is None:
            raise NotFoundError("Job matching profile not found")
        return profile

    def score_job(self, profile_id: str, job_id: str) -> tuple[JobMatch, str]:
        profile = self.profile_repository.get_by_id(profile_id)
        if profile is None:
            raise NotFoundError("Job matching profile not found")
        job = self.job_repository.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job not found")
        logger.info("Job scoring started", extra={"job_id": job.id, "profile_id": profile.id})
        scored = self._score(job, profile)
        match, action = self.match_repository.upsert_match(profile.id, job.id, scored.data)
        logger.info("JobMatch %s", action, extra={"job_id": job.id, "match_id": match.id})
        return match, action

    def score_jobs(
        self,
        profile_id: str,
        *,
        job_ids: list[str] | None = None,
        limit: int | None = None,
        force: bool = False,
    ) -> BatchScoreResult:
        profile = self.profile_repository.get_by_id(profile_id)
        if profile is None:
            raise NotFoundError("Job matching profile not found")
        started = datetime.now(timezone.utc)
        jobs = self._jobs_to_score(job_ids, limit)
        counters = {"eligible": 0, "stretch": 0, "uncertain": 0, "unsuitable": 0}
        created = updated = failed = scored_count = 0
        results: list[dict[str, Any]] = []
        for job in jobs:
            try:
                existing = self.match_repository.get_by_profile_and_job(profile.id, job.id)
                if existing and not force and not self.is_stale(existing, profile):
                    results.append({"job_id": job.id, "status": "skipped", "reason": "match_current"})
                    continue
                match, action = self.score_job(profile.id, job.id)
                scored_count += 1
                created += 1 if action == "created" else 0
                updated += 1 if action == "updated" else 0
                counters[match.eligibility_status] = counters.get(match.eligibility_status, 0) + 1
                results.append({"job_id": job.id, "status": "scored", "match_id": match.id, "eligibility_status": match.eligibility_status})
            except Exception as exc:
                self.session.rollback()
                failed += 1
                logger.info("Job scoring failed", extra={"job_id": getattr(job, "id", None), "error": exc.__class__.__name__})
                results.append({"job_id": getattr(job, "id", None), "status": "failed", "reason": exc.__class__.__name__})
        finished = datetime.now(timezone.utc)
        logger.info("Batch scoring completed", extra={"jobs_examined": len(jobs), "jobs_scored": scored_count, "jobs_failed": failed})
        return BatchScoreResult(
            jobs_examined=len(jobs),
            jobs_scored=scored_count,
            jobs_created=created,
            jobs_updated=updated,
            jobs_failed=failed,
            eligible=counters.get("eligible", 0),
            stretch=counters.get("stretch", 0),
            uncertain=counters.get("uncertain", 0),
            unsuitable=counters.get("unsuitable", 0),
            started_at=started,
            finished_at=finished,
            results=results,
        )

    def get_match(self, profile_id: str, job_id: str) -> JobMatch:
        if self.job_repository.get_by_id(job_id) is None:
            raise NotFoundError("Job not found")
        match = self.match_repository.get_by_profile_and_job(profile_id, job_id)
        if match is None:
            raise NotFoundError("Job match not found")
        return match

    def list_matches(
        self,
        profile_id: str,
        *,
        eligibility_status: str | None = None,
        match_tier: str | None = None,
        remote_eligibility: str | None = None,
        minimum_score: float | None = None,
        include_unsuitable: bool = False,
        limit: int = 20,
        offset: int = 0,
        order_by: str = "recommended",
    ) -> list[JobMatch]:
        matches = self.match_repository.list_for_profile(
            profile_id,
            eligibility_status=eligibility_status,
            match_tier=match_tier,
            remote_eligibility=remote_eligibility,
            minimum_score=minimum_score,
            include_unsuitable=include_unsuitable,
            limit=500,
            offset=0,
        )
        return _sort_matches(matches, order_by)[offset : offset + limit]

    def is_stale(self, match: JobMatch, profile: JobMatchingProfile | None = None) -> bool:
        profile = profile or match.job_matching_profile
        job = match.job
        return bool(
            match.scoring_version != SCORING_VERSION
            or (job.updated_at and job.updated_at > match.scored_at)
            or (profile.updated_at and profile.updated_at > match.scored_at)
        )

    def _jobs_to_score(self, job_ids: list[str] | None, limit: int | None) -> list[Job]:
        if job_ids:
            jobs: list[Job] = []
            for job_id in job_ids:
                job = self.job_repository.get_by_id(job_id)
                if job is not None:
                    jobs.append(job)
            return jobs
        return self.job_repository.list_jobs(limit=limit or 100, status=JobStatus.ACTIVE.value)

    def _score(self, job: Job, profile: JobMatchingProfile) -> ScoredJob:
        role = self.role_matcher.match(job, profile)
        remote = self.remote_classifier.classify(job, profile)
        hard_filters: list[str] = []
        positives = [*role.positive_signals, *remote.positive_signals]
        negatives = [*role.negative_signals, *remote.negative_signals]
        missing: list[str] = []
        if _excluded_company(job, profile):
            hard_filters.append("excluded_company")
        if role.match_type == "excluded":
            hard_filters.append(role.reason)
        if remote.classification in {"onsite", "hybrid"}:
            hard_filters.append(remote.classification)
        if remote.classification == "remote_country_restricted":
            hard_filters.append("remote_country_restriction_excludes_india")
        if remote.reason == "authorization_restriction":
            hard_filters.append("authorization_restriction")
        elif _authorization_restricted(job):
            hard_filters.append("authorization_restriction")
        seniority_score, seniority_reason, seniority_hard = _seniority_score(job)
        if seniority_hard:
            hard_filters.append(seniority_reason)
        experience_score, experience_reason, experience_hard = _experience_score(job)
        if experience_hard:
            hard_filters.append(experience_reason)
        if not role.matched:
            negatives.append("no_target_role_match")
        remote_score = _remote_score(remote.classification)
        employment_score = _employment_score(job, profile)
        skills_score = _overlap_score(getattr(profile, "skills_json", None), _job_skills(job), neutral=60)
        tech_score = _overlap_score(getattr(profile, "technologies_json", None), getattr(job, "technologies_json", None), neutral=60)
        salary_score = _salary_score(job, profile)
        company_score = _company_score(job, profile)
        confidence_score = _confidence_score(job, role.confidence, remote.confidence)
        if (
            not getattr(job, "location", None)
            and remote.classification not in {"work_from_anywhere", "remote_india_eligible", "remote_global_unspecified"}
        ):
            missing.append("location")
        if (
            not getattr(job, "work_authorization", None)
            and remote.classification not in {"work_from_anywhere", "remote_india_eligible", "remote_global_unspecified"}
        ):
            missing.append("work_authorization")
        if getattr(job, "experience_min", None) is None:
            missing.append("experience")
        total = round(
            role.score * 0.30
            + remote_score * 0.25
            + seniority_score * 0.15
            + experience_score * 0.10
            + employment_score * 0.05
            + skills_score * 0.07
            + tech_score * 0.03
            + salary_score * 0.03
            + company_score * 0.02,
            2,
        )
        eligibility = _eligibility(hard_filters, role, remote.classification, job, seniority_score, experience_score, missing)
        tier = _tier(eligibility, total, role.score, remote_score)
        explanation = _explanation(eligibility, role.canonical_role, remote.classification, hard_filters, experience_reason)
        if eligibility == "unsuitable":
            total = min(total, 30)
            tier = "unsuitable"
        now = datetime.now(timezone.utc)
        breakdown = {
            "role": role.reason,
            "remote": remote.reason,
            "seniority": seniority_reason,
            "experience": experience_reason,
            "explanation": explanation,
        }
        return ScoredJob(
            data={
                "eligibility_status": eligibility,
                "eligibility_reason": explanation,
                "remote_eligibility": remote.classification,
                "match_tier": tier,
                "total_score": total,
                "role_score": role.score,
                "seniority_score": seniority_score,
                "remote_score": remote_score,
                "experience_score": experience_score,
                "employment_type_score": employment_score,
                "skills_score": skills_score,
                "technology_score": tech_score,
                "salary_score": salary_score,
                "company_score": company_score,
                "confidence_score": confidence_score,
                "hard_filter_reasons_json": hard_filters,
                "positive_signals_json": positives,
                "negative_signals_json": negatives,
                "missing_information_json": missing,
                "score_breakdown_json": breakdown,
                "scoring_version": SCORING_VERSION,
                "scored_at": now,
            },
            action="",
            explanation=explanation,
        )


def _seniority_score(job: Job) -> tuple[int, str, bool]:
    text = f"{getattr(job, 'title', '')} {getattr(job, 'seniority', '')}".lower()
    senior = {"senior", "staff", "principal", "lead", "manager", "director", "executive"}
    if any(word in text.split() for word in senior) or any(word in text for word in ("senior ", "staff ", "principal ", "lead ")):
        return 0, "seniority_hard_exclusion", True
    if any(word in text for word in ("intern", "entry", "junior", "new grad", "associate", "engineer i")):
        return 100, "junior_or_entry", False
    if "mid" in text:
        return 45, "mid_level", False
    return 70, "unknown_or_open_seniority", False


def _experience_score(job: Job) -> tuple[int, str, bool]:
    years = getattr(job, "experience_min", None)
    if years is None:
        return 60, "missing_experience", False
    if years <= 1:
        return 100, "zero_to_one_year", False
    if years == 2:
        return 95, "two_years", False
    if years == 3:
        return 65, "three_year_stretch", False
    if years == 4:
        return 30, "four_year_weak", True
    return 0, "experience_min_too_high", True


def _remote_score(value: str) -> int:
    return {
        "work_from_anywhere": 100,
        "remote_india_eligible": 100,
        "remote_global_unspecified": 85,
        "remote_eligibility_unclear": 60,
        "remote_region_restricted": 25,
        "remote_country_restricted": 0,
        "hybrid": 0,
        "onsite": 0,
        "unknown": 35,
    }.get(value, 35)


def _employment_score(job: Job, profile: JobMatchingProfile) -> int:
    accepted = set(profile.accepted_employment_types_json or [])
    value = str(getattr(job, "employment_type", "") or "")
    if not value:
        return 60
    if value == "cofounder" and value not in accepted:
        return 0
    if not accepted:
        return 80 if value in {"full_time", "contract", "internship"} else 40
    if value in accepted:
        return {"full_time": 100, "contract": 90, "internship": 85}.get(value, 80)
    return 20


def _overlap_score(profile_items: Any, job_items: Any, *, neutral: int) -> int:
    profile = {_skill_key(item.get("name") if isinstance(item, dict) else item) for item in (profile_items or [])}
    job = {_skill_key(item) for item in (job_items or [])}
    profile.discard("")
    job.discard("")
    if not job:
        return neutral
    if not profile:
        return neutral
    hits = len(profile & job)
    if hits >= 3:
        return 95
    if hits == 2:
        return 80
    if hits == 1:
        return 55
    return 25


def _job_skills(job: Job) -> list[str]:
    return [*(job.required_skills_json or []), *(job.preferred_skills_json or []), *(job.technologies_json or [])]


def _skill_key(value: Any) -> str:
    aliases = {"llms": "llm", "backend development": "backend", "machine learning": "ml"}
    key = normalize_title(str(value or "")) or ""
    return aliases.get(key, key)


def _salary_score(job: Job, profile: JobMatchingProfile) -> int:
    if profile.minimum_salary and profile.salary_currency:
        if job.salary_min and job.salary_currency and str(job.salary_currency).upper() == profile.salary_currency.upper():
            return 90 if Decimal(job.salary_min) >= profile.minimum_salary else 30
        return 60
    if job.salary_min or job.salary_max:
        return 75
    if job.salary_text and "equity" in job.salary_text.lower() and "salary" not in job.salary_text.lower():
        return 0
    return 60


def _company_score(job: Job, profile: JobMatchingProfile) -> int:
    company = getattr(job, "company", None)
    if not company:
        return 60
    if profile.preferred_company_stages_json and str(getattr(company, "stage", "")) in profile.preferred_company_stages_json:
        return 80
    return 60


def _confidence_score(job: Job, role_confidence: float, remote_confidence: float) -> int:
    score = 40 + int(role_confidence * 25) + int(remote_confidence * 20)
    if getattr(job, "enrichment_status", "") == "enriched":
        score += 15
    return min(100, score)


def _excluded_company(job: Job, profile: JobMatchingProfile) -> bool:
    return bool(job.company_id and job.company_id in set(profile.excluded_company_ids_json or []))


def _authorization_restricted(job: Job) -> bool:
    text = " ".join(
        str(item or "")
        for item in (
            getattr(job, "description", None),
            getattr(job, "work_authorization", None),
            getattr(job, "visa_sponsorship", None),
        )
    ).lower()
    return any(
        token in text
        for token in (
            "us citizenship required",
            "u.s. citizenship required",
            "security clearance required",
            "ts/sci required",
            "existing us work authorization",
            "must be authorized to work in the united states",
        )
    )


def _eligibility(
    hard_filters: list[str],
    role: Any,
    remote: str,
    job: Job,
    seniority_score: int,
    experience_score: int,
    missing: list[str],
) -> str:
    if hard_filters:
        return "unsuitable"
    if not role.matched:
        return "unsuitable"
    if experience_score in {65, 30} or seniority_score == 45 or remote in {"remote_region_restricted", "remote_eligibility_unclear"}:
        return "stretch"
    if missing or getattr(job, "enrichment_status", "") in {"not_enriched", "partially_enriched"} or remote in {"unknown"}:
        return "uncertain"
    return "eligible"


def _tier(eligibility: str, total: float, role_score: int, remote_score: int) -> str:
    if eligibility == "unsuitable" or role_score == 0:
        return "unsuitable"
    if eligibility == "stretch":
        return "stretch"
    if eligibility == "eligible" and total >= 85 and role_score >= 90 and remote_score >= 85:
        return "best_match"
    if eligibility == "eligible" and total >= 70:
        return "strong_match"
    if eligibility in {"eligible", "uncertain"} and total >= 55:
        return "worth_checking"
    return "stretch" if eligibility == "uncertain" else "unsuitable"


def _explanation(eligibility: str, role: str | None, remote: str, hard_filters: list[str], experience_reason: str) -> str:
    if eligibility == "unsuitable":
        return "Unsuitable: " + ", ".join(hard_filters or ["hard filter triggered"]) + "."
    if eligibility == "stretch":
        return f"Stretch: target {role or 'role'} role, remote eligibility is {remote}, and {experience_reason}."
    if eligibility == "uncertain":
        return f"Worth checking: target {role or 'role'} role, but important eligibility details are missing."
    return f"Strong match: {role or 'target'} role with {remote.replace('_', ' ')} eligibility."


def _sort_matches(matches: list[JobMatch], order_by: str) -> list[JobMatch]:
    if order_by == "newest":
        return sorted(matches, key=lambda item: item.job.published_at or item.job.created_at, reverse=True)
    if order_by == "salary":
        return sorted(matches, key=lambda item: item.job.salary_max or item.job.salary_min or 0, reverse=True)
    tier_rank = {"best_match": 0, "strong_match": 1, "worth_checking": 2, "stretch": 3, "unsuitable": 4}
    return sorted(
        matches,
        key=lambda item: (
            tier_rank.get(item.match_tier, 9),
            REMOTE_PRIORITY.get(item.remote_eligibility, 9),
            -item.total_score,
            -(item.job.published_at or item.job.created_at).timestamp(),
        ),
    )
