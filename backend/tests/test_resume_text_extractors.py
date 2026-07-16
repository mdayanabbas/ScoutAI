from pathlib import Path

from app.resume.text_extractors import extract_resume_text, normalize_whitespace


def test_txt_extractor_decodes_normalizes_and_caps(tmp_path: Path):
    path = tmp_path / "resume.txt"
    path.write_text("Python   FastAPI\n\n\nPostgreSQL", encoding="utf-8")

    result = extract_resume_text(path, "text/plain", max_chars=20)

    assert result.text == "Python FastAPI\n\nPos"
    assert "extracted_text_truncated" in result.warnings


def test_normalize_whitespace_preserves_clean_paragraph_breaks():
    text = "  Python\t\tFastAPI  \n  \n \n PostgreSQL  "

    assert normalize_whitespace(text) == "Python FastAPI\n\nPostgreSQL"
