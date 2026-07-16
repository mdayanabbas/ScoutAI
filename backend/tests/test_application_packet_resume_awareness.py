from datetime import datetime, timezone

from app.models.resume import Resume
from app.repositories.job_repository import JobRepository
from app.repositories.resume_repository import ResumeRepository
from app.schemas.application_packet import ApplicationPacketRequest
from app.services.application_packet_service import ApplicationPacketService

from job_application_decision_helpers import create_job, create_user_profile


def test_packet_without_active_resume_still_generates_and_marks_resume_unused(db_session):
    create_user_profile(db_session)
    job = create_job(db_session)

    packet = ApplicationPacketService(db_session).generate_for_job(job.id, ApplicationPacketRequest(update_decision=False))

    assert packet.resume_used is False
    assert any("No active resume" in item.value for item in packet.risks_to_verify)


def test_packet_uses_active_resume_strengths_and_gaps_without_raw_text(db_session):
    user = create_user_profile(db_session)
    job = create_job(db_session, title="AI Engineer")
    JobRepository(db_session).update_job(
        job,
        {
            "required_skills_json": ["Python", "FastAPI", "Docker"],
            "technologies_json": ["PostgreSQL"],
        },
    )
    resume = ResumeRepository(db_session).create(
        Resume(
            user_profile_id=user.id,
            filename="safe.txt",
            original_filename="resume.txt",
            content_type="text/plain",
            file_size_bytes=10,
            file_sha256="a" * 64,
            storage_path="/tmp/safe.txt",
            is_active=True,
            parse_status="parsed",
            raw_text="Built Python FastAPI systems.",
            parsed_summary_json={"text": "Backend AI work"},
            skills_json=["Python"],
            technologies_json=["FastAPI"],
            projects_json=[{"title": "AI workflow", "text": "Python FastAPI"}],
            experience_json=[],
            education_json=[],
            certifications_json=[],
            links_json=[],
            parsed_at=datetime.now(timezone.utc),
        )
    )

    packet = ApplicationPacketService(db_session).generate_for_job(job.id, ApplicationPacketRequest(update_decision=False))
    text = packet.model_dump_json()

    assert packet.resume_id == resume.id
    assert packet.resume_used is True
    assert any("Python" in item.value for item in packet.resume_strengths)
    assert any("Docker" in item.value or "PostgreSQL" in item.value for item in packet.resume_gaps)
    assert any("Emphasize" in item.value for item in packet.resume_bullet_suggestions)
    assert "Built Python FastAPI systems" not in text
