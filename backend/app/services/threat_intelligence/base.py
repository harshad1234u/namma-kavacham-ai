from datetime import datetime, timezone
from typing import Protocol

from app.schemas.threat_intelligence import ThreatIntelResult, ThreatIntelStatus, UnavailableReason

STATUS_NOTES = {
    ThreatIntelStatus.MALICIOUS: "Security vendors flagged this link as malicious.",
    ThreatIntelStatus.SUSPICIOUS: "Security vendors flagged this link as suspicious.",
    ThreatIntelStatus.CLEAN_OR_HARMLESS: (
        "No vendor flagged this link in its last analysis. This does not prove the link is safe; "
        "new scam sites are often not yet detected."
    ),
    ThreatIntelStatus.NOT_FOUND: (
        "The provider has no report for this link. No report means it was not checked before — "
        "it does not mean the link is safe."
    ),
    ThreatIntelStatus.UNAVAILABLE: (
        "The threat-intelligence check could not be completed. The link was not checked, so this "
        "must not be read as safe."
    ),
    ThreatIntelStatus.UNKNOWN: "The provider returned a result that could not be interpreted.",
}


STATUS_NOTES_TA = {
    ThreatIntelStatus.MALICIOUS: "பாதுகாப்பு நிறுவனங்கள் இந்த இணைப்பைத் தீங்கானது எனக் குறித்துள்ளன.",
    ThreatIntelStatus.SUSPICIOUS: "பாதுகாப்பு நிறுவனங்கள் இந்த இணைப்பைச் சந்தேகத்திற்குரியது எனக் குறித்துள்ளன.",
    ThreatIntelStatus.CLEAN_OR_HARMLESS: (
        "கடைசி பகுப்பாய்வில் எந்த நிறுவனமும் இந்த இணைப்பைக் குறிக்கவில்லை. இது இணைப்பு பாதுகாப்பானது என்பதை நிரூபிக்காது; "
        "புதிய மோசடித் தளங்கள் பெரும்பாலும் இன்னும் கண்டறியப்பட்டிருக்காது."
    ),
    ThreatIntelStatus.NOT_FOUND: (
        "இந்த இணைப்புக்கு வழங்குநரிடம் அறிக்கை இல்லை. அறிக்கை இல்லை என்றால் இது முன்பு சரிபார்க்கப்படவில்லை என்று "
        "அர்த்தம் — இணைப்பு பாதுகாப்பானது என்று அல்ல."
    ),
    ThreatIntelStatus.UNAVAILABLE: (
        "அச்சுறுத்தல் தகவல் சோதனையை முடிக்க முடியவில்லை. இணைப்பு சரிபார்க்கப்படவில்லை, எனவே இதைப் பாதுகாப்பானது "
        "என்று கருதக்கூடாது."
    ),
    ThreatIntelStatus.UNKNOWN: "வழங்குநர் அளித்த முடிவைப் புரிந்துகொள்ள முடியவில்லை.",
}


class ThreatIntelProvider(Protocol):
    name: str

    async def check_url(self, url: str) -> dict: ...


def unavailable_result(provider: str, url: str, reason: UnavailableReason) -> dict:
    return ThreatIntelResult(
        provider=provider,
        indicator=url,
        status=ThreatIntelStatus.UNAVAILABLE,
        available=False,
        unavailable_reason=reason,
        checked_at=datetime.now(timezone.utc),
        note=STATUS_NOTES[ThreatIntelStatus.UNAVAILABLE],
        note_ta=STATUS_NOTES_TA[ThreatIntelStatus.UNAVAILABLE],
    ).model_dump(mode="json")


class DisabledProvider:
    """Stands in when the provider is switched off or has no key, so callers never branch on None."""

    def __init__(self, name: str, reason: UnavailableReason):
        self.name = name
        self._reason = reason

    async def check_url(self, url: str) -> dict:
        return unavailable_result(self.name, url, self._reason)
