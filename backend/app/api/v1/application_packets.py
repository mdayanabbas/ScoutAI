from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.application_packet import ApplicationPacketRequest, ApplicationPacketResponse
from app.services.application_packet_service import ApplicationPacketService

router = APIRouter(prefix="/application-packets", tags=["application-packets"])


def get_application_packet_service(db: Session = Depends(get_db)) -> ApplicationPacketService:
    return ApplicationPacketService(db)


@router.post("/jobs/{job_id}", response_model=ApplicationPacketResponse)
def generate_application_packet_for_job(
    job_id: str,
    data: ApplicationPacketRequest | None = None,
    service: ApplicationPacketService = Depends(get_application_packet_service),
):
    return service.generate_for_job(job_id, data or ApplicationPacketRequest())


@router.post("/decisions/{decision_id}", response_model=ApplicationPacketResponse)
def generate_application_packet_for_decision(
    decision_id: str,
    data: ApplicationPacketRequest | None = None,
    service: ApplicationPacketService = Depends(get_application_packet_service),
):
    return service.generate_for_decision(decision_id, data or ApplicationPacketRequest())
