from pathlib import Path

import pytest
from fastapi import UploadFile

from app.services.resume_service import ResumeService

from job_application_decision_helpers import create_user_profile


def _upload(path: Path, content: bytes, content_type: str = "text/plain") -> UploadFile:
    path.write_bytes(content)
    return UploadFile(filename=path.name, file=path.open("rb"), headers={"content-type": content_type})


@pytest.mark.asyncio
async def test_resume_service_upload_list_activate_delete_txt(db_session, tmp_path, monkeypatch):
    create_user_profile(db_session)
    service = ResumeService(db_session)
    monkeypatch.setattr(service.settings, "RESUME_UPLOADS_DIR", str(tmp_path / "uploads"))

    first = await service.upload_resume(_upload(tmp_path / "resume.txt", b"Skills\nPython, FastAPI\nProjects\nScoutAI"), make_active=True)
    second = await service.upload_resume(_upload(tmp_path / "resume2.txt", b"Skills\nDocker"), make_active=True)

    assert first.resume.parse_status == "parsed"
    assert first.resume.is_active is True
    assert second.resume.is_active is True
    assert service.get_active_resume().id == second.resume.id
    assert service.list_resumes().total == 2

    service.activate_resume(first.resume.id)
    assert service.get_active_resume().id == first.resume.id
    service.delete_resume(second.resume.id)
    assert service.list_resumes().total == 1


@pytest.mark.asyncio
async def test_resume_service_rejects_invalid_uploads(db_session, tmp_path, monkeypatch):
    create_user_profile(db_session)
    service = ResumeService(db_session)
    monkeypatch.setattr(service.settings, "RESUME_UPLOADS_DIR", str(tmp_path / "uploads"))

    with pytest.raises(Exception):
        await service.upload_resume(_upload(tmp_path / "bad.exe", b"nope", "application/octet-stream"))
