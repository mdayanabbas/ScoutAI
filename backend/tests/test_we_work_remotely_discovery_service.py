from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.discovery.sources.we_work_remotely.models import WWRFeedDefinition, WWRFeedResponse
from app.models.job_matching_profile import JobMatchingProfile
from app.models.user_profile import UserProfile
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import UserProfileRepository
from app.services.we_work_remotely_discovery_service import WeWorkRemotelyDiscoveryService


RSS = b"""<?xml version="1.0"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Remote Programming Jobs</title>
    <link>https://weworkremotely.com/categories/remote-programming-jobs</link>
    <description>Remote jobs</description>
    <lastBuildDate>Tue, 14 Jul 2026 10:00:00 GMT</lastBuildDate>
    <language>en</language>
    <item>
      <guid>wwr-ai-1</guid>
      <title>Remote AI Co: Junior AI Engineer</title>
      <link>https://weworkremotely.com/remote-jobs/remote-ai-junior-ai-engineer?utm_source=rss</link>
      <pubDate>Tue, 14 Jul 2026 09:00:00 GMT</pubDate>
      <category>Programming</category>
      <content:encoded><![CDATA[
        <p>Anywhere in the World</p>
        <p>Full-Time</p>
        <p>Build production AI systems with Python. 1+ years experience.</p>
      ]]></content:encoded>
    </item>
    <item>
      <guid>wwr-ai-1</guid>
      <title>Remote AI Co: Junior AI Engineer</title>
      <link>https://weworkremotely.com/remote-jobs/remote-ai-junior-ai-engineer</link>
      <pubDate>Tue, 14 Jul 2026 09:00:00 GMT</pubDate>
      <description>Anywhere in the World. Full-Time. Build production AI systems.</description>
    </item>
    <item>
      <guid>wwr-pm-1</guid>
      <title>Remote PM Co: Product Manager</title>
      <link>https://weworkremotely.com/remote-jobs/remote-pm-product-manager</link>
      <pubDate>Tue, 14 Jul 2026 09:00:00 GMT</pubDate>
      <description>Anywhere in the World.</description>
    </item>
  </channel>
</rss>"""


class FakeWWRClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def fetch_feed(self, feed: WWRFeedDefinition, **kwargs):
        self.calls.append((feed, kwargs))
        return self.responses.pop(0)


def _settings(**overrides):
    values = {
        "WWR_DISCOVERY_ENABLED": True,
        "WWR_PROGRAMMING_RSS_URL": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "WWR_ALL_OTHER_RSS_URL": "https://weworkremotely.com/categories/all-other-remote-jobs.rss",
        "WWR_INCLUDE_ALL_OTHER_FEED": False,
        "WWR_REQUEST_TIMEOUT_SECONDS": 15,
        "WWR_MAX_RETRIES": 1,
        "WWR_MAX_RESPONSE_BYTES": 5_000_000,
        "WWR_DISCOVERY_COOLDOWN_HOURS": 6,
        "WWR_MAX_ITEMS_PER_FEED": 200,
        "WWR_MAX_JOBS_PER_RUN": 100,
        "WWR_SCORE_AFTER_INGESTION": False,
        "WWR_STORE_REJECTED_CANDIDATES": True,
        "WWR_USE_CONDITIONAL_REQUESTS": True,
        "WWR_MAX_JOB_AGE_DAYS": 45,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _profile(db_session):
    user = UserProfileRepository(db_session).create_profile(UserProfile(display_name="Abbas"))
    profile = JobMatchingProfile(
        user_profile_id=user.id,
        target_titles_json=["AI Engineer"],
        target_role_categories_json=["ai_engineer"],
        accepted_employment_types_json=["full_time", "contract"],
        preferred_countries_json=["India"],
        work_authorization_countries_json=["India"],
        willing_to_relocate=False,
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


def _response(body=RSS, *, not_modified=False):
    feed = WWRFeedDefinition("Remote Programming Jobs", "programming", "https://weworkremotely.com/categories/remote-programming-jobs.rss")
    return WWRFeedResponse(
        success=True,
        feed=feed,
        body=None if not_modified else body,
        status_code=304 if not_modified else 200,
        reason="not_modified" if not_modified else None,
        not_modified=not_modified,
    )


@pytest.mark.asyncio
async def test_service_creates_run_company_job_rejection_and_deduplicates(db_session, monkeypatch):
    profile = _profile(db_session)
    monkeypatch.setattr("app.services.we_work_remotely_discovery_service.get_settings", lambda: _settings(WWR_DISCOVERY_COOLDOWN_HOURS=0))

    result = await WeWorkRemotelyDiscoveryService(db_session, client=FakeWWRClient([_response()])).run_discovery(
        force=True,
        score_after_ingestion=False,
    )

    assert result.status == "succeeded"
    assert result.profile_id == profile.id
    assert result.unique_items == 2
    assert result.candidates_created == 2
    assert result.candidates_rejected == 1
    assert result.jobs_created == 1
    assert result.accepted_jobs[0].company_name == "Remote AI Co"
    assert result.accepted_jobs[0].attribution_label == "We Work Remotely"
    assert result.rejected_samples[0].rejection_reason == "rejected_role"
    assert len(JobRepository(db_session).list_jobs()) == 1


@pytest.mark.asyncio
async def test_service_handles_not_modified_feed_as_success(db_session, monkeypatch):
    _profile(db_session)
    monkeypatch.setattr("app.services.we_work_remotely_discovery_service.get_settings", lambda: _settings(WWR_DISCOVERY_COOLDOWN_HOURS=0))

    result = await WeWorkRemotelyDiscoveryService(db_session, client=FakeWWRClient([_response(not_modified=True)])).run_discovery(force=True)

    assert result.status == "succeeded"
    assert result.feeds_not_modified == 1
    assert result.feed_results[0].status == "not_modified"
    assert result.jobs_created == 0


@pytest.mark.asyncio
async def test_service_cooldown_skips_without_fetching(db_session, monkeypatch):
    _profile(db_session)
    monkeypatch.setattr("app.services.we_work_remotely_discovery_service.get_settings", lambda: _settings(WWR_DISCOVERY_COOLDOWN_HOURS=24))
    client = FakeWWRClient([_response()])
    service = WeWorkRemotelyDiscoveryService(db_session, client=client)

    first = await service.run_discovery(force=True, score_after_ingestion=False)
    second = await service.run_discovery(force=False, score_after_ingestion=False)

    assert first.status == "succeeded"
    assert second.status == "skipped"
    assert second.reason == "wwr_discovery_cooldown_active"
    assert len(client.calls) == 1
