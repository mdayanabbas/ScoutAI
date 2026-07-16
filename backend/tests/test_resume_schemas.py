from datetime import datetime, timezone

from app.schemas.resume import ResumeResponse


def test_resume_response_does_not_expose_storage_path_or_raw_text():
    response = ResumeResponse(
        id="resume-1",
        user_profile_id="user-1",
        filename="safe.txt",
        original_filename="resume.txt",
        file_size_bytes=10,
        is_active=True,
        parse_status="parsed",
        parsed_summary={"text": "summary"},
        skills=["Python"],
        technologies=["FastAPI"],
        created_at=datetime.now(timezone.utc),
    )

    data = response.model_dump()
    assert "storage_path" not in data
    assert "raw_text" not in data
    assert data["skills"] == ["Python"]
