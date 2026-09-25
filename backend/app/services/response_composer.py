"""Deterministic report text: missing data, limitations, sender handling, and safe next steps (EN + TA)."""

import re

from app.schemas.analysis import AnalyzeRequest, SenderAssessmentOut
from app.schemas.government_claim import GovernmentClaimResult, GovernmentClaimStatus
from app.schemas.threat_intelligence import ThreatIntelResult, ThreatIntelStatus, UnavailableReason

VERDICT_SCOPE = (
    "This is a message-risk assessment based on the content you submitted and observable "
    "indicators. It does not verify the sender's identity, authenticate any organization, or "
    "guarantee that a message is genuine or fraudulent."
)
VERDICT_SCOPE_TA = (
    "இது நீங்கள் சமர்ப்பித்த உள்ளடக்கம் மற்றும் காணக்கூடிய குறிகளின் அடிப்படையிலான செய்தி-ஆபத்து மதிப்பீடு. இது "
    "அனுப்புநரின் அடையாளத்தைச் சரிபார்க்கவோ, எந்த நிறுவனத்தையும் உறுதிப்படுத்தவோ, செய்தி உண்மையானது அல்லது மோசடி "
    "என்று உத்தரவாதம் அளிக்கவோ இல்லை."
)

HELPLINE_STEP = (
    "If you already shared an OTP or lost money, call the National Cyber Crime Helpline 1930 "
    "immediately or report at cybercrime.gov.in.",
    "ஏற்கனவே OTP பகிர்ந்திருந்தால் அல்லது பணத்தை இழந்திருந்தால், உடனடியாக தேசிய சைபர் குற்ற உதவி எண் 1930-ஐ "
    "அழைக்கவும் அல்லது cybercrime.gov.in-இல் புகாரளிக்கவும்.",
)
VERIFY_STEP = (
    "Verify the claim yourself by typing the official website address or opening the official "
    "app — not through any link, number, or contact in this message.",
    "இந்தச் செய்தியில் உள்ள இணைப்பு, எண் அல்லது தொடர்பு மூலம் அல்லாமல், அதிகாரப்பூர்வ இணையதள முகவரியை நீங்களே "
    "தட்டச்சு செய்து அல்லது அதிகாரப்பூர்வ செயலியைத் திறந்து சரிபார்க்கவும்.",
)
_CONDITIONAL_STEPS: list[tuple[set[str], tuple[str, str]]] = [
    (
        {"credential_request"},
        ("Do not share any OTP, PIN, UPI PIN, password, or verification code.",
         "எந்த OTP, PIN, UPI PIN, கடவுச்சொல் அல்லது சரிபார்ப்புக் குறியீட்டையும் பகிர வேண்டாம்."),
    ),
    (
        {"payment_or_fee_request", "personal_upi_payment", "fee_for_free_benefit"},
        ("Do not pay any fee or transfer money based on this message.",
         "இந்தச் செய்தியின் அடிப்படையில் எந்தக் கட்டணமும் செலுத்தவோ பணம் அனுப்பவோ வேண்டாம்."),
    ),
    (
        {"apk_install_instruction", "executable_download_link", "remote_access_app_request"},
        ("Do not install any app or file from this message. If you already installed one, disconnect "
         "from the internet and seek help before using banking apps.",
         "இந்தச் செய்தியிலிருந்து எந்தச் செயலியையும் கோப்பையும் நிறுவ வேண்டாம். ஏற்கனவே நிறுவியிருந்தால், இணையத்தைத் "
         "துண்டித்து, வங்கிச் செயலிகளைப் பயன்படுத்தும் முன் உதவி பெறவும்."),
    ),
    (
        {"sensitive_document_request"},
        ("Do not send identity documents, card details, or bank details in reply.",
         "பதிலாக அடையாள ஆவணங்கள், அட்டை அல்லது வங்கி விவரங்களை அனுப்ப வேண்டாம்."),
    ),
    (
        {"unofficial_channel_application"},
        ("Do not apply or send documents through WhatsApp or Telegram; apply only on the official website "
         "or at a government office.",
         "வாட்ஸ்அப் அல்லது டெலிகிராம் மூலம் விண்ணப்பிக்கவோ ஆவணங்களை அனுப்பவோ வேண்டாம்; அதிகாரப்பூர்வ இணையதளத்திலோ "
         "அரசு அலுவலகத்திலோ மட்டுமே விண்ணப்பிக்கவும்."),
    ),
    (
        {"unverified_callback_number"},
        ("Do not call the number given in the message; use the helpline listed on the official website.",
         "செய்தியில் கொடுக்கப்பட்ட எண்ணை அழைக்க வேண்டாம்; அதிகாரப்பூர்வ இணையதளத்தில் உள்ள உதவி எண்ணைப் பயன்படுத்தவும்."),
    ),
]
_LINK_STEP = (
    "Do not open the link or enter any login, card, or personal details on it.",
    "இணைப்பைத் திறக்கவோ அதில் உள்நுழைவு, அட்டை அல்லது தனிப்பட்ட விவரங்களை உள்ளிடவோ வேண்டாம்.",
)
_LOW_RISK_STEP = (
    "No strong risk indicators were found, but that does not prove the message is genuine. "
    "Stay cautious with any request for money or personal details.",
    "வலுவான ஆபத்துக் குறிகள் கண்டறியப்படவில்லை, ஆனால் இது செய்தி உண்மையானது என்பதற்கான ஆதாரம் அல்ல. பணம் அல்லது "
    "தனிப்பட்ட விவரங்கள் கோரும் எந்தக் கோரிக்கையிலும் எச்சரிக்கையாக இருங்கள்.",
)


def safe_next_steps(
    level: str,
    signals: set[str],
    has_url: bool,
    official_guidance: list[tuple[str, str]] | None = None,
) -> tuple[list[str], list[str]]:
    steps: list[tuple[str, str]] = []
    if has_url and level != "LOW":
        steps.append(_LINK_STEP)
    for triggers, step in _CONDITIONAL_STEPS:
        if signals & triggers and step not in steps:
            steps.append(step)
    if level == "LOW":
        steps.append(_LOW_RISK_STEP)
    steps.extend(official_guidance or [])
    steps.append(VERIFY_STEP)
    steps.append(HELPLINE_STEP)
    return [s[0] for s in steps], [s[1] for s in steps]


def missing_metadata(
    request: AnalyzeRequest,
    intel: ThreatIntelResult | None,
    has_url: bool,
    ocr_attempted: bool,
    government: GovernmentClaimResult,
) -> list[str]:
    missing: list[str] = []
    if request.sender is None or not request.sender.value:
        missing.append("sender_identity_not_supplied")
    missing.append("original_message_timestamp")
    missing.append("original_messaging_app")
    if has_url:
        if intel is None or intel.status == ThreatIntelStatus.UNAVAILABLE:
            reason = intel.unavailable_reason if intel else None
            missing.append(
                "url_threat_intelligence_disabled"
                if reason in (UnavailableReason.DISABLED, UnavailableReason.NOT_CONFIGURED)
                else "url_threat_intelligence_unavailable"
            )
        elif intel.status == ThreatIntelStatus.NOT_FOUND:
            missing.append("no_threat_intelligence_report_for_url")
    if ocr_attempted:
        missing.append("screenshot_text_extraction_not_available")
    if government.claim_status == GovernmentClaimStatus.UNABLE_TO_ASSESS:
        missing.append("government_claim_too_vague_to_compare")
    elif government.claim_status == GovernmentClaimStatus.NOT_FOUND:
        missing.append("government_service_not_in_curated_kb")
    if government.government_related:
        missing.append("government_records_not_checked_live")
    return missing


def limitations(
    has_url: bool, intel: ThreatIntelResult | None, explanation_by_ai: bool
) -> tuple[list[str], list[str]]:
    pairs: list[tuple[str, str] | None] = [
        ("The sender's identity was not authenticated. Phone numbers, sender IDs, and names can be spoofed.",
         "அனுப்புநரின் அடையாளம் உறுதிப்படுத்தப்படவில்லை. தொலைபேசி எண்கள், அனுப்புநர் ஐடிகள், பெயர்கள் போலியாக்கப்படலாம்."),
        ("The link was not opened or visited; only its address was analysed.",
         "இணைப்பு திறக்கப்படவில்லை; அதன் முகவரி மட்டுமே பகுப்பாய்வு செய்யப்பட்டது.") if has_url else None,
        (f"URL threat intelligence ({intel.provider}): {intel.note}",
         f"இணைப்பு அச்சுறுத்தல் தகவல் ({intel.provider}): {intel.note_ta or intel.note}") if has_url and intel else None,
        ("The explanation is AI-generated from the evidence above. It is not an official statement.",
         "விளக்கம் மேலே உள்ள ஆதாரங்களிலிருந்து AI மூலம் உருவாக்கப்பட்டது. இது அதிகாரப்பூர்வ அறிக்கை அல்ல.")
        if explanation_by_ai else
        ("The explanation was composed from fixed templates; no AI explanation was generated.",
         "விளக்கம் நிலையான வார்ப்புருக்களிலிருந்து தொகுக்கப்பட்டது; AI விளக்கம் உருவாக்கப்படவில்லை."),
    ]
    present = [p for p in pairs if p]
    return [p[0] for p in present], [p[1] for p in present]


_PHONE = re.compile(r"^\+?[\d\s-]{7,15}$")

_W_NOT_AUTH = ("The sender was not authenticated. This assessment evaluates the message, not who sent it.",
               "அனுப்புநர் உறுதிப்படுத்தப்படவில்லை. இந்த மதிப்பீடு செய்தியை மதிப்பிடுகிறது, அனுப்பியவரை அல்ல.")
_W_NONE = ("No sender was supplied. Sender-related checks were not performed.",
           "அனுப்புநர் வழங்கப்படவில்லை. அனுப்புநர் தொடர்பான சோதனைகள் செய்யப்படவில்லை.")
_W_PHONE = ("A phone number alone does not prove legitimacy.",
            "தொலைபேசி எண் மட்டும் நம்பகத்தன்மையை நிரூபிக்காது.")
_W_ID = ("Sender IDs can be spoofed or displayed misleadingly.",
         "அனுப்புநர் ஐடிகள் போலியாக்கப்படலாம் அல்லது தவறாகக் காட்டப்படலாம்.")
_W_OCR = ("This sender value was read from a screenshot and may contain extraction errors.",
          "இந்த அனுப்புநர் மதிப்பு திரைப்பிடிப்பிலிருந்து படிக்கப்பட்டது; பிழைகள் இருக்கலாம்.")


def sender_assessment(request: AnalyzeRequest) -> SenderAssessmentOut:
    sender = request.sender
    warnings = [_W_NOT_AUTH]
    if sender is None or not sender.value:
        warnings.append(_W_NONE)
        return SenderAssessmentOut(
            value_masked=None, kind="unknown", provenance="unavailable",
            warnings=[w[0] for w in warnings], warnings_ta=[w[1] for w in warnings],
        )
    value = sender.value.strip()
    if sender.kind == "phone_number" or _PHONE.match(value):
        digits = re.sub(r"\D", "", value)
        masked = ("+" if value.startswith("+") else "") + "*" * max(0, len(digits) - 4) + digits[-4:]
        warnings.append(_W_PHONE)
    elif sender.kind == "display_name":
        masked = value[:1] + "***"
    else:
        masked = value
        warnings.append(_W_ID)
    if sender.provenance in ("ocr", "user_corrected_ocr"):
        warnings.append(_W_OCR)
    return SenderAssessmentOut(
        value_masked=masked, kind=sender.kind, provenance=sender.provenance,
        warnings=[w[0] for w in warnings], warnings_ta=[w[1] for w in warnings],
    )
