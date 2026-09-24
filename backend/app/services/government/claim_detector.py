"""Government-claim detection (deterministic, English / Tamil / Tanglish).

Finds which government service a message invokes, what it claims, and which
amounts it mentions. It never upgrades a vague reference ("PM scheme",
"government subsidy") into a specific scheme: vague references stay ambiguous.
Detection says nothing about whether the message is genuine.
"""

import re

from app.schemas.government_claim import ClaimField, DetectedClaim
from app.services.government.kb import GovernmentKb, KbEntry

# Specific services the curated KB does not cover. Naming one leads to `not_found_in_curated_kb`.
_UNCOVERED_SERVICES: dict[str, tuple[str, ...]] = {
    "Electricity board (TNEB / TANGEDCO)": ("tneb", "tangedco", "electricity board", "eb bill", "மின் வாரியம்", "மின்சார வாரியம்"),
    "EPFO / Provident Fund": ("epfo", "provident fund", "pf account", "uan number"),
    "Ration card / PDS": ("ration card", "ரேஷன்"),
    "Voter ID / Election Commission": ("voter id", "epic card", "election commission"),
    "Driving licence / vehicle (Parivahan)": ("driving licence", "driving license", "parivahan", "e-challan", "traffic challan", "rto"),
    "Telecom / SIM (DoT, TRAI)": ("trai", "department of telecom", "sim will be blocked", "sim card block"),
    "LPG / gas subsidy": ("lpg subsidy", "gas subsidy", "gas connection"),
    "Law enforcement (CBI / police / customs)": ("cbi", "narcotics", "customs", "digital arrest", "police case", "crime branch"),
}

# Generic references: government-related, but too vague to compare against the KB.
_GENERIC_PATTERN = re.compile(
    r"\b(pm scheme|pm yojana|pradhan mantri yojana|government scheme|govt scheme|sarkari yojana|"
    r"government subsidy|govt subsidy|government benefit|govt benefit|government department|govt department|"
    r"ministry|central government|state government|scholarship|pension|dbt)\b"
    r"|(அரசு திட்டம்|அரசுத் திட்டம்|அரசு மானியம்|மானியம்|உதவித்தொகை|ஓய்வூதியம்|அமைச்சகம்)"
)

_CLAIM_TYPES: list[tuple[str, re.Pattern[str]]] = [
    ("suspension_or_block_threat", re.compile(
        r"\b(suspend|suspended|block|blocked|deactivat|cancel|disconnect|frozen|freeze|closed|terminat|expire|aagidum)"
        r"|(முடக்க|நிறுத்த|இடைநிறுத்த|ரத்து|துண்டிக்க|காலாவதி)")),
    ("benefit_or_installment", re.compile(
        r"\b(installment|instalment|benefit|subsidy|kist|credited|release|pending amount)\b"
        r"|(தவணை|நலத்திட்ட|மானியம்|வரவு)")),
    ("refund", re.compile(r"\b(refund|tax return|itr)\b|(திருப்பி|ரீஃபண்ட்)")),
    ("verification_or_kyc", re.compile(r"\b(kyc|verify|verification|update|link your|re-?verify)\b|(சரிபார்|புதுப்பி)")),
    ("legal_or_penalty_notice", re.compile(r"\b(notice|penalty|fine|arrest|warrant|legal action|case)\b|(அபராதம்|கைது|நோட்டீஸ்)")),
    ("report_or_complaint", re.compile(r"\b(report|complaint|complain)\b|(புகார்)")),
]

_AMOUNT = re.compile(r"(?:₹|\brs\.?\s?|\binr\s?)\s?(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d{1,2})?|\b(\d{1,3}(?:,\d{2,3})+|\d+)\s?(?:rupees|/-)")

_SIGNAL_ACTIONS = {
    "credential_request": "share_otp_pin_or_password",
    "payment_or_fee_request": "pay_money_or_fee",
    "apk_install_instruction": "install_app",
    "remote_access_app_request": "install_remote_access_app",
    "sensitive_document_request": "send_documents_or_bank_details",
    "unverified_callback_number": "call_number_in_message",
}


def _alias_pattern(alias: str) -> re.Pattern[str]:
    if re.search(r"[a-z0-9]", alias):
        return re.compile(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])")
    return re.compile(re.escape(alias))


def _amounts(text: str) -> list[int]:
    values: list[int] = []
    for m in _AMOUNT.finditer(text):
        raw = (m.group(1) or m.group(2) or "").replace(",", "")
        if raw.isdigit():
            values.append(int(raw))
    return values


_INSTALLMENT_WORDS = r"(installment|instalment|kist|தவணை)"
_AMOUNT_TOKEN = r"(?:₹|rs\.?\s?|inr\s?)\s?(\d{1,3}(?:,\d{2,3})+|\d+)"
_INSTALLMENT_AMOUNT = re.compile(
    rf"{_INSTALLMENT_WORDS}[^.!?\n]{{0,40}}?{_AMOUNT_TOKEN}|{_AMOUNT_TOKEN}[^.!?\n]{{0,25}}?{_INSTALLMENT_WORDS}"
)


def installment_amounts(text: str) -> list[int]:
    """Amounts the message ties to an instalment (not unrelated fees mentioned elsewhere)."""
    values = []
    for m in _INSTALLMENT_AMOUNT.finditer(text):
        raw = (m.group(2) or m.group(3) or "").replace(",", "")
        if raw.isdigit():
            values.append(int(raw))
    return values


def _claim_type(text: str) -> str:
    return next((name for name, pattern in _CLAIM_TYPES if pattern.search(text)), "service_reference")


def _requested_actions(rule_signals: set[str], has_url: bool) -> list[str]:
    actions = [action for signal, action in _SIGNAL_ACTIONS.items() if signal in rule_signals]
    if has_url:
        actions.append("open_link")
    return actions


def _matches(entry: KbEntry, text: str) -> str | None:
    return next((a for a in entry.aliases if _alias_pattern(a).search(text)), None)


def detect_claims(normalized_text: str, kb: GovernmentKb, rule_signals: set[str], has_url: bool) -> list[DetectedClaim]:
    if not normalized_text:
        return []
    claim_type = _claim_type(normalized_text)
    actions = _requested_actions(rule_signals, has_url)
    amounts = _amounts(normalized_text)
    claims: list[DetectedClaim] = []

    for entry in kb.entries:
        alias = _matches(entry, normalized_text)
        if alias:
            claims.append(DetectedClaim(
                claim_type=claim_type,
                category=entry.category,
                scheme_or_service=ClaimField(value=entry.service_name, confidence="high"),
                department=ClaimField(value=entry.authority, confidence="medium"),
                requested_actions=actions,
                kb_entry_id=entry.id,
                amounts_inr=amounts,
            ))

    for service, aliases in _UNCOVERED_SERVICES.items():
        if any(_alias_pattern(a.strip()).search(normalized_text) for a in aliases):
            claims.append(DetectedClaim(
                claim_type=claim_type,
                scheme_or_service=ClaimField(value=service, confidence="medium"),
                requested_actions=actions,
                amounts_inr=amounts,
            ))

    if not claims:
        generic = _GENERIC_PATTERN.search(normalized_text)
        if generic:
            claims.append(DetectedClaim(
                claim_type=claim_type,
                scheme_or_service=ClaimField(value=generic.group(0), confidence="low", ambiguous=True),
                requested_actions=actions,
                amounts_inr=amounts,
            ))
    return claims
