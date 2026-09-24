from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ThreatIntelStatus(str, Enum):
    MALICIOUS = "malicious"
    SUSPICIOUS = "suspicious"
    NOT_FOUND = "not_found"
    CLEAN_OR_HARMLESS = "clean_or_harmless"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class UnavailableReason(str, Enum):
    DISABLED = "disabled_by_configuration"
    NOT_CONFIGURED = "api_key_not_configured"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    AUTH_ERROR = "authentication_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    PROVIDER_ERROR = "provider_error"
    INVALID_RESPONSE = "invalid_response"


class EngineStats(BaseModel):
    malicious: int = 0
    suspicious: int = 0
    harmless: int = 0
    undetected: int = 0
    timeout: int = 0

    @property
    def total(self) -> int:
        return self.malicious + self.suspicious + self.harmless + self.undetected + self.timeout


class ThreatIntelResult(BaseModel):
    provider: str
    indicator_type: str = "url"
    indicator: str
    status: ThreatIntelStatus
    available: bool
    unavailable_reason: UnavailableReason | None = None
    engine_stats: EngineStats | None = None
    engines_total: int | None = Field(default=None, description="Engines that reported on this indicator")
    categories: list[str] = Field(default_factory=list)
    source_timestamp: datetime | None = Field(
        default=None, description="Provider's last-analysis time, only when the provider supplied it"
    )
    checked_at: datetime
    from_cache: bool = False
    note: str = Field(
        description="Plain-language meaning of this status. `not_found` and `unavailable` never mean safe."
    )
    note_ta: str | None = None
