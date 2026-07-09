import pytest

from app.enrichment.domain_validator import DomainValidator


@pytest.mark.asyncio
async def test_rejects_localhost():
    result = await DomainValidator().validate("http://localhost")

    assert result.valid is False
    assert result.reason in {"blocked_or_shared_domain", "unsafe_host"}


@pytest.mark.asyncio
async def test_rejects_loopback_ip():
    result = await DomainValidator().validate("http://127.0.0.1")

    assert result.valid is False
    assert result.reason == "unsafe_host"


@pytest.mark.asyncio
async def test_rejects_ipv6_loopback_ip():
    result = await DomainValidator().validate("http://[::1]")

    assert result.valid is False
    assert result.reason == "unsafe_host"
