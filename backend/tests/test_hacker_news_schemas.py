import pytest
from pydantic import ValidationError

from app.discovery.sources.hacker_news.schemas import HackerNewsDiscoveryRequest


def test_hacker_news_request_defaults():
    request = HackerNewsDiscoveryRequest()

    assert request.feeds == ["show", "jobs"]
    assert request.limit > 0
    assert request.lookback_days > 0
    assert request.include_items_without_website is True


def test_hacker_news_request_rejects_invalid_feed():
    with pytest.raises(ValidationError):
        HackerNewsDiscoveryRequest(feeds=["show", "bad-feed"])


def test_hacker_news_request_rejects_invalid_limit():
    with pytest.raises(ValidationError):
        HackerNewsDiscoveryRequest(limit=0)
