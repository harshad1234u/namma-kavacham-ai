from datetime import datetime, timezone

import pytest

from app.schemas.government_claim import GovernmentClaimResult, GovernmentClaimStatus
from app.schemas.threat_intelligence import ThreatIntelResult, ThreatIntelStatus
from app.services.message_rules import RuleHit
from app.services.risk_engine import RiskEngineInput, compute_risk, score_to_level
from app.services.url_analyzer import DomainCheckHit

NO_GOV = GovernmentClaimResult(government_related=False, claim_status=GovernmentClaimStatus.NOT_GOVERNMENT_RELATED)


def rule(signal: str, confidence: str = "high") -> RuleHit:
    return RuleHit("R", signal, confidence, "", "", "")


def intel(status: ThreatIntelStatus, available: bool = True) -> ThreatIntelResult:
    return ThreatIntelResult(provider="virustotal", indicator="http://x", status=status, available=available,
                             checked_at=datetime.now(timezone.utc), note="")


def run(rules=(), domains=(), ti=None, gov=NO_GOV):
    return compute_risk(RiskEngineInput(list(rules), list(domains), ti, gov))


def test_empty_is_low():
    out = run()
    assert (out.level, out.score) == ("LOW", 0)


def test_single_high_rule_is_medium():
    assert run([rule("credential_request")]).level == "MEDIUM"


def test_two_high_rules_is_high():
    assert run([rule("credential_request"), rule("apk_install_instruction")]).level == "HIGH"


def test_malicious_url_alone_is_high():
    assert run(ti=intel(ThreatIntelStatus.MALICIOUS)).level == "HIGH"


def test_malicious_url_with_credential_harvesting_is_critical():
    assert run([rule("credential_request")], ti=intel(ThreatIntelStatus.MALICIOUS)).level == "CRITICAL"


def test_unavailable_provider_adds_nothing_and_is_not_safe_signal():
    out = run(ti=intel(ThreatIntelStatus.UNAVAILABLE, available=False))
    assert out.score == 0 and out.contributing_signals == []


def test_unavailable_provider_does_not_lower_deterministic_risk():
    base = run([rule("credential_request"), rule("payment_or_fee_request")])
    with_outage = run([rule("credential_request"), rule("payment_or_fee_request")],
                      ti=intel(ThreatIntelStatus.UNAVAILABLE, available=False))
    with_not_found = run([rule("credential_request"), rule("payment_or_fee_request")],
                         ti=intel(ThreatIntelStatus.NOT_FOUND))
    with_clean = run([rule("credential_request"), rule("payment_or_fee_request")],
                     ti=intel(ThreatIntelStatus.CLEAN_OR_HARMLESS))
    assert base.score == with_outage.score == with_not_found.score == with_clean.score


def test_domain_signal_counted_once_across_urls():
    hit = DomainCheckHit("suspicious_tld", "medium", "", "")
    assert run(domains=[hit, hit, hit]).score == 15


def test_info_domain_hits_add_nothing():
    info = DomainCheckHit("government_namespace_domain", "low", "", "", kind="info")
    assert run(domains=[info]).score == 0


def test_kb_support_never_reduces_risk():
    supported = GovernmentClaimResult(government_related=True, claim_status=GovernmentClaimStatus.SUPPORTED)
    assert run([rule("credential_request")], gov=supported).score == run([rule("credential_request")]).score


def test_kb_contradiction_raises_risk():
    contradicted = GovernmentClaimResult(government_related=True, claim_status=GovernmentClaimStatus.CONTRADICTED)
    assert run(gov=contradicted).score == 30


def test_kb_contradiction_alone_is_not_treated_as_proof_of_fraud():
    contradicted = GovernmentClaimResult(government_related=True, claim_status=GovernmentClaimStatus.CONTRADICTED)
    assert run(gov=contradicted).level == "MEDIUM"


@pytest.mark.parametrize(
    "status",
    [s for s in GovernmentClaimStatus if s != GovernmentClaimStatus.CONTRADICTED],
)
def test_uncertain_or_supportive_claim_status_neither_raises_nor_lowers(status):
    gov = GovernmentClaimResult(government_related=status != GovernmentClaimStatus.NOT_GOVERNMENT_RELATED,
                                claim_status=status)
    base = run([rule("credential_request"), rule("payment_or_fee_request")])
    out = run([rule("credential_request"), rule("payment_or_fee_request")], gov=gov)
    assert (out.score, out.level) == (base.score, base.level)
    assert status.value not in out.contributing_signals


def test_contradiction_with_provider_outage_keeps_contradiction_points():
    contradicted = GovernmentClaimResult(government_related=True, claim_status=GovernmentClaimStatus.CONTRADICTED)
    outage = intel(ThreatIntelStatus.UNAVAILABLE, available=False)
    assert run(gov=contradicted, ti=outage).score == run(gov=contradicted).score == 30


def test_score_is_clamped():
    out = run([rule(f"s{i}") for i in range(10)])
    assert out.score == 100 and out.level == "CRITICAL"


def test_thresholds():
    assert [score_to_level(s) for s in (0, 17, 18, 39, 40, 69, 70)] == \
        ["LOW", "LOW", "MEDIUM", "MEDIUM", "HIGH", "HIGH", "CRITICAL"]
