"""VirusTotal v3 URL-report lookup.

Lookup only: URLs are never submitted for a fresh scan (PRD: no unreviewed
automatic submissions). Only the extracted URL is sent — never the message.
"""

import base64
import hashlib
import time
from datetime import datetime, timezone

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.threat_intelligence import (
    EngineStats,
    ThreatIntelResult,
    ThreatIntelStatus,
    UnavailableReason,
)
from app.services.threat_intelligence.base import (
    STATUS_NOTES,
    STATUS_NOTES_TA,
    DisabledProvider,
    ThreatIntelProvider,
    unavailable_result,
)

log = get_logger("virustotal")

VT_URL_REPORT = "https://www.virustotal.com/api/v3/urls/{url_id}"
PROVIDER_NAME = "virustotal"
CACHE_TTL_SECONDS = 3600
CACHE_MAX_ENTRIES = 512


def url_id(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")


def cache_key(normalized_url: str) -> str:
    return hashlib.sha256(normalized_url.encode()).hexdigest()


class _ResultCache:
    """In-process cache keyed by sha256(normalized_url); stores provider results only, never message text."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[float, dict]] = {}

    def get(self, key: str) -> dict | None:
        item = self._items.get(key)
        if not item:
            return None
        stored_at, value = item
        if time.monotonic() - stored_at > CACHE_TTL_SECONDS:
            self._items.pop(key, None)
            return None
        return {**value, "from_cache": True}

    def put(self, key: str, value: dict) -> None:
        if len(self._items) >= CACHE_MAX_ENTRIES:
            self._items.pop(next(iter(self._items)))
        self._items[key] = (time.monotonic(), value)

    def clear(self) -> None:
        self._items.clear()


class VirusTotalProvider:
    name = PROVIDER_NAME

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 6.0,
        transport: httpx.AsyncBaseTransport | None = None,
        cache: _ResultCache | None = None,
    ):
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._transport = transport
        self._cache = cache if cache is not None else _ResultCache()

    async def check_url(self, url: str) -> dict:
        key = cache_key(url)
        if cached := self._cache.get(key):
            return cached

        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                response = await client.get(
                    VT_URL_REPORT.format(url_id=url_id(url)),
                    headers={"x-apikey": self._api_key, "accept": "application/json"},
                )
        except httpx.TimeoutException:
            log.warning("virustotal_lookup_failed", extra={"reason": "timeout"})
            return unavailable_result(self.name, url, UnavailableReason.TIMEOUT)
        except httpx.HTTPError as exc:
            log.warning("virustotal_lookup_failed", extra={"reason": "network_error", "exc_type": type(exc).__name__})
            return unavailable_result(self.name, url, UnavailableReason.NETWORK_ERROR)

        elapsed_ms = int((time.monotonic() - started) * 1000)
        log.info("virustotal_lookup", extra={"http_status": response.status_code, "elapsed_ms": elapsed_ms})

        if response.status_code == 404:
            result = self._result(url, ThreatIntelStatus.NOT_FOUND)
            self._cache.put(key, result)
            return result
        if response.status_code in (401, 403):
            return unavailable_result(self.name, url, UnavailableReason.AUTH_ERROR)
        if response.status_code == 429:
            return unavailable_result(self.name, url, UnavailableReason.QUOTA_EXCEEDED)
        if response.status_code != 200:
            return unavailable_result(self.name, url, UnavailableReason.PROVIDER_ERROR)

        try:
            attributes = response.json()["data"]["attributes"]
            stats = EngineStats(**{k: int(v) for k, v in attributes["last_analysis_stats"].items()
                                   if k in EngineStats.model_fields})
        except (ValueError, KeyError, TypeError):
            return unavailable_result(self.name, url, UnavailableReason.INVALID_RESPONSE)

        if stats.malicious > 0:
            status = ThreatIntelStatus.MALICIOUS
        elif stats.suspicious > 0:
            status = ThreatIntelStatus.SUSPICIOUS
        elif stats.total == 0:
            status = ThreatIntelStatus.UNKNOWN
        else:
            status = ThreatIntelStatus.CLEAN_OR_HARMLESS

        last_analysis = attributes.get("last_analysis_date")
        categories = attributes.get("categories") or {}
        result = self._result(
            url,
            status,
            engine_stats=stats,
            engines_total=stats.total,
            categories=sorted({str(c) for c in categories.values()})[:6] if isinstance(categories, dict) else [],
            source_timestamp=datetime.fromtimestamp(last_analysis, tz=timezone.utc)
            if isinstance(last_analysis, (int, float)) else None,
        )
        self._cache.put(key, result)
        return result

    def _result(self, url: str, status: ThreatIntelStatus, **fields) -> dict:
        return ThreatIntelResult(
            provider=self.name,
            indicator=url,
            status=status,
            available=True,
            checked_at=datetime.now(timezone.utc),
            note=STATUS_NOTES[status],
            note_ta=STATUS_NOTES_TA[status],
            **fields,
        ).model_dump(mode="json")


_shared_cache = _ResultCache()


def build_provider(settings: Settings) -> ThreatIntelProvider:
    if not settings.virustotal_enabled:
        return DisabledProvider(PROVIDER_NAME, UnavailableReason.DISABLED)
    key = settings.virustotal_api_key.get_secret_value()
    if not key:
        return DisabledProvider(PROVIDER_NAME, UnavailableReason.NOT_CONFIGURED)
    return VirusTotalProvider(key, settings.virustotal_timeout_seconds, cache=_shared_cache)
