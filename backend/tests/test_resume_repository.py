from app.models.resume import Resume
from app.repositories.resume_repository import ResumeRepository

from job_application_decision_helpers import create_user_profile


def _resume(user_profile_id: str, filename: str, active: bool = False):
    return Resume(
        user_profile_id=user_profile_id,
        filename=filename,
        original_filename=filename,
        content_type="text/plain",
        file_size_bytes=12,
        file_sha256=f"{filename:0<64}"[:64],
        storage_path=f"/tmp/{filename}",
        is_active=active,
        parse_status="parsed",
        skills_json=[],
        technologies_json=[],
        projects_json=[],
        experience_json=[],
        education_json=[],
        certifications_json=[],
        links_json=[],
    )


def test_resume_repository_set_active_deactivates_previous(db_session):
    user = create_user_profile(db_session)
    repository = ResumeRepository(db_session)
    first = repository.create(_resume(user.id, "first.txt", active=True))
    second = repository.create(_resume(user.id, "second.txt"))

    activated, previous_id = repository.set_active(second)

    assert activated.is_active is True
    assert previous_id == first.id
    assert repository.get_by_id(first.id).is_active is False
    assert repository.get_active_for_user_profile(user.id).id == second.id
