"""Deterministic verification of a claim about a government scheme.

Order: curated KB first; if the claim names nothing in the KB, evidence retrieved from official
government pages. The LLM never takes part in this decision.

Statuses
- supported            every checked aspect is backed by the official source
- partially_supported  the scheme is confirmed, but some claimed detail is not stated by the source
- contradicted         an official source states something different (an amount for the same period,
                       or an application link on a lookalike of the scheme's official domain)
- not_found            official sources were read, and none of them mentions the named scheme
                       (this does NOT mean the scheme is fake)
- unable_to_verify     nothing identifiable to check, or no official source could be read
"""
import re
from dataclasses import dataclass, field
from typing import Literal

from app.civic.retrieval.index import Evidence, tokens
from app.civic.retrieval.service import RetrievalResult
from app.civic.schemes.kb import get_scheme
from app.civic.schemes.schema import Scheme, is_official_host, norm
from app.civic.text import amounts_inr, amounts_with_period, inr

VerifyStatus = Literal["supported", "partially_supported", "contradicted", "not_found", "unable_to_verify"]
Outcome = Literal["supported", "contradicted", "not_covered"]

UNABLE_MESSAGE = "Unable to verify from the currently available official sources."
NOT_FOUND_MESSAGE = ("The named scheme was not found in the official government sources we checked. "
                     "This does not mean it is fake; confirm on the official portal.")
_PERIOD_TEXT = {"per_year": "per year", "per_month": "per month", "per_day": "per day",
                "per_instalment": "per instalment", "one_time": "one time"}
_URL = re.compile(r"https?://[^\s<>\"']+|(?<![@\w])(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:in|com|org|net|co|info|xyz|online|site|top)(?:/[^\s<>\"']*)?", re.I)
_GENERIC = frozenset("pm pradhan mantri yojana yojna scheme abhiyan mission nidhi government sarkari new the of".split())


@dataclass(frozen=True)
class Finding:
    aspect: Literal["scheme_exists", "amount", "link"]
    outcome: Outcome
    detail_en: str
    source_ref: str | None = None
    evidence_url: str | None = None


@dataclass(frozen=True)
class SchemeVerification:
    scheme: Scheme
    findings: list[Finding]


@dataclass(frozen=True)
class VerifyOutcome:
    status: VerifyStatus
    basis: Literal["curated_kb", "official_evidence", "none"]
    schemes: list[SchemeVerification] = field(default_factory=list)
    evidence_findings: list[Finding] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    message_en: str | None = None


def _host(raw: str) -> str | None:
    m = re.match(r"^(?:[a-z]+://)?([^/:?#\s]+)", raw, re.I)
    return m.group(1).lower().rstrip(".") if m else None


def _hosts(text: str, url: str | None) -> set[str]:
    return {h for raw in _URL.findall(text + " " + (url or "")) if (h := _host(raw))}


def link_status(host: str, scheme: Scheme) -> Outcome:
    if any(host == d or host.endswith("." + d) for d in scheme.official_domains):
        return "supported"
    tokens_ = {re.sub(r"[^a-z0-9]", "", norm(a)) for a in (*scheme.abbreviations, *scheme.aliases) if a.isascii()}
    squashed = re.sub(r"[^a-z0-9]", "", host)
    if not is_official_host(host) and any(len(t) >= 5 and t in squashed for t in tokens_):
        return "contradicted"  # imitates the scheme's name but is not its official domain
    return "not_covered"


def _amount_finding(scheme: Scheme, amount: int, period: str | None) -> Finding:
    stated_all: set[int] = set()
    for b in scheme.benefits:
        stated = amounts_inr(b.text["en"]) | amounts_inr(b.quote) | ({b.amount_inr} if b.amount_inr else set())
        stated_all |= stated
        if period and b.period == period:
            per = _PERIOD_TEXT[period]
            if amount in stated:
                return Finding("amount", "supported", f"The official source states {inr(amount)} {per}.", b.source_ref)
            listed = ", ".join(f"{inr(a)}" for a in sorted(stated))
            return Finding("amount", "contradicted", f"The official source states {listed} {per}, not {inr(amount)}.", b.source_ref)
    if amount in stated_all:
        ref = next(b.source_ref for b in scheme.benefits if amount in amounts_inr(b.text["en"]) | amounts_inr(b.quote) | {b.amount_inr})
        return Finding("amount", "supported", f"The official source states the amount {inr(amount)}.", ref)
    detail = f"{inr(amount)} is not stated in the official sources we hold for this scheme."
    if stated_all:
        detail += " They state: " + ", ".join(f"{inr(a)}" for a in sorted(stated_all)) + "."
    return Finding("amount", "not_covered", detail)


def _kb_findings(scheme: Scheme, text: str, url: str | None) -> list[Finding]:
    found = [Finding("scheme_exists", "supported", f"{scheme.names['en']} is in the verified scheme set.", scheme.description.source_ref)]
    found += [_amount_finding(scheme, a, p) for a, p in amounts_with_period(text)]
    for host in sorted(_hosts(text, url)):
        outcome = link_status(host, scheme)
        domains = ", ".join(scheme.official_domains)
        found.append(Finding("link", outcome, {
            "supported": f"{host} is an official domain of this scheme.",
            "contradicted": f"{host} imitates this scheme's name but is not its official domain ({domains}).",
            "not_covered": f"{host} is not one of this scheme's official domains ({domains}).",
        }[outcome]))
    return found


def _status(findings: list[Finding]) -> VerifyStatus:
    outcomes = {f.outcome for f in findings}
    if "contradicted" in outcomes:
        return "contradicted"
    return "partially_supported" if "not_covered" in outcomes else "supported"


def verify_against_kb(text: str, url: str | None, scheme_ids: list[str]) -> VerifyOutcome | None:
    schemes = [s for sid in scheme_ids if (s := get_scheme(sid))]
    if not schemes:
        return None
    results = [SchemeVerification(s, _kb_findings(s, text, url)) for s in schemes]
    return VerifyOutcome(_status([f for r in results for f in r.findings]), "curated_kb", results)


def _name_tokens(name: str) -> set[str]:
    return {t for t in tokens(name) if t not in _GENERIC}


def verify_against_evidence(text: str, url: str | None, scheme_name: str | None, retrieval: RetrievalResult | None) -> VerifyOutcome:
    """For schemes outside the curated KB: decide only from what official pages actually say."""
    if retrieval is None or not retrieval.available:
        return VerifyOutcome("unable_to_verify", "none", message_en=UNABLE_MESSAGE)
    wanted = _name_tokens(scheme_name or "")
    if not wanted:
        return VerifyOutcome("unable_to_verify", "none", evidence=retrieval.evidence, message_en=UNABLE_MESSAGE)
    mentions = [e for e in retrieval.evidence if wanted <= set(tokens(e.passage))]
    if not mentions:
        return VerifyOutcome("not_found", "official_evidence", message_en=NOT_FOUND_MESSAGE)  # unrelated passages are not evidence
    top = mentions[0]
    findings = [Finding("scheme_exists", "supported", f"An official page ({top.domain}) mentions {scheme_name}.", evidence_url=top.url)]
    for amount, _ in amounts_with_period(text):
        hit = next((e for e in mentions if amount in amounts_inr(e.passage)), None)
        findings.append(Finding("amount", "supported", f"The official page states {inr(amount)}.", evidence_url=hit.url) if hit else
                        Finding("amount", "not_covered", f"{inr(amount)} is not stated in the official passages found."))
    for host in sorted(_hosts(text, url)):
        findings.append(Finding("link", "supported", f"{host} is an official government domain.") if is_official_host(host) else
                        Finding("link", "not_covered", f"{host} is not an official government (.gov.in/.nic.in) domain."))
    return VerifyOutcome(_status(findings), "official_evidence", evidence_findings=findings, evidence=mentions)
