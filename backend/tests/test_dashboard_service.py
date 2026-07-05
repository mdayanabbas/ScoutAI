from datetime import datetime, timedelta, timezone

from app.schemas.dashboard import DashboardResponse, DashboardSummary
from app.services.agent_run_service import AgentRunService
from app.services.company_service import CompanyService
from app.services.crawl_run_service import CrawlRunService
from app.services.dashboard_service import DashboardService
from app.services.job_service import JobService
from app.utils.enums import AgentRunStatus, CrawlStatus, JobStatus, RemoteType


def test_dashboard_schemas_importable():
    assert DashboardSummary
    assert DashboardResponse


def test_dashboard_summary_counts_backend_records(db_session):
    company = CompanyService(db_session).create_company(
        {"name": "Dash Co", "website_url": "https://dash.example"}
    )
    JobService(db_session).create_or_update_job(
        company.id,
        {
            "title": "Remote AI Engineer",
            "job_url": "https://dash.example/jobs/ai",
            "status": JobStatus.ACTIVE,
            "remote_type": RemoteType.REMOTE_WORLDWIDE,
        },
    )
    crawl_service = CrawlRunService(db_session)
    successful_crawl = crawl_service.create_crawl_run(company.id)
    failed_crawl = crawl_service.create_crawl_run(company.id)
    crawl_service.mark_success(successful_crawl.id)
    crawl_service.mark_failed(failed_crawl.id, "failed")
    agent_service = AgentRunService(db_session)
    successful_agent = agent_service.create_agent_run(
        {"company_id": company.id, "agent_name": "company_research"}
    )
    failed_agent = agent_service.create_agent_run(
        {"company_id": company.id, "agent_name": "job_understanding"}
    )
    agent_service.mark_success(successful_agent.id)
    agent_service.mark_failed(failed_agent.id, "failed")

    summary = DashboardService(db_session).get_summary()

    assert summary.total_companies == 1
    assert summary.total_jobs == 1
    assert summary.active_jobs == 1
    assert summary.remote_jobs == 1
    assert summary.companies_added_today == 1
    assert summary.jobs_added_today == 1
    assert summary.recent_crawl_runs == 2
    assert summary.successful_crawl_runs == 1
    assert summary.failed_crawl_runs == 1
    assert summary.recent_agent_runs == 2
    assert summary.successful_agent_runs == 1
    assert summary.failed_agent_runs == 1


def test_dashboard_recent_activity_is_sorted_newest_first(db_session):
    older = CompanyService(db_session).create_company(
        {"name": "Older Co", "website_url": "https://older.example"}
    )
    newer = CompanyService(db_session).create_company(
        {"name": "Newer Co", "website_url": "https://newer.example"}
    )
    older.created_at = datetime.now(timezone.utc) - timedelta(days=1)
    newer.created_at = datetime.now(timezone.utc)
    db_session.commit()

    activity = DashboardService(db_session).get_recent_activity(limit=2)

    assert [item.entity_id for item in activity] == [newer.id, older.id]
    assert activity[0].type == "company_created"
