from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.company_enrichment import (
    CandidateEnrichmentResult,
    CompanyEnrichmentAttemptRead,
    ManualCompanyDomainInput,
    RunEnrichmentResult,
)
from app.services.company_domain_enrichment_service import (
    CompanyDomainEnrichmentService,
)

router = APIRouter(prefix="/discovery", tags=["discovery"])


def get_company_domain_enrichment_service(
    db: Session = Depends(get_db),
) -> CompanyDomainEnrichmentService:
    return CompanyDomainEnrichmentService(db)


@router.post(
    "/candidates/{candidate_id}/enrich-domain",
    response_model=CandidateEnrichmentResult,
    status_code=status.HTTP_200_OK,
    summary="Enrich discovery candidate company domain",
)
async def enrich_candidate_domain(
    candidate_id: str,
    service: CompanyDomainEnrichmentService = Depends(
        get_company_domain_enrichment_service
    ),
):
    return await service.enrich_candidate(candidate_id)


@router.post(
    "/runs/{run_id}/enrich-domains",
    response_model=RunEnrichmentResult,
    status_code=status.HTTP_200_OK,
    summary="Enrich discovery run company domains",
)
async def enrich_run_domains(
    run_id: str,
    limit: int | None = Query(default=None, ge=1),
    service: CompanyDomainEnrichmentService = Depends(
        get_company_domain_enrichment_service
    ),
):
    return await service.enrich_discovery_run(run_id, limit=limit)


@router.post(
    "/candidates/{candidate_id}/resolve-domain",
    response_model=CandidateEnrichmentResult,
    status_code=status.HTTP_200_OK,
    summary="Manually resolve discovery candidate domain",
)
async def manually_resolve_candidate_domain(
    candidate_id: str,
    data: ManualCompanyDomainInput,
    service: CompanyDomainEnrichmentService = Depends(
        get_company_domain_enrichment_service
    ),
):
    return await service.manually_resolve_candidate(candidate_id, data.website_url)


@router.get(
    "/candidates/{candidate_id}/enrichment-attempts",
    response_model=list[CompanyEnrichmentAttemptRead],
    summary="List discovery candidate enrichment attempts",
)
def list_candidate_enrichment_attempts(
    candidate_id: str,
    service: CompanyDomainEnrichmentService = Depends(
        get_company_domain_enrichment_service
    ),
):
    return service.list_attempts(candidate_id)
