from datetime import datetime, timedelta, timezone

from app.discovery.sources.remotive.filter import RemotiveTargetJobFilter
from app.discovery.sources.remotive.parser import ParsedRemotiveJob


def _job(title="AI Engineer", location="Worldwide", description="Remote role. 2 years experience.", company="Remote AI Co"):
    return ParsedRemotiveJob(
        source_item_id="1",
        title=title,
        normalized_title=title.lower(),
        company_name=company,
        description=description,
        excerpt=description[:100],
        source_url="https://remotive.com/remote-jobs/software-dev/ai-engineer-123",
        category="software-dev",
        role_category=None,
        role_match_type=None,
        remote_eligibility=None,
        remote_type=None,
        seniority=None,
        employment_type="full_time",
        experience_min=None,
        experience_max=None,
        salary_min=None,
        salary_max=None,
        salary_currency=None,
        salary_text=None,
        published_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
        location=location,
    )


def test_role_filter_accepts_targets_and_adjacent_roles():
    accepted = [
        ("AI Engineer", "ai_engineer"),
        ("Applied AI Engineer", "ai_engineer"),
        ("LLM Engineer", "ai_engineer"),
        ("Machine Learning Engineer", "ml_engineer"),
        ("ML Engineer", "ml_engineer"),
        ("Forward Deployed Engineer", "forward_deployed_engineer"),
        ("FDE", "forward_deployed_engineer"),
        ("SWE", "software_engineer"),
        ("SDE", "software_engineer"),
        ("Software Engineer", "software_engineer"),
        ("Backend Engineer", "backend_engineer"),
        ("Full Stack Engineer", "full_stack_engineer"),
    ]

    for title, category in accepted:
        result = RemotiveTargetJobFilter().evaluate(_job(title=title))
        assert result.accepted is True, title
        assert result.role_category == category


def test_role_filter_rejects_unrelated_roles_and_plain_solutions_engineer():
    for title in ["Electrical Engineer", "Robotics Engineer", "QA Engineer", "Sales Engineer", "Account Executive", "Developer Advocate", "Solutions Engineer"]:
        result = RemotiveTargetJobFilter().evaluate(_job(title=title))
        assert result.accepted is False, title
        assert result.rejection_reason == "rejected_role"


def test_seniority_and_experience_rules():
    filter_ = RemotiveTargetJobFilter()

    assert filter_.evaluate(_job("Intern AI Engineer")).accepted is True
    assert filter_.evaluate(_job("Junior AI Engineer")).accepted is True
    assert filter_.evaluate(_job("Associate AI Engineer")).accepted is True
    assert filter_.evaluate(_job(description="Work with senior engineers. 2 years experience.")).accepted is True
    assert filter_.evaluate(_job(description="3 years experience.")).accepted is True
    assert filter_.evaluate(_job(description="4 years experience.")).rejection_reason == "rejected_experience"
    assert filter_.evaluate(_job(description="5 years experience.")).rejection_reason == "rejected_seniority"
    for title in ["Senior AI Engineer", "Staff AI Engineer", "Principal AI Engineer", "Lead AI Engineer", "Engineering Manager"]:
        assert filter_.evaluate(_job(title=title)).rejection_reason == "rejected_seniority"


def test_remote_rules_and_stale_listings():
    filter_ = RemotiveTargetJobFilter()
    assert filter_.evaluate(_job(location="Worldwide")).remote_eligibility == "work_from_anywhere"
    assert filter_.evaluate(_job(location="Anywhere in the World")).remote_eligibility == "work_from_anywhere"
    assert filter_.evaluate(_job(location="India and Singapore")).remote_eligibility == "remote_india_eligible"
    assert filter_.evaluate(_job(location="APAC")).remote_eligibility == "remote_india_eligible"
    assert filter_.evaluate(_job(location="Remote")).remote_eligibility == "remote_eligibility_unclear"
    assert filter_.evaluate(_job(location=None)).remote_eligibility == "remote_eligibility_unclear"
    for location in ["US Only", "Canada Only", "Europe Only", "UK Only", "EMEA", "LATAM", "Worldwide excluding India"]:
        assert filter_.evaluate(_job(location=location)).rejection_reason == "rejected_country_restriction"
    assert filter_.evaluate(_job(description="Hybrid in Berlin")).rejection_reason == "rejected_hybrid"
    assert filter_.evaluate(_job(description="Onsite in Berlin")).rejection_reason == "rejected_onsite"
    stale = _job()
    stale = ParsedRemotiveJob(**{**stale.__dict__, "published_at": datetime.now(timezone.utc) - timedelta(days=90)})
    assert filter_.evaluate(stale, max_age_days=45).rejection_reason == "rejected_stale_listing"
