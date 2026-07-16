from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.application_prep import ApplicationPrepRequest, ApplicationPrepResponse
from app.services.application_prep_service import ApplicationPrepService

router = APIRouter(prefix="/application-prep", tags=["application-prep"])


def get_application_prep_service(db: Session = Depends(get_db)) -> ApplicationPrepService:
    return ApplicationPrepService(db)


@router.post("/jobs/{job_id}", response_model=ApplicationPrepResponse)
def generate_application_prep_for_job(
    job_id: str,
    data: ApplicationPrepRequest | None = None,
    service: ApplicationPrepService = Depends(get_application_prep_service),
):
    return service.generate_for_job(job_id, data or ApplicationPrepRequest())


@router.post("/decisions/{decision_id}", response_model=ApplicationPrepResponse)
def generate_application_prep_for_decision(
    decision_id: str,
    data: ApplicationPrepRequest | None = None,
    service: ApplicationPrepService = Depends(get_application_prep_service),
):
    return service.generate_for_decision(decision_id, data or ApplicationPrepRequest())


@router.get("/jobs/{job_id}", response_model=ApplicationPrepResponse)
def get_generated_application_prep_for_job(
    job_id: str,
    service: ApplicationPrepService = Depends(get_application_prep_service),
):
    return service.get_generated_for_job(job_id)
