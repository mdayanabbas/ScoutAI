from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.company_page import (
    CompanyPageCreate,
    CompanyPageListItem,
    CompanyPageRead,
    CompanyPageUpdate,
)
from app.services.company_page_service import CompanyPageService
from app.utils.enums import PageType

router = APIRouter(tags=["company-pages"])


def get_company_page_service(db: Session = Depends(get_db)) -> CompanyPageService:
    return CompanyPageService(db)


@router.post(
    "/companies/{company_id}/pages",
    response_model=CompanyPageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update company page",
)
def create_or_update_company_page(
    company_id: str,
    data: CompanyPageCreate,
    service: CompanyPageService = Depends(get_company_page_service),
):
    return service.create_or_update_page(company_id, data)


@router.get(
    "/companies/{company_id}/pages",
    response_model=PaginatedResponse[CompanyPageListItem],
    summary="List company pages",
)
def list_company_pages(
    company_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    page_type: PageType | None = None,
    service: CompanyPageService = Depends(get_company_page_service),
):
    offset = (page - 1) * page_size
    items = service.list_company_pages(
        company_id,
        offset=offset,
        limit=page_size,
        page_type=page_type,
    )
    total = service.count_company_pages(company_id, page_type=page_type)
    return PaginatedResponse[CompanyPageListItem](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=offset + len(items) < total,
        has_prev=page > 1,
    )


@router.get(
    "/company-pages/{page_id}",
    response_model=CompanyPageRead,
    summary="Get company page",
)
def get_company_page(
    page_id: str,
    service: CompanyPageService = Depends(get_company_page_service),
):
    return service.get_page(page_id)


@router.patch(
    "/company-pages/{page_id}",
    response_model=CompanyPageRead,
    summary="Update company page",
)
def update_company_page(
    page_id: str,
    data: CompanyPageUpdate,
    service: CompanyPageService = Depends(get_company_page_service),
):
    return service.update_page(page_id, data)


@router.delete(
    "/company-pages/{page_id}",
    response_model=MessageResponse,
    summary="Delete company page",
)
def delete_company_page(
    page_id: str,
    service: CompanyPageService = Depends(get_company_page_service),
):
    service.delete_page(page_id)
    return MessageResponse(message="Company page deleted successfully")
