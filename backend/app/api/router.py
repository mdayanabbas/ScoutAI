from fastapi import APIRouter

from app.api.v1.agent_runs import router as agent_runs_router
from app.api.v1.companies import router as companies_router
from app.api.v1.company_pages import router as company_pages_router
from app.api.v1.company_enrichment import router as company_enrichment_router
from app.api.v1.crawler_runs import router as crawler_runs_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.discovery import router as discovery_router
from app.api.v1.discovery_job_ingestion import router as discovery_job_ingestion_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.profiles import router as profiles_router
from app.api.v1.tech_stack import router as tech_stack_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(agent_runs_router)
api_router.include_router(companies_router)
api_router.include_router(company_pages_router)
api_router.include_router(company_enrichment_router)
api_router.include_router(crawler_runs_router)
api_router.include_router(dashboard_router)
api_router.include_router(discovery_router)
api_router.include_router(discovery_job_ingestion_router)
api_router.include_router(jobs_router)
api_router.include_router(profiles_router)
api_router.include_router(tech_stack_router)
