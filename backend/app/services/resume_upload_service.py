from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
import uuid

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import ValidationAppError


REJECTED_EXTENSIONS = {".doc", ".rtf", ".exe", ".zip", ".html", ".js"}


@dataclass
class ValidatedResumeUpload:
    original_filename: str
    safe_filename: str
    content_type: str | None
    file_size_bytes: int
    file_sha256: str
    content: bytes
    extension: str


class ResumeUploadService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def validate(self, file: UploadFile) -> ValidatedResumeUpload:
        if file is None:
            raise ValidationAppError("Resume file is required")
        original = Path(file.filename or "").name
        if not original:
            raise ValidationAppError("Resume filename is required")
        if original != (file.filename or ""):
            raise ValidationAppError("Resume filename is invalid")
        extension = Path(original).suffix.lower()
        if extension in REJECTED_EXTENSIONS or extension not in allowed_extensions(self.settings.RESUME_ALLOWED_EXTENSIONS):
            raise ValidationAppError("Resume file extension is not allowed")
        content_type = file.content_type or "application/octet-stream"
        if not content_type_allowed(content_type, extension, self.settings.RESUME_ALLOWED_CONTENT_TYPES):
            raise ValidationAppError("Resume content type is not allowed")
        content = await file.read()
        size = len(content)
        if size <= 0:
            raise ValidationAppError("Resume file is empty")
        if size > self.settings.RESUME_MAX_FILE_SIZE_BYTES:
            raise ValidationAppError("Resume file is too large")
        digest = sha256(content).hexdigest()
        safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", Path(original).stem).strip(".-")[:80] or "resume"
        safe_filename = f"{uuid.uuid4().hex}_{safe_stem}{extension}"
        return ValidatedResumeUpload(
            original_filename=original,
            safe_filename=safe_filename,
            content_type=content_type,
            file_size_bytes=size,
            file_sha256=digest,
            content=content,
            extension=extension,
        )


def allowed_extensions(value: str) -> set[str]:
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def content_type_allowed(content_type: str, extension: str, allowed: str) -> bool:
    allowed_types = {item.strip().lower() for item in allowed.split(",") if item.strip()}
    normalized = content_type.split(";")[0].lower()
    if normalized in allowed_types and normalized != "application/octet-stream":
        return True
    return normalized == "application/octet-stream" and extension in {".pdf", ".docx", ".txt"}
