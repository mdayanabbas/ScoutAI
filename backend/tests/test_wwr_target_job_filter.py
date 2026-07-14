from datetime import datetime, timedelta, timezone

from app.discovery.sources.we_work_remotely.filter import WWRTargetJobFilter
from app.discovery.sources.we_work_remotely.models import WWRFeedItem


def _item(
    title="Junior AI Engineer",
    text="Anywhere in the World. Full-Time. Build LLM systems with Python. 1+ years experience.",
    company="Remote AI Co",
    published_at=None,
):
    return WWRFeedItem(
        guid="wwr-1",
        title=f"{company}: {title}" if company else title,
        link="https://weworkremotely.com/remote-jobs/remote-ai-junior-ai-engineer",
        published_at=published_at or datetime(2026, 7, 14, tzinfo=timezone.utc),
        description_html=text,
        description_text=text,
        company_name=company,
        role_title=title,
        employment_type="full_time",
        source_feed="programming",
    )


def test_filter_accepts_target_worldwide_entry_level_roles():
    result = WWRTargetJobFilter().evaluate(
        _item(),
        now=datetime(2026, 7, 14, tzinfo=timezone.utc),
    )

    assert result.accepted is True
    assert result.role_category == "ai_engineer"
    assert result.remote_eligibility == "work_from_anywhere"
    assert result.remote_type == "remote_worldwide"
    assert result.experience_min == 1


def test_filter_rejects_non_target_senior_restricted_hybrid_and_stale_roles():
    filter_ = WWRTargetJobFilter()
    now = datetime(2026, 7, 14, tzinfo=timezone.utc)

    assert filter_.evaluate(_item("Product Manager"), now=now).rejection_reason == "rejected_role"
    assert filter_.evaluate(_item("Senior AI Engineer"), now=now).rejection_reason == "rejected_seniority"
    assert filter_.evaluate(_item(text="Remote US only. AI systems."), now=now).rejection_reason == "rejected_country_restriction"
    assert filter_.evaluate(_item(text="Hybrid in Berlin. AI systems."), now=now).rejection_reason == "rejected_hybrid"
    assert filter_.evaluate(
        _item(published_at=now - timedelta(days=60)),
        max_age_days=45,
        now=now,
    ).rejection_reason == "rejected_stale_listing"


def test_filter_does_not_treat_senior_mentions_as_senior_title():
    result = WWRTargetJobFilter().evaluate(
        _item(text="Remote worldwide. Work with senior engineers. 2 years experience."),
        now=datetime(2026, 7, 14, tzinfo=timezone.utc),
    )

    assert result.accepted is True
    assert result.seniority is None
