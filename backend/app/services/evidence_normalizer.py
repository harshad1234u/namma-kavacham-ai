"""Turns raw rule/domain/provider/KB findings into one uniform evidence list."""

from app.schemas.analysis import EvidenceItem
from app.schemas.government_claim import GovernmentClaimResult, GovernmentClaimStatus
from app.schemas.threat_intelligence import ThreatIntelResult, ThreatIntelStatus
from app.services.message_rules import RuleHit
from app.services.url_analyzer import DomainCheckHit

_INTEL_TEXT = {
    ThreatIntelStatus.MALICIOUS: (
        "high",
        "{flagged} of {total} security vendors on VirusTotal flagged this link as malicious.",
        "VirusTotal-இல் {total} பாதுகாப்பு நிறுவனங்களில் {flagged} இந்த இணைப்பைத் தீங்கானது எனக் குறித்துள்ளன.",
    ),
    ThreatIntelStatus.SUSPICIOUS: (
        "medium",
        "{flagged} of {total} security vendors on VirusTotal flagged this link as suspicious.",
        "VirusTotal-இல் {total} பாதுகாப்பு நிறுவனங்களில் {flagged} இந்த இணைப்பைச் சந்தேகத்திற்குரியது எனக் குறித்துள்ளன.",
    ),
}


def from_rule_hits(hits: list[RuleHit]) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            signal=h.signal,
            category="message",
            source="deterministic_message_rules",
            confidence=h.confidence,
            rule_id=h.rule_id,
            description_en=h.description_en,
            description_ta=h.description_ta,
            observed=h.matched_text,
        )
        for h in hits
    ]


def from_domain_hits(hits_by_url: list[tuple[str, list[DomainCheckHit]]]) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for url, hits in hits_by_url:
        for h in hits:
            items.append(
                EvidenceItem(
                    signal=h.signal,
                    category="url",
                    source="deterministic_url_analysis",
                    kind=h.kind,
                    confidence=h.confidence,
                    rule_id=h.rule_id,
                    description_en=h.detail_en,
                    description_ta=h.detail_ta,
                    observed=url,
                )
            )
    return items


def from_threat_intel(result: ThreatIntelResult | None) -> list[EvidenceItem]:
    if result is None or not result.available or result.status not in _INTEL_TEXT:
        return []
    confidence, en, ta = _INTEL_TEXT[result.status]
    stats = result.engine_stats
    flagged = (stats.malicious if result.status == ThreatIntelStatus.MALICIOUS else stats.suspicious) if stats else 0
    total = result.engines_total or 0
    return [
        EvidenceItem(
            signal=f"threat_intel_{result.status.value}",
            category="threat_intelligence",
            source=result.provider,
            confidence=confidence,
            rule_id="TI-VT-01",
            description_en=en.format(flagged=flagged, total=total),
            description_ta=ta.format(flagged=flagged, total=total),
            observed=result.indicator,
        )
    ]


def from_government_claim(result: GovernmentClaimResult) -> list[EvidenceItem]:
    if result.claim_status != GovernmentClaimStatus.CONTRADICTED:
        return []
    return [
        EvidenceItem(
            signal="contradicted_by_curated_kb",
            category="government_claim",
            source="curated_government_kb",
            confidence="high",
            rule_id="KB-CONTRA-01",
            description_en=f.detail_en,
            description_ta=f.detail_ta,
        )
        for f in result.findings
        if f.outcome == "contradicted"
    ]


_ORDER = {"high": 0, "medium": 1, "low": 2}


def normalize_evidence(*groups: list[EvidenceItem]) -> list[EvidenceItem]:
    items = [item for group in groups for item in group]
    return sorted(items, key=lambda e: (e.kind != "risk", _ORDER[e.confidence]))
