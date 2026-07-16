from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.resume_improvement import ResumeImprovementRequest, ResumeImprovementResponse
from app.services.resume_improvement_service import ResumeImprovementService

router = APIRouter(prefix="/resume-improvements", tags=["resume-improvements"])


def get_resume_improvement_service(db: Session = Depends(get_db)) -> ResumeImprovementService:
    return ResumeImprovementService(db)


@router.post("/jobs/{job_id}", response_model=ResumeImprovementResponse)
def generate_resume_improvement_for_job(
    job_id: str,
    data: ResumeImprovementRequest | None = None,
    service: ResumeImprovementService = Depends(get_resume_improvement_service),
):
    return service.generate_for_job(job_id, data or ResumeImprovementRequest())


@router.post("/decisions/{decision_id}", response_model=ResumeImprovementResponse)
def generate_resume_improvement_for_decision(
    decision_id: str,
    data: ResumeImprovementRequest | None = None,
    service: ResumeImprovementService = Depends(get_resume_improvement_service),
):
    return service.generate_for_decision(decision_id, data or ResumeImprovementRequest())
