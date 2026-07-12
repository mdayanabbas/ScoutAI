from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.session import get_db
from app.schemas.user_profile import (
    UserProfileCreate,
    UserProfileRead,
    UserProfileUpdate,
)
from app.schemas.job_matching_profile import (
    JobMatchingProfileCreate,
    JobMatchingProfileRead,
    JobMatchingProfileUpdate,
)
from app.schemas.common import MessageResponse
from app.services.job_matching_profile_service import JobMatchingProfileService
from app.services.user_profile_service import UserProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


def get_user_profile_service(db: Session = Depends(get_db)) -> UserProfileService:
    return UserProfileService(db)


def get_job_matching_profile_service(
    db: Session = Depends(get_db),
) -> JobMatchingProfileService:
    return JobMatchingProfileService(db)


@router.get(
    "",
    response_model=UserProfileRead,
    summary="Get user profile",
)
def get_profile(
    service: UserProfileService = Depends(get_user_profile_service),
):
    profile = service.get_profile()
    if profile is None:
        raise NotFoundError("User profile not found")
    return profile


@router.get(
    "/job-matching",
    response_model=JobMatchingProfileRead,
    summary="Get job matching profile",
)
def get_job_matching_profile(
    service: JobMatchingProfileService = Depends(get_job_matching_profile_service),
):
    return service.get_for_current_profile()


@router.put(
    "/job-matching",
    response_model=JobMatchingProfileRead,
    summary="Create or replace job matching profile",
)
def create_or_replace_job_matching_profile(
    data: JobMatchingProfileCreate,
    service: JobMatchingProfileService = Depends(get_job_matching_profile_service),
):
    return service.create_or_replace(data)


@router.patch(
    "/job-matching",
    response_model=JobMatchingProfileRead,
    summary="Update job matching profile",
)
def update_job_matching_profile(
    data: JobMatchingProfileUpdate,
    service: JobMatchingProfileService = Depends(get_job_matching_profile_service),
):
    return service.partial_update(data)


@router.delete(
    "/job-matching",
    response_model=MessageResponse,
    summary="Reset job matching profile",
)
def reset_job_matching_profile(
    service: JobMatchingProfileService = Depends(get_job_matching_profile_service),
):
    service.reset()
    return MessageResponse(message="Job matching profile reset successfully")


@router.put(
    "",
    response_model=UserProfileRead,
    summary="Create or replace user profile",
)
def create_or_replace_profile(
    data: UserProfileCreate,
    service: UserProfileService = Depends(get_user_profile_service),
):
    return service.create_or_update_profile(data)


@router.patch(
    "",
    response_model=UserProfileRead,
    summary="Update user profile",
)
def update_profile(
    data: UserProfileUpdate,
    service: UserProfileService = Depends(get_user_profile_service),
):
    return service.update_profile(data)
