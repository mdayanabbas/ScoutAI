import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError, ValidationAppError
from app.models.resume import Resume
from app.repositories.profile_repository import UserProfileRepository
from app.repositories.resume_repository import ResumeRepository
from app.resume.parser import ResumeParsedData, ResumeParser
from app.resume.text_extractors import extract_resume_text
from app.schemas.resume import (
    ResumeActivateResponse,
    ResumeListResponse,
    ResumeResponse,
    ResumeUploadResponse,
)
from app.services.resume_upload_service import ResumeUploadService

logger = logging.getLogger(__name__)


class ResumeService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()
        self.user_profile_repository = UserProfileRepository(session)
        self.resume_repository = ResumeRepository(session)
        self.upload_service = ResumeUploadService()
        self.parser = ResumeParser()

    async def upload_resume(self, file: UploadFile, make_active: bool = True) -> ResumeUploadResponse:
        user_profile = self._current_user_profile()
        logger.info("Resume upload started", extra={"user_profile_id": user_profile.id})
        try:
            validated = await self.upload_service.validate(file)
        except ValidationAppError:
            logger.info("Resume validation failed", extra={"user_profile_id": user_profile.id})
            raise
        upload_dir = self._upload_dir()
        storage_path = self._safe_storage_path(upload_dir, validated.safe_filename)
        storage_path.write_bytes(validated.content)
        logger.info("Resume stored", extra={"user_profile_id": user_profile.id, "file_size_bytes": validated.file_size_bytes})
        resume = Resume(
            user_profile_id=user_profile.id,
            filename=validated.safe_filename,
            original_filename=validated.original_filename,
            content_type=validated.content_type,
            file_size_bytes=validated.file_size_bytes,
            file_sha256=validated.file_sha256,
            storage_path=str(storage_path),
            is_active=False,
            parse_status="uploaded",
            skills_json=[],
            technologies_json=[],
            projects_json=[],
            experience_json=[],
            education_json=[],
            certifications_json=[],
            links_json=[],
        )
        resume = self.resume_repository.create(resume)
        warnings = self._parse_resume(resume)
        first_resume = self.resume_repository.count_for_user_profile(user_profile.id) == 1
        if make_active or first_resume:
            resume, _previous = self.resume_repository.set_active(resume)
            logger.info("Resume activated", extra={"resume_id": resume.id})
        return ResumeUploadResponse(resume=to_response(resume), warnings=warnings)

    def list_resumes(self, limit: int = 50, offset: int = 0) -> ResumeListResponse:
        user_profile = self._current_user_profile()
        items = self.resume_repository.list_for_user_profile(user_profile.id, limit=limit, offset=offset)
        return ResumeListResponse(
            items=[to_response(item) for item in items],
            total=self.resume_repository.count_for_user_profile(user_profile.id),
            limit=limit,
            offset=offset,
        )

    def get_resume(self, resume_id: str) -> ResumeResponse:
        return to_response(self._resume_for_current_user(resume_id))

    def get_active_resume(self) -> ResumeResponse:
        user_profile = self._current_user_profile()
        resume = self.resume_repository.get_active_for_user_profile(user_profile.id)
        if resume is None:
            raise NotFoundError("Active resume not found")
        return to_response(resume)

    def get_active_resume_model(self, user_profile_id: str) -> Resume | None:
        return self.resume_repository.get_active_for_user_profile(user_profile_id)

    def activate_resume(self, resume_id: str) -> ResumeActivateResponse:
        resume = self._resume_for_current_user(resume_id)
        resume, previous_id = self.resume_repository.set_active(resume)
        logger.info("Resume activated", extra={"resume_id": resume.id})
        return ResumeActivateResponse(resume_id=resume.id, is_active=resume.is_active, previous_active_resume_id=previous_id)

    def delete_resume(self, resume_id: str) -> None:
        resume = self._resume_for_current_user(resume_id)
        path = Path(resume.storage_path)
        self.resume_repository.delete(resume)
        if self._path_inside_upload_dir(path) and path.exists():
            path.unlink()
        logger.info("Resume deleted", extra={"resume_id": resume_id})

    def reparse_resume(self, resume_id: str) -> ResumeUploadResponse:
        resume = self._resume_for_current_user(resume_id)
        warnings = self._parse_resume(resume)
        return ResumeUploadResponse(resume=to_response(resume), warnings=warnings)

    def _parse_resume(self, resume: Resume) -> list[str]:
        try:
            extracted = extract_resume_text(
                Path(resume.storage_path),
                resume.content_type,
                self.settings.RESUME_TEXT_EXTRACTION_MAX_CHARS,
            )
            parsed = self.parser.parse(extracted.text)
            self.resume_repository.update(resume, parsed_values(parsed, extracted.text))
            logger.info("Resume parsed", extra={"resume_id": resume.id})
            return extracted.warnings + parsed.warnings
        except Exception as exc:
            self.resume_repository.update(
                resume,
                {
                    "parse_status": "failed",
                    "parse_error": str(exc),
                    "parsed_at": datetime.now(timezone.utc),
                },
            )
            logger.info("Resume parse failed", extra={"resume_id": resume.id})
            return ["resume_parse_failed"]

    def _current_user_profile(self):
        user_profile = self.user_profile_repository.get_first_profile()
        if user_profile is None:
            raise NotFoundError("User profile not found")
        return user_profile

    def _resume_for_current_user(self, resume_id: str) -> Resume:
        user_profile = self._current_user_profile()
        resume = self.resume_repository.get_by_user_profile(resume_id, user_profile.id)
        if resume is None:
            raise NotFoundError("Resume not found")
        return resume

    def _upload_dir(self) -> Path:
        path = Path(self.settings.RESUME_UPLOADS_DIR)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()

    def _safe_storage_path(self, upload_dir: Path, filename: str) -> Path:
        candidate = (upload_dir / filename).resolve()
        if upload_dir not in candidate.parents:
            raise ValidationAppError("Resume storage path is invalid")
        return candidate

    def _path_inside_upload_dir(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            upload_dir = self._upload_dir()
            return resolved == upload_dir or upload_dir in resolved.parents
        except OSError:
            return False


def parsed_values(parsed: ResumeParsedData, raw_text: str) -> dict:
    return {
        "parse_status": "parsed",
        "parse_error": None,
        "raw_text": raw_text,
        "parsed_summary_json": parsed.summary,
        "skills_json": parsed.skills,
        "technologies_json": parsed.technologies,
        "projects_json": parsed.projects,
        "experience_json": parsed.experience,
        "education_json": parsed.education,
        "certifications_json": parsed.certifications,
        "links_json": parsed.links,
        "parsed_at": datetime.now(timezone.utc),
    }


def to_response(resume: Resume) -> ResumeResponse:
    return ResumeResponse(
        id=resume.id,
        user_profile_id=resume.user_profile_id,
        filename=resume.filename,
        original_filename=resume.original_filename,
        content_type=resume.content_type,
        file_size_bytes=resume.file_size_bytes,
        is_active=resume.is_active,
        parse_status=resume.parse_status,
        parse_error=resume.parse_error,
        parsed_summary=resume.parsed_summary_json,
        skills=resume.skills_json or [],
        technologies=resume.technologies_json or [],
        projects=resume.projects_json or [],
        experience=resume.experience_json or [],
        education=resume.education_json or [],
        certifications=resume.certifications_json or [],
        links=resume.links_json or [],
        created_at=resume.created_at,
        updated_at=resume.updated_at,
        parsed_at=resume.parsed_at,
    )
