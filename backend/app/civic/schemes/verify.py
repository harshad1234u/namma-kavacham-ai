"""Check a claim about a government scheme against the verified knowledge base.

Statuses: supported, partially_supported, contradicted, not_found, unable_to_verify.
"contradicted" is only used where a verified source settles the point (an application link on a
lookalike of the scheme's official domain). An amount the sources do not state is reported as
"not covered", never as false: the claim may describe a benefit our sources do not quote.
"""
import re
from dataclasses import dataclass
from typing import Literal

from app.civic.schemes.identify import identify_schemes, mentions_a_scheme
from app.civic.schemes.kb import get_scheme
from app.civic.schemes.schema import Scheme, is_official_host, norm
from app.civic.text import amounts_inr

VerifyStatus = Literal["supported", "partially_supported", "contradicted", "not_found", "unable_to_verify"]
Outcome = Literal["supported", "contradicted", "not_covered"]

_URL = re.compile(r"https?://[^\s<>\"']+|(?<![@\w])(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:in|com|org|net|co|info|xyz|online|site|top)(?:/[^\s<>\"']*)?", re.I)


@dataclass(frozen=True)
class Finding:
    aspect: Literal["scheme_exists", "amount", "link"]
    outcome: Outcome
    detail_en: str
    source_ref: str | None = None


@dataclass(frozen=True)
class SchemeVerification:
    scheme: Scheme
    findings: list[Finding]


@dataclass(frozen=True)
class VerifyOutcome:
    status: VerifyStatus
    schemes: list[SchemeVerification]


def _host(raw: str) -> str | None:
    m = re.match(r"^(?:[a-z]+://)?([^/:?#\s]+)", raw, re.I)
    return m.group(1).lower().rstrip(".") if m else None


def link_status(host: str, scheme: Scheme) -> Outcome:
    if any(host == d or host.endswith("." + d) for d in scheme.official_domains):
        return "supported"
    tokens = {re.sub(r"[^a-z0-9]", "", norm(a)) for a in (*scheme.abbreviations, *scheme.aliases) if a.isascii()}
    squashed = re.sub(r"[^a-z0-9]", "", host)
    if not is_official_host(host) and any(len(tok) >= 5 and tok in squashed for tok in tokens):
        return "contradicted"  # looks like the scheme's site but is not its official domain
    return "not_covered"


def _stated_amounts(scheme: Scheme) -> set[int]:
    out: set[int] = set()
    for b in scheme.benefits:
        if b.amount_inr:
            out.add(b.amount_inr)
        out |= amounts_inr(b.text["en"]) | amounts_inr(b.quote)
    return out


def _findings(scheme: Scheme, text: str, url: str | None) -> list[Finding]:
    src = scheme.description.source_ref
    found = [Finding("scheme_exists", "supported", f"{scheme.names['en']} is in the verified scheme set.", src)]
    stated = _stated_amounts(scheme)
    for amount in sorted(amounts_inr(text)):
        if amount in stated:
            ref = next((b.source_ref for b in scheme.benefits if amount in amounts_inr(b.text["en"]) or b.amount_inr == amount), src)
            found.append(Finding("amount", "supported", f"The official source states the amount ₹{amount:,}.", ref))
        else:
            detail = f"₹{amount:,} is not stated in the official sources we hold for this scheme."
            if stated:
                detail += " They state: " + ", ".join(f"₹{a:,}" for a in sorted(stated)) + "."
            found.append(Finding("amount", "not_covered", detail))
    hosts = {h for raw in _URL.findall(text + " " + (url or "")) if (h := _host(raw))}
    for host in sorted(hosts):
        outcome = link_status(host, scheme)
        detail = {
            "supported": f"{host} is an official domain of this scheme.",
            "contradicted": f"{host} imitates this scheme's name but is not its official domain ({', '.join(scheme.official_domains)}).",
            "not_covered": f"{host} is not one of this scheme's official domains ({', '.join(scheme.official_domains)}).",
        }[outcome]
        found.append(Finding("link", outcome, detail))
    return found


def verify_claim(text: str, url: str | None = None) -> VerifyOutcome:
    matches = identify_schemes(text)
    if not matches:
        return VerifyOutcome("not_found" if mentions_a_scheme(text) else "unable_to_verify", [])
    results = [SchemeVerification(s, _findings(s, text, url)) for m in matches if (s := get_scheme(m.scheme_id))]
    outcomes = {f.outcome for r in results for f in r.findings}
    if "contradicted" in outcomes:
        status: VerifyStatus = "contradicted"
    elif "not_covered" in outcomes:
        status = "partially_supported"
    else:
        status = "supported"
    return VerifyOutcome(status, results)
