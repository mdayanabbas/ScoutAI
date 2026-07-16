from dataclasses import dataclass, field
from pathlib import Path
import re

from app.core.errors import ValidationAppError


@dataclass
class ExtractedResumeText:
    text: str
    warnings: list[str] = field(default_factory=list)


def extract_resume_text(path: Path, content_type: str | None, max_chars: int) -> ExtractedResumeText:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return extract_txt(path, max_chars)
    if suffix == ".pdf":
        return extract_pdf(path, max_chars)
    if suffix == ".docx":
        return extract_docx(path, max_chars)
    raise ValidationAppError("Unsupported resume file type")


def extract_txt(path: Path, max_chars: int) -> ExtractedResumeText:
    warnings: list[str] = []
    data = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig"):
        try:
            return ExtractedResumeText(_cap(normalize_whitespace(data.decode(encoding)), max_chars, warnings), warnings)
        except UnicodeDecodeError:
            continue
    raise ValidationAppError("Resume text file is not valid UTF-8")


def extract_pdf(path: Path, max_chars: int) -> ExtractedResumeText:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValidationAppError("PDF resume extraction dependency is not installed") from exc
    warnings: list[str] = []
    try:
        reader = PdfReader(str(path))
        if getattr(reader, "is_encrypted", False):
            raise ValidationAppError("Encrypted PDF resumes are not supported")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except ValidationAppError:
        raise
    except Exception as exc:
        raise ValidationAppError("PDF resume could not be read") from exc
    return ExtractedResumeText(_cap(normalize_whitespace(text), max_chars, warnings), warnings)


def extract_docx(path: Path, max_chars: int) -> ExtractedResumeText:
    try:
        from docx import Document
    except ImportError as exc:
        raise ValidationAppError("DOCX resume extraction dependency is not installed") from exc
    warnings: list[str] = []
    try:
        document = Document(str(path))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception as exc:
        raise ValidationAppError("DOCX resume could not be read") from exc
    return ExtractedResumeText(_cap(normalize_whitespace(text), max_chars, warnings), warnings)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t\f\v]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _cap(text: str, max_chars: int, warnings: list[str]) -> str:
    if len(text) > max_chars:
        warnings.append("extracted_text_truncated")
        limit = max_chars - 1 if max_chars > 1 else max_chars
        return text[:limit]
    return text
