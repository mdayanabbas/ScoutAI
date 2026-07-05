from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.session import get_db
from app.schemas.user_profile import (
    UserProfileCreate,
    UserProfileRead,
    UserProfileUpdate,
)
from app.services.user_profile_service import UserProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


def get_user_profile_service(db: Session = Depends(get_db)) -> UserProfileService:
    return UserProfileService(db)


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
