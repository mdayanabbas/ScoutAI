from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import MessageResponse
from app.schemas.tech_stack_item import (
    TechStackItemCreate,
    TechStackItemRead,
    TechStackItemUpdate,
)
from app.services.tech_stack_service import TechStackService

router = APIRouter(tags=["tech-stack"])


def get_tech_stack_service(db: Session = Depends(get_db)) -> TechStackService:
    return TechStackService(db)


@router.post(
    "/companies/{company_id}/tech-stack",
    response_model=TechStackItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update company tech stack item",
)
def create_or_update_tech_stack_item(
    company_id: str,
    data: TechStackItemCreate,
    service: TechStackService = Depends(get_tech_stack_service),
):
    return service.create_or_update_item(company_id, data)


@router.get(
    "/companies/{company_id}/tech-stack",
    response_model=list[TechStackItemRead],
    summary="List company tech stack",
)
def list_company_tech_stack(
    company_id: str,
    service: TechStackService = Depends(get_tech_stack_service),
):
    return service.list_company_tech_stack(company_id)


@router.patch(
    "/tech-stack/{item_id}",
    response_model=TechStackItemRead,
    summary="Update tech stack item",
)
def update_tech_stack_item(
    item_id: str,
    data: TechStackItemUpdate,
    service: TechStackService = Depends(get_tech_stack_service),
):
    return service.update_item(item_id, data)


@router.delete(
    "/tech-stack/{item_id}",
    response_model=MessageResponse,
    summary="Delete tech stack item",
)
def delete_tech_stack_item(
    item_id: str,
    service: TechStackService = Depends(get_tech_stack_service),
):
    service.delete_item(item_id)
    return MessageResponse(message="Tech stack item deleted successfully")
