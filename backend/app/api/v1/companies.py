from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.company import (
    CompanyCreate,
    CompanyListItem,
    CompanyRead,
    CompanyUpdate,
)
from app.services.company_service import CompanyService
from app.utils.enums import CompanySource, CompanyStage

router = APIRouter(prefix="/companies", tags=["companies"])


def get_company_service(db: Session = Depends(get_db)) -> CompanyService:
    return CompanyService(db)


@router.post(
    "",
    response_model=CompanyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a company",
)
def create_company(
    data: CompanyCreate,
    service: CompanyService = Depends(get_company_service),
):
    return service.create_company(data)


@router.get(
    "",
    response_model=PaginatedResponse[CompanyListItem],
    summary="List companies",
)
def list_companies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    source: CompanySource | None = None,
    stage: CompanyStage | None = None,
    is_active: bool | None = None,
    service: CompanyService = Depends(get_company_service),
):
    offset = (page - 1) * page_size
    items = service.list_companies(
        offset=offset,
        limit=page_size,
        search=search,
        source=source,
        stage=stage,
        is_active=is_active,
    )
    total = service.count_companies(
        search=search,
        source=source,
        stage=stage,
        is_active=is_active,
    )
    return PaginatedResponse[CompanyListItem](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=offset + len(items) < total,
        has_prev=page > 1,
    )


@router.get(
    "/{company_id}",
    response_model=CompanyRead,
    summary="Get a company",
)
def get_company(
    company_id: str,
    service: CompanyService = Depends(get_company_service),
):
    return service.get_company(company_id)


@router.patch(
    "/{company_id}",
    response_model=CompanyRead,
    summary="Update a company",
)
def update_company(
    company_id: str,
    data: CompanyUpdate,
    service: CompanyService = Depends(get_company_service),
):
    return service.update_company(company_id, data)


@router.delete(
    "/{company_id}",
    response_model=MessageResponse,
    summary="Delete a company",
)
def delete_company(
    company_id: str,
    service: CompanyService = Depends(get_company_service),
):
    service.delete_company(company_id)
    return MessageResponse(message="Company deleted successfully")
