from fastapi import APIRouter

from app.api.v1.agent_runs import router as agent_runs_router
from app.api.v1.application_prep import router as application_prep_router
from app.api.v1.application_packets import router as application_packets_router
from app.api.v1.companies import router as companies_router
from app.api.v1.company_pages import router as company_pages_router
from app.api.v1.company_enrichment import router as company_enrichment_router
from app.api.v1.crawler_runs import router as crawler_runs_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.discovery import router as discovery_router
from app.api.v1.discovery_job_ingestion import router as discovery_job_ingestion_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.job_application_decisions import router as job_application_decisions_router
from app.api.v1.job_matches import router as job_matches_router
from app.api.v1.profiles import router as profiles_router
from app.api.v1.resumes import router as resumes_router
from app.api.v1.resume_improvements import router as resume_improvements_router
from app.api.v1.tech_stack import router as tech_stack_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(agent_runs_router)
api_router.include_router(application_prep_router)
api_router.include_router(application_packets_router)
api_router.include_router(companies_router)
api_router.include_router(company_pages_router)
api_router.include_router(company_enrichment_router)
api_router.include_router(crawler_runs_router)
api_router.include_router(dashboard_router)
api_router.include_router(discovery_router)
api_router.include_router(discovery_job_ingestion_router)
api_router.include_router(jobs_router)
api_router.include_router(job_application_decisions_router)
api_router.include_router(job_matches_router)
api_router.include_router(profiles_router)
api_router.include_router(resumes_router)
api_router.include_router(resume_improvements_router)
api_router.include_router(tech_stack_router)
