from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.resume import ResumeActivateResponse, ResumeListResponse, ResumeResponse, ResumeUploadResponse
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/resumes", tags=["resumes"])


def get_resume_service(db: Session = Depends(get_db)) -> ResumeService:
    return ResumeService(db)


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    make_active: bool = Form(True),
    service: ResumeService = Depends(get_resume_service),
):
    return await service.upload_resume(file, make_active=make_active)


@router.get("", response_model=ResumeListResponse)
def list_resumes(
    limit: int = 50,
    offset: int = 0,
    service: ResumeService = Depends(get_resume_service),
):
    return service.list_resumes(limit=limit, offset=offset)


@router.get("/active", response_model=ResumeResponse)
def get_active_resume(service: ResumeService = Depends(get_resume_service)):
    return service.get_active_resume()


@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: str, service: ResumeService = Depends(get_resume_service)):
    return service.get_resume(resume_id)


@router.post("/{resume_id}/activate", response_model=ResumeActivateResponse)
def activate_resume(resume_id: str, service: ResumeService = Depends(get_resume_service)):
    return service.activate_resume(resume_id)


@router.post("/{resume_id}/reparse", response_model=ResumeUploadResponse)
def reparse_resume(resume_id: str, service: ResumeService = Depends(get_resume_service)):
    return service.reparse_resume(resume_id)


@router.delete("/{resume_id}", status_code=204)
def delete_resume(resume_id: str, service: ResumeService = Depends(get_resume_service)):
    service.delete_resume(resume_id)
    return None
