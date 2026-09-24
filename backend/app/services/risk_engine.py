"""Deterministic risk aggregation — the authoritative verdict.

Points are an explainability aid ("indicator strength"), not a probability.
Missing or unavailable external checks contribute zero: they never raise the
level and, critically, never lower it or imply safety.
"""

from dataclasses import dataclass, field

from app.schemas.government_claim import GovernmentClaimResult, GovernmentClaimStatus
from app.schemas.threat_intelligence import ThreatIntelResult, ThreatIntelStatus
from app.services.message_rules import RuleHit
from app.services.url_analyzer import DomainCheckHit

MESSAGE_POINTS = {"high": 30, "medium": 18, "low": 8}
DOMAIN_POINTS = {"high": 30, "medium": 15, "low": 8}
THREAT_INTEL_POINTS = {ThreatIntelStatus.MALICIOUS: 45, ThreatIntelStatus.SUSPICIOUS: 25}
GOVERNMENT_POINTS = {GovernmentClaimStatus.CONTRADICTED: 30}

THRESHOLDS = ((70, "CRITICAL"), (40, "HIGH"), (18, "MEDIUM"))
_RANK = {"low": 0, "medium": 1, "high": 2}


@dataclass
class RiskEngineInput:
    message_rule_hits: list[RuleHit]
    domain_check_hits: list[DomainCheckHit]
    threat_intel_result: ThreatIntelResult | None
    government_claim: GovernmentClaimResult


@dataclass
class RiskEngineOutput:
    level: str
    score: int
    contributing_signals: list[str] = field(default_factory=list)


def score_to_level(score: int) -> str:
    for threshold, level in THRESHOLDS:
        if score >= threshold:
            return level
    return "LOW"


def _strongest_per_signal(hits: list[DomainCheckHit]) -> dict[str, str]:
    """A signal repeated across several URLs counts once, at its highest confidence."""
    strongest: dict[str, str] = {}
    for hit in hits:
        if hit.kind != "risk":
            continue
        current = strongest.get(hit.signal)
        if current is None or _RANK[hit.confidence] > _RANK[current]:
            strongest[hit.signal] = hit.confidence
    return strongest


def compute_risk(data: RiskEngineInput) -> RiskEngineOutput:
    score = 0
    signals: list[str] = []

    for hit in data.message_rule_hits:
        score += MESSAGE_POINTS[hit.confidence]
        signals.append(hit.signal)

    for signal, confidence in _strongest_per_signal(data.domain_check_hits).items():
        score += DOMAIN_POINTS[confidence]
        signals.append(signal)

    intel = data.threat_intel_result
    if intel is not None and intel.available and intel.status in THREAT_INTEL_POINTS:
        score += THREAT_INTEL_POINTS[intel.status]
        signals.append(f"threat_intel_{intel.status.value}")

    gov_points = GOVERNMENT_POINTS.get(data.government_claim.claim_status, 0)
    if gov_points:
        score += gov_points
        signals.append(data.government_claim.claim_status.value)

    score = max(0, min(100, score))
    return RiskEngineOutput(level=score_to_level(score), score=score, contributing_signals=signals)
