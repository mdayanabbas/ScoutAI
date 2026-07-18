from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.remote_discovery import (
    RemoteDiscoverySourceResult,
    RemoteJobDiscoveryOrchestratorResult,
    RemoteJobDiscoveryRunRequest,
)


def test_run_request_normalizes_and_validates_sources():
    request = RemoteJobDiscoveryRunRequest(
        sources=["Remotive", "remotive", "himalayas", "hacker_news", "ycombinator", "ashby"]
    )

    assert request.sources == ["remotive", "himalayas", "hacker_news", "ycombinator", "ashby"]

    with pytest.raises(ValidationError):
        RemoteJobDiscoveryRunRequest(sources=["linkedin"])


def test_run_request_rejects_arbitrary_inputs_and_caps_provider_options():
    with pytest.raises(ValidationError):
        RemoteJobDiscoveryRunRequest(profile_id="profile-1")

    with pytest.raises(ValidationError):
        RemoteJobDiscoveryRunRequest(himalayas={"max_queries": 51})

    with pytest.raises(ValidationError):
        RemoteJobDiscoveryRunRequest(we_work_remotely={"rss_url": "https://evil.example/jobs.rss"})

    with pytest.raises(ValidationError):
        RemoteJobDiscoveryRunRequest(remotive={"limit_per_request": 501})

    with pytest.raises(ValidationError):
        RemoteJobDiscoveryRunRequest(hacker_news={"limit": 501})

    with pytest.raises(ValidationError):
        RemoteJobDiscoveryRunRequest(ycombinator={"max_pages": 26})

    with pytest.raises(ValidationError):
        RemoteJobDiscoveryRunRequest(ashby={"max_jobs_per_board": 201})


def test_new_unified_source_options_default_to_credit_conscious_pipeline():
    request = RemoteJobDiscoveryRunRequest(
        sources=["hacker_news", "ycombinator", "ashby"],
        hacker_news={},
        ycombinator={},
        ashby={},
    )

    assert request.hacker_news is not None
    assert request.hacker_news.feeds == ["jobs"]
    assert request.hacker_news.limit == 100
    assert request.hacker_news.lookback_days == 30
    assert request.hacker_news.enrich_domains is True
    assert request.hacker_news.ingest_jobs is True
    assert request.hacker_news.enrich_jobs is True
    assert request.hacker_news.score_jobs is True
    assert request.ycombinator is not None
    assert request.ycombinator.max_pages == 5
    assert request.ycombinator.remote_only is False
    assert request.ashby is not None
    assert request.ashby.board_slugs == []
    assert request.ashby.max_jobs_per_board == 50


def test_source_result_and_orchestrator_result_shape_is_stable():
    now = datetime.now(timezone.utc)
    source = RemoteDiscoverySourceResult(
        source="remotive",
        status="succeeded",
        started_at=now,
        finished_at=now,
        duration_ms=0,
    )
    result = RemoteJobDiscoveryOrchestratorResult(
        status="succeeded",
        profile_id="profile-1",
        sources_planned=["remotive"],
        source_results=[source],
        started_at=now,
        finished_at=now,
        duration_ms=0,
    )

    dumped = result.model_dump()
    assert dumped["source_results"][0]["provider_records_seen"] == 0
    assert dumped["source_results"][0]["candidates_found"] == 0
    assert dumped["source_results"][0]["diagnostics"] == {}
    assert dumped["top_recommendations"] == []
    assert "description" not in result.model_dump_json()
    assert "raw_payload" not in result.model_dump_json()
