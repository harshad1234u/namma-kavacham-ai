import json
from collections.abc import Callable, Iterator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.analyze import get_explainer, get_threat_intel_provider
from app.core.config import Settings, get_settings
from app.main import app
from app.schemas.threat_intelligence import ThreatIntelResult, ThreatIntelStatus
from app.services.threat_intelligence.base import STATUS_NOTES, STATUS_NOTES_TA, DisabledProvider
from app.schemas.threat_intelligence import UnavailableReason

SCAM_TNEB = (
    "Dear Customer, Your electricity power will be disconnected tonight at 9:30 PM due to unpaid bill "
    "of Rs480. Immediately pay or call electricity officer at 98765-43210 or download update app at "
    "http://tneb-billupdate.in/pay.apk"
)
SCAM_PMKISAN = (
    "URGENT: Your PM-Kisan 16th installment benefit of ₹5,000 is on hold. Pay ₹50 processing & "
    "verification charge immediately to release payment. Click http://pm-kisan-gov.in.payment-desk.cc/verify"
)
SCAM_AADHAAR_OTP = "Your Aadhaar will be suspended today. Share the OTP sent to your mobile to our officer to stop this."
BENIGN = "Hi Amma, I will reach home by 7. Please keep dinner ready."
ADVISORY = "Your bank will never ask for your PIN or OTP. Do not share your OTP with anyone."


def make_payload(body: str, source: str = "pasted_text", **extra) -> str:
    payload = {
        "schema_version": "1.0",
        "content": {"body": body, "source": source, "user_confirmed": True},
        "language_preference": "both",
        "privacy": {"upload_confirmed": True, "retention_preference": "delete_after_analysis"},
    }
    payload.update(extra)
    return json.dumps(payload)


class FakeProvider:
    name = "virustotal"

    def __init__(self, status: ThreatIntelStatus, malicious: int = 0, suspicious: int = 0):
        self.status = status
        self.malicious = malicious
        self.suspicious = suspicious
        self.calls: list[str] = []

    async def check_url(self, url: str) -> dict:
        self.calls.append(url)
        available = self.status != ThreatIntelStatus.UNAVAILABLE
        return ThreatIntelResult(
            provider=self.name,
            indicator=url,
            status=self.status,
            available=available,
            unavailable_reason=None if available else UnavailableReason.TIMEOUT,
            engine_stats={"malicious": self.malicious, "suspicious": self.suspicious, "harmless": 60, "undetected": 20}
            if available else None,
            engines_total=80 + self.malicious + self.suspicious if available else None,
            checked_at=datetime.now(timezone.utc),
            note=STATUS_NOTES[self.status],
            note_ta=STATUS_NOTES_TA[self.status],
        ).model_dump(mode="json")


def settings_for_test(**overrides) -> Settings:
    base = {"virustotal_enabled": False, "virustotal_api_key": "", "gemini_api_key": "", "groq_api_key": ""}
    base.update(overrides)
    return Settings(_env_file=None, **base)


@pytest.fixture
def make_client() -> Iterator[Callable[..., TestClient]]:
    def _make(provider=None, explainer=None, **settings_overrides) -> TestClient:
        settings = settings_for_test(**settings_overrides)
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_threat_intel_provider] = lambda: (
            provider or DisabledProvider("virustotal", UnavailableReason.DISABLED)
        )
        if explainer is not None:
            app.dependency_overrides[get_explainer] = lambda: explainer
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()
