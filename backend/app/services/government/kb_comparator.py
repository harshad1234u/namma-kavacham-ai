"""Compares detected government claims with the curated KB and assigns one of the six statuses.

Rules:
- `contradicted` only when a cited KB fact conflicts with the message.
- `supported` only when every aspect is backed by the KB; a specific claim (suspension,
  refund, instalment...) or a requested action the KB does not describe makes it partial.
- Nothing here reduces risk. A supported claim does not make a message genuine.
"""

from app.schemas.government_claim import (
    DetectedClaim,
    GovernmentClaimResult,
    GovernmentClaimStatus,
    KbFinding,
    KbSource,
)
from app.services.government.claim_detector import installment_amounts
from app.services.government.kb import GovernmentKb, KbEntry
from app.services.url_analyzer import NormalizedUrl

_CLAIM_TYPE_TEXT = {
    "suspension_or_block_threat": ("a suspension or blocking threat", "முடக்கம் அல்லது தடை அச்சுறுத்தல்"),
    "benefit_or_installment": ("a pending benefit or instalment", "நிலுவையில் உள்ள நலத்திட்டம் அல்லது தவணை"),
    "refund": ("a refund", "பணத் திருப்பம் (ரீஃபண்ட்)"),
    "verification_or_kyc": ("a verification or KYC update", "சரிபார்ப்பு அல்லது KYC புதுப்பிப்பு"),
    "legal_or_penalty_notice": ("a legal notice or penalty", "சட்ட அறிவிப்பு அல்லது அபராதம்"),
}
_ACTION_TEXT = {
    "share_otp_pin_or_password": ("share an OTP, PIN or password", "OTP, PIN அல்லது கடவுச்சொல்லைப் பகிர்வது"),
    "pay_money_or_fee": ("pay money or a fee", "பணம் அல்லது கட்டணம் செலுத்துவது"),
    "install_app": ("install an app", "செயலியை நிறுவுவது"),
    "install_remote_access_app": ("install a remote-access app", "தொலை அணுகல் செயலியை நிறுவுவது"),
    "send_documents_or_bank_details": ("send documents or bank details", "ஆவணங்கள் அல்லது வங்கி விவரங்களை அனுப்புவது"),
    "call_number_in_message": ("call a number given in the message", "செய்தியில் உள்ள எண்ணை அழைப்பது"),
    "apply_through_chat_app": ("apply through WhatsApp or Telegram", "வாட்ஸ்அப் அல்லது டெலிகிராம் மூலம் விண்ணப்பிப்பது"),
}
_ACTION_SIGNAL = {
    "share_otp_pin_or_password": "credential_request",
    "pay_money_or_fee": "payment_or_fee_request",
    "apply_through_chat_app": "unofficial_channel_application",
}

LIMITATIONS = {
    GovernmentClaimStatus.NOT_GOVERNMENT_RELATED: ([], []),
    GovernmentClaimStatus.UNABLE_TO_ASSESS: (
        ["The message refers to a government scheme or department only in general terms, so it could not be "
         "matched to a specific entry in the curated reference. It was not checked."],
        ["செய்தி அரசுத் திட்டம் அல்லது துறையைப் பொதுவாக மட்டுமே குறிப்பிடுவதால், தொகுக்கப்பட்ட குறிப்பில் உள்ள "
         "குறிப்பிட்ட பதிவுடன் பொருத்த முடியவில்லை. இது சரிபார்க்கப்படவில்லை."],
    ),
    GovernmentClaimStatus.NOT_FOUND: (
        ["The government service named in the message is not in the curated reference, so its claim was not "
         "compared. This does not mean the message is genuine or fraudulent."],
        ["செய்தியில் குறிப்பிடப்பட்ட அரசுச் சேவை தொகுக்கப்பட்ட குறிப்பில் இல்லை, எனவே அதன் கூற்று ஒப்பிடப்படவில்லை. "
         "இது செய்தி உண்மையானது அல்லது மோசடி என்று அர்த்தமல்ல."],
    ),
    GovernmentClaimStatus.PARTIALLY_SUPPORTED: (
        ["Only part of the message matches the curated reference. The service exists, but at least one claim "
         "or instruction in the message is not backed by the reference."],
        ["செய்தியின் ஒரு பகுதி மட்டுமே தொகுக்கப்பட்ட குறிப்புடன் பொருந்துகிறது. சேவை உள்ளது, ஆனால் செய்தியில் உள்ள குறைந்தது "
         "ஒரு கூற்று அல்லது வழிமுறை குறிப்பால் உறுதிப்படுத்தப்படவில்லை."],
    ),
    GovernmentClaimStatus.CONTRADICTED: (
        ["At least one detail in the message conflicts with official information in the curated reference."],
        ["செய்தியில் உள்ள குறைந்தது ஒரு விவரம் தொகுக்கப்பட்ட குறிப்பில் உள்ள அதிகாரப்பூர்வ தகவலுக்கு முரணாக உள்ளது."],
    ),
    GovernmentClaimStatus.SUPPORTED: (
        ["The service and link match the curated reference. This does not confirm that the message was sent by "
         "that service."],
        ["சேவையும் இணைப்பும் தொகுக்கப்பட்ட குறிப்புடன் பொருந்துகின்றன. இது அந்தச் சேவையே செய்தியை அனுப்பியது என்பதை "
         "உறுதிப்படுத்தாது."],
    ),
}


def _on_domain(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def _alias_tokens(entry: KbEntry) -> list[str]:
    tokens = {"".join(ch for ch in a if ch.isalnum()) for a in entry.aliases if a.isascii()}
    return [t for t in tokens if len(t) >= 5]


def _entry_findings(entry: KbEntry, claim: DetectedClaim, text: str, rule_signals: set[str],
                    urls: list[NormalizedUrl]) -> list[KbFinding]:
    domain = entry.official_domains[0]
    findings = [KbFinding(
        aspect="service_exists", outcome="supported", kb_entry_id=entry.id,
        detail_en=f"{entry.service_name} is a real service in the curated reference (official site: {domain}). "
                  "This does not confirm that this message comes from it.",
        detail_ta=f"{entry.service_name_ta} தொகுக்கப்பட்ட குறிப்பில் உள்ள உண்மையான சேவை (அதிகாரப்பூர்வ தளம்: {domain}). "
                  "இந்தச் செய்தி அதிலிருந்து வந்தது என்பதை இது உறுதிப்படுத்தாது.",
    )]

    for url in urls:
        host = url.hostname
        if any(_on_domain(host, d) for d in entry.official_domains):
            findings.append(KbFinding(
                aspect="official_link", outcome="supported", kb_entry_id=entry.id,
                detail_en=f"The link is on {host}, an official domain for {entry.service_name}. An official domain "
                          "does not validate every instruction in the message.",
                detail_ta=f"இணைப்பு {host}-இல் உள்ளது, இது {entry.service_name_ta}-இன் அதிகாரப்பூர்வ டொமைன். அதிகாரப்பூர்வ "
                          "டொமைன் செய்தியின் ஒவ்வொரு வழிமுறையையும் உறுதிப்படுத்தாது.",
            ))
        elif any(tok in host.replace("-", "").replace(".", "") for tok in _alias_tokens(entry)):
            findings.append(KbFinding(
                aspect="official_link", outcome="contradicted", kb_entry_id=entry.id,
                detail_en=f"The link {host} uses the name of {entry.service_name} but is not on its official "
                          f"domain ({domain}).",
                detail_ta=f"{host} என்ற இணைப்பு {entry.service_name_ta}-இன் பெயரைப் பயன்படுத்துகிறது, ஆனால் அதன் "
                          f"அதிகாரப்பூர்வ டொமைனில் ({domain}) இல்லை.",
            ))
        else:
            findings.append(KbFinding(
                aspect="official_link", outcome="not_covered", kb_entry_id=entry.id,
                detail_en=f"The link {host} is not an official domain listed for {entry.service_name} ({domain}).",
                detail_ta=f"{host} என்ற இணைப்பு {entry.service_name_ta}-க்குப் பட்டியலிடப்பட்ட அதிகாரப்பூர்வ டொமைன் "
                          f"({domain}) அல்ல.",
            ))

    covered_signals: set[str] = set()
    covered_claim = False
    for fact in entry.facts:
        if fact.applies_to_signal and fact.applies_to_signal in rule_signals:
            covered_signals.add(fact.applies_to_signal)
            findings.append(KbFinding(
                aspect=f"fact:{fact.id}",
                outcome="contradicted" if fact.effect == "contradicts" else "not_covered",
                detail_en=fact.statement_en, detail_ta=fact.statement_ta,
                kb_entry_id=entry.id, source_ref=fact.source_ref,
            ))
        elif fact.applies_to_claim == "installment_amount" and claim.claim_type == "benefit_or_installment":
            amounts = installment_amounts(text)
            if not amounts:
                continue
            covered_claim = True
            expected = fact.expected_amount_inr
            if expected in amounts:
                findings.append(KbFinding(
                    aspect=f"fact:{fact.id}", outcome="supported", kb_entry_id=entry.id, source_ref=fact.source_ref,
                    detail_en=f"The instalment amount in the message (₹{expected:,}) matches the reference. "
                              + fact.statement_en,
                    detail_ta=f"செய்தியில் உள்ள தவணைத் தொகை (₹{expected:,}) குறிப்புடன் பொருந்துகிறது. " + fact.statement_ta,
                ))
            else:
                shown = ", ".join(f"₹{a:,}" for a in amounts)
                findings.append(KbFinding(
                    aspect=f"fact:{fact.id}", outcome="contradicted", kb_entry_id=entry.id, source_ref=fact.source_ref,
                    detail_en=f"The message states an instalment of {shown}. " + fact.statement_en,
                    detail_ta=f"செய்தி {shown} தவணையைக் குறிப்பிடுகிறது. " + fact.statement_ta,
                ))

    if claim.claim_type in _CLAIM_TYPE_TEXT and not covered_claim:
        en, ta = _CLAIM_TYPE_TEXT[claim.claim_type]
        findings.append(KbFinding(
            aspect="claim", outcome="not_covered", kb_entry_id=entry.id,
            detail_en=f"The message makes {en}. The curated reference has no information confirming this.",
            detail_ta=f"செய்தி {ta} பற்றிக் கூறுகிறது. இதை உறுதிப்படுத்தும் தகவல் தொகுக்கப்பட்ட குறிப்பில் இல்லை.",
        ))

    for action in claim.requested_actions:
        if action == "open_link" or _ACTION_SIGNAL.get(action) in covered_signals:
            continue
        en, ta = _ACTION_TEXT[action]
        findings.append(KbFinding(
            aspect="requested_action", outcome="not_covered", kb_entry_id=entry.id,
            detail_en=f"The message asks you to {en}. The curated reference does not describe {entry.service_name} "
                      "asking for this.",
            detail_ta=f"செய்தி {ta} பற்றிக் கேட்கிறது. {entry.service_name_ta} இதைக் கேட்பதாகத் தொகுக்கப்பட்ட குறிப்பு "
                      "குறிப்பிடவில்லை.",
        ))
    return findings


def _sources(entry: KbEntry, kb: GovernmentKb) -> list[KbSource]:
    return [
        KbSource(
            kb_entry_id=entry.id,
            name=entry.service_name,
            authority=entry.authority,
            official_url=entry.official_urls[0],
            source_citation=f"{doc.publisher}: {doc.title}",
            last_reviewed=kb.last_reviewed,
            source_url=doc.url,
            published=doc.published,
        )
        for doc in entry.sources
    ]


def _status(findings: list[KbFinding]) -> GovernmentClaimStatus:
    outcomes = {f.outcome for f in findings}
    if "contradicted" in outcomes:
        return GovernmentClaimStatus.CONTRADICTED
    if outcomes & {"not_covered", "ambiguous"}:
        return GovernmentClaimStatus.PARTIALLY_SUPPORTED
    return GovernmentClaimStatus.SUPPORTED


def compare_claims(claims: list[DetectedClaim], kb: GovernmentKb, text: str, rule_signals: set[str],
                   urls: list[NormalizedUrl]) -> GovernmentClaimResult:
    if not claims:
        status = GovernmentClaimStatus.NOT_GOVERNMENT_RELATED
        return GovernmentClaimResult(government_related=False, claim_status=status)

    entries = {e.id: e for e in kb.entries}
    matched = [c for c in claims if c.kb_entry_id]
    findings: list[KbFinding] = []
    for claim in matched:
        findings.extend(_entry_findings(entries[claim.kb_entry_id], claim, text, rule_signals, urls))

    for claim in claims:
        if claim.kb_entry_id:
            continue
        name = claim.scheme_or_service.value
        if claim.scheme_or_service.ambiguous:
            findings.append(KbFinding(
                aspect="service_identity", outcome="ambiguous",
                detail_en=f"The message mentions '{name}' without naming a specific scheme or department. It was "
                          "not matched to any scheme.",
                detail_ta=f"செய்தி குறிப்பிட்ட திட்டம் அல்லது துறையைப் பெயரிடாமல் '{name}' என்று குறிப்பிடுகிறது. இது எந்தத் "
                          "திட்டத்துடனும் பொருத்தப்படவில்லை.",
            ))
        else:
            findings.append(KbFinding(
                aspect="service_identity", outcome="not_covered",
                detail_en=f"{name} is not covered by the curated reference, so this claim was not compared.",
                detail_ta=f"{name} தொகுக்கப்பட்ட குறிப்பில் இல்லை, எனவே இந்தக் கூற்று ஒப்பிடப்படவில்லை.",
            ))

    if matched:
        status = _status(findings)
    elif any(not c.scheme_or_service.ambiguous for c in claims):
        status = GovernmentClaimStatus.NOT_FOUND
    else:
        status = GovernmentClaimStatus.UNABLE_TO_ASSESS

    matched_entries = [entries[i] for i in dict.fromkeys(c.kb_entry_id for c in matched)]
    limitations_en, limitations_ta = LIMITATIONS[status]
    return GovernmentClaimResult(
        government_related=True,
        claim_status=status,
        claims=claims,
        matched_kb_entries=[e.id for e in matched_entries],
        sources=[s for e in matched_entries for s in _sources(e, kb)],
        findings=findings,
        limitations=list(limitations_en),
        limitations_ta=list(limitations_ta),
        safe_guidance_en=[e.safe_guidance_en for e in matched_entries],
        safe_guidance_ta=[e.safe_guidance_ta for e in matched_entries],
    )
