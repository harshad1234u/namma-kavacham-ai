import httpx
import pytest

from app.schemas.threat_intelligence import ThreatIntelStatus, UnavailableReason
from app.services.threat_intelligence.base import DisabledProvider
from app.services.threat_intelligence.virustotal import (
    VirusTotalProvider,
    _ResultCache,
    build_provider,
    cache_key,
    url_id,
)
from app.tests.conftest import settings_for_test

URL = "http://pm-kisan-gov.in/verify"


def vt_body(malicious=0, suspicious=0, harmless=60, undetected=20):
    return {
        "data": {
            "attributes": {
                "last_analysis_stats": {
                    "malicious": malicious, "suspicious": suspicious, "harmless": harmless,
                    "undetected": undetected, "timeout": 0,
                },
                "last_analysis_date": 1_758_000_000,
                "categories": {"Forcepoint ThreatSeeker": "phishing"},
            }
        }
    }


def provider_with(handler) -> tuple[VirusTotalProvider, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    return VirusTotalProvider("test-key", transport=httpx.MockTransport(_handler), cache=_ResultCache()), seen


async def test_malicious_mapping_and_request_shape():
    provider, seen = provider_with(lambda r: httpx.Response(200, json=vt_body(malicious=4)))
    result = await provider.check_url(URL)
    assert result["status"] == "malicious"
    assert result["available"] is True
    assert result["engine_stats"]["malicious"] == 4
    assert result["categories"] == ["phishing"]
    assert seen[0].url.path.endswith(url_id(URL))
    assert seen[0].headers["x-apikey"] == "test-key"
    assert seen[0].method == "GET"  # lookup only, never a submission


async def test_suspicious_mapping():
    provider, _ = provider_with(lambda r: httpx.Response(200, json=vt_body(suspicious=2)))
    assert (await provider.check_url(URL))["status"] == "suspicious"


async def test_clean_mapping_is_not_called_safe():
    provider, _ = provider_with(lambda r: httpx.Response(200, json=vt_body()))
    result = await provider.check_url(URL)
    assert result["status"] == "clean_or_harmless"
    assert "does not prove the link is safe" in result["note"]


async def test_404_is_not_found_not_clean():
    provider, _ = provider_with(lambda r: httpx.Response(404, json={"error": {"code": "NotFoundError"}}))
    result = await provider.check_url(URL)
    assert result["status"] == "not_found"
    assert result["available"] is True
    assert "does not mean the link is safe" in result["note"]


@pytest.mark.parametrize(
    "status_code,reason",
    [(401, UnavailableReason.AUTH_ERROR), (403, UnavailableReason.AUTH_ERROR),
     (429, UnavailableReason.QUOTA_EXCEEDED), (503, UnavailableReason.PROVIDER_ERROR)],
)
async def test_error_statuses_are_unavailable(status_code, reason):
    provider, _ = provider_with(lambda r: httpx.Response(status_code))
    result = await provider.check_url(URL)
    assert result["status"] == "unavailable"
    assert result["available"] is False
    assert result["unavailable_reason"] == reason.value


async def test_timeout_is_unavailable():
    def boom(request):
        raise httpx.ReadTimeout("slow", request=request)

    provider, _ = provider_with(boom)
    result = await provider.check_url(URL)
    assert result["status"] == "unavailable"
    assert result["unavailable_reason"] == "timeout"


async def test_malformed_body_is_unavailable():
    provider, _ = provider_with(lambda r: httpx.Response(200, json={"unexpected": True}))
    assert (await provider.check_url(URL))["unavailable_reason"] == "invalid_response"


async def test_results_are_cached_by_url_hash_but_failures_are_not():
    provider, seen = provider_with(lambda r: httpx.Response(200, json=vt_body(malicious=1)))
    await provider.check_url(URL)
    second = await provider.check_url(URL)
    assert len(seen) == 1 and second["from_cache"] is True

    failing, seen_fail = provider_with(lambda r: httpx.Response(503))
    await failing.check_url(URL)
    await failing.check_url(URL)
    assert len(seen_fail) == 2


def test_cache_key_is_sha256_of_url():
    assert len(cache_key(URL)) == 64 and URL not in cache_key(URL)


async def test_disabled_flag_builds_disabled_provider_without_network():
    provider = build_provider(settings_for_test(virustotal_enabled=False, virustotal_api_key="k"))
    assert isinstance(provider, DisabledProvider)
    result = await provider.check_url(URL)
    assert result["status"] == ThreatIntelStatus.UNAVAILABLE.value
    assert result["unavailable_reason"] == "disabled_by_configuration"


def test_enabled_without_key_is_not_configured():
    provider = build_provider(settings_for_test(virustotal_enabled=True, virustotal_api_key=""))
    assert isinstance(provider, DisabledProvider)
