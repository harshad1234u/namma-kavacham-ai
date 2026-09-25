"""Deterministic, bilingual (English / Tamil / Tanglish) message-risk rules.

These rules are the fallback that must work when every external service is
down. Each rule returns at most one hit. Advisory phrasing such as "never share
your OTP" is excluded via a negation window so safety tips are not flagged.
"""

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

Confidence = Literal["low", "medium", "high"]

_EXCERPT_RADIUS = 40
_NEGATION_BEFORE = re.compile(
    r"(never|don'?t|do not|doesn'?t|does not|won'?t|will not|not|no one|nobody|avoid|beware)\W+(\w+\W+){0,4}$"
)
# The -ாதீர்கள் / -ாதீங்க / -ாதே forms are negative imperatives glued to the matched verb ("சொல்லாதீங்க" =
# "don't tell"). They are anchored with ^, so they only count directly after the verb, never later in the
# sentence ("பகிருங்கள், யாரிடமும் சொல்லாதீர்கள்" stays a scam request).
_NEGATION_AFTER_TA = re.compile(
    r"^\S*\s*(\S+\s+){0,2}(வேண்டாம்|கூடாது|மாட்டோம்|மாட்டார்கள்|கேட்காது|கேட்பதில்லை)|^(ாதீர்கள்|ாதீங்க|ாதீர்|ாதே)"
)
# Tanglish "don't do it" must directly follow the matched verb ("share pannatheenga"); a looser
# window would also swallow the classic scam line "OTP share pannunga, yaarukkum sollatheenga".
_NEGATION_AFTER_TANGLISH = re.compile(
    r"^\s+(pannatheenga|pannadheenga|pannaadheenga|pannaatheenga|panna venaam|panna vendaam|seiyatheenga)\b"
)
_PHONE_IN_EXCERPT = re.compile(r"(?<![\d])(\+?91[\s-]?)?[6-9](?:[\s-]?[\dx]){9}(?![\d])")


@dataclass(frozen=True)
class RuleHit:
    rule_id: str
    signal: str
    confidence: Confidence
    matched_text: str
    description_en: str
    description_ta: str


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    text = text.replace("​", "").replace("‌", "").replace("‍", "")
    return re.sub(r"\s+", " ", text).strip().lower()


def _mask_phone(match: re.Match[str]) -> str:
    digits = re.sub(r"[^\dx]", "", match.group(0).removeprefix("+"))
    return "******" + digits[-4:]


def _mask_phones(excerpt: str) -> str:
    return _PHONE_IN_EXCERPT.sub(_mask_phone, excerpt)


def _excerpt(text: str, match: re.Match[str]) -> str:
    start = max(0, match.start() - _EXCERPT_RADIUS // 2)
    end = min(len(text), match.end() + _EXCERPT_RADIUS // 2)
    # Snap to whole words so excerpts never begin or end mid-token.
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    while end < len(text) and not text[end].isspace():
        end += 1
    snippet = text[start:end].strip()
    if len(snippet) > 80:
        snippet = snippet[:77] + "..."
    return _mask_phones(snippet)


def _is_negated(text: str, match: re.Match[str]) -> bool:
    before = text[max(0, match.start() - 40): match.start()]
    after = text[match.end(): match.end() + 30]
    return bool(
        _NEGATION_BEFORE.search(before) or _NEGATION_AFTER_TA.search(after) or _NEGATION_AFTER_TANGLISH.search(after)
    )


def _first_affirmative(patterns: list[re.Pattern[str]], text: str) -> re.Match[str] | None:
    for pattern in patterns:
        for match in pattern.finditer(text):
            if not _is_negated(text, match):
                return match
    return None


def _c(*patterns: str) -> list[re.Pattern[str]]:
    return [re.compile(p) for p in patterns]


# ---- rule: OTP / PIN / password request ----
_CREDENTIAL_PATTERNS = _c(
    r"\b(share|send|tell|enter|provide|forward|give|confirm|type|reply with|submit|read out)\b[^.!?\n]{0,40}"
    r"\b(otp|one[- ]time password|upi pin|m-?pin|atm pin|pin|password|passcode|cvv|verification code)\b",
    r"\b(otp|upi pin|m-?pin|password|cvv|verification code)\b[^.!?\n]{0,30}\b(share|send|tell|forward|reply|sollunga|anuppunga|kudunga)\b",
    r"(otp|ஓடிபி|ஒடிபி|கடவுச்சொல்|பின் எண்|யுபிஐ பின்)[^.!?\n]{0,30}?(பகிர|அனுப்ப|சொல்ல|தெரிவி|கொடு|பதிவிடு)",
    r"\botp\b[^.!?\n]{0,15}\b(share pannunga|sollunga|anuppunga|kodunga|sollu|anuppu)\b",
)


def rule_credential_request(text: str) -> RuleHit | None:
    match = _first_affirmative(_CREDENTIAL_PATTERNS, text)
    if not match:
        return None
    return RuleHit(
        "MSG-CRED-01", "credential_request", "high", _excerpt(text, match),
        "The message asks you to share or enter an OTP, PIN, password, or verification code. "
        "Banks and government services do not ask for these over SMS, calls, or chat.",
        "செய்தி OTP, PIN, கடவுச்சொல் அல்லது சரிபார்ப்புக் குறியீட்டைப் பகிரக் கேட்கிறது. வங்கிகளும் அரசுச் "
        "சேவைகளும் இவற்றை SMS, அழைப்பு அல்லது அரட்டை மூலம் கேட்பதில்லை.",
    )


# ---- rule: payment / fee request ----
_UPI_ID = r"\b[\w.-]{2,}@(upi|ybl|okaxis|oksbi|okhdfcbank|okicici|paytm|ibl|axl|apl|fbl|kotak|icici|sbi)\b(?!\.[a-z])"  # not an email such as x@sbi.co.in
_FEE_PATTERNS = _c(
    r"\b(processing|activation|registration|verification|release|unfreeze|unblock|service|convenience|"
    r"clearance|handling|kyc|refund|reactivation|approval)\s+(fee|fees|charge|charges|amount)\b",
    r"\b(pay|transfer|deposit|send)\b[^.!?\n]{0,40}(₹|\brs\.?\s?\d|\binr\b|\brupees\b)[^.!?\n]{0,40}"
    r"\b(to|for)\s+(activate|release|unblock|unfreeze|receive|claim|process|restore|avoid)",
    _UPI_ID,
    # "ரூ.100" contains a period, so the amount is matched explicitly before the sentence-bounded gap.
    r"(கட்டணம்|செயலாக்கக் கட்டணம்|பதிவுக் கட்டணம்)\s*(ரூ\.?\s?\d[\d,]*)?[^.!?\n]{0,30}?(செலுத்த|கட்ட|அனுப்ப)",
)
_PAY_PATTERNS = _c(
    r"\b(pay|payment|transfer|deposit|remit|send money)\b[^.!?\n]{0,40}(₹|\brs\.?\s?\d|\binr\b|\brupees\b|\bamount\b|\bbill\b)",
    r"(₹|\brs\.?\s?)\s?\d[\d,]*[^.!?\n]{0,30}\b(pay|transfer|deposit)\b",
    r"\b(immediately|urgently|now|today)\s+(pay|make (the )?payment|transfer)\b",
    r"\b(pay|make (the )?payment)\s+(immediately|urgently|now|today|at once)\b",
    r"(பணம்|தொகை|₹|ரூ\.?\s?\d[\d,]*)[^.!?\n]{0,30}?(செலுத்த|அனுப்ப|கட்ட)",
    r"\b(pay pannunga|panam anuppunga|kattunga)\b",
    r"\b(fee|fees|charge|amount|rupees|rs)\b[^.!?\n]{0,30}\b(anuppunga|kattunga|pay pannunga)\b",
)


def rule_payment_request(text: str) -> RuleHit | None:
    match = _first_affirmative(_FEE_PATTERNS, text)
    confidence: Confidence = "high"
    if not match:
        match = _first_affirmative(_PAY_PATTERNS, text)
        confidence = "medium"
    if not match:
        return None
    return RuleHit(
        "MSG-PAY-01", "payment_or_fee_request", confidence, _excerpt(text, match),
        "The message asks for a payment, fee, or transfer. Government benefits are not released "
        "by paying a fee to a link, UPI ID, or phone number from a message."
        if confidence == "high" else
        "The message asks you to make a payment. Verify any payment request through the official "
        "app or website you open yourself.",
        "செய்தி கட்டணம் அல்லது பணப் பரிமாற்றத்தைக் கேட்கிறது. அரசு நலத்திட்டங்கள் செய்தியில் உள்ள இணைப்பு, "
        "UPI ஐடி அல்லது தொலைபேசி எண்ணுக்குப் பணம் செலுத்துவதன் மூலம் வழங்கப்படுவதில்லை."
        if confidence == "high" else
        "செய்தி பணம் செலுத்தக் கேட்கிறது. நீங்களே திறக்கும் அதிகாரப்பூர்வ செயலி அல்லது இணையதளம் மூலம் சரிபார்க்கவும்.",
    )


# ---- rule: urgency / threat language ----
_DEADLINE_PATTERNS = _c(
    r"\b(immediately|urgent(ly)?|right now|asap|at the earliest)\b",
    r"\bwithin\s+\d+\s*(hours?|hrs?|minutes?|mins?|days?)\b",
    r"\b(today|tonight|by \d{1,2}(:\d{2})?\s*(am|pm)|before \d{1,2}(:\d{2})?\s*(am|pm)|last (date|chance|day|warning))\b",
    r"(உடனடியாக|உடனே|இன்று இரவு|இன்றே|இன்று மாலை|கடைசி நாள்|கடைசி வாய்ப்பு)",
    r"\b(udane|inniku night|innaikke)\b",
)
_CONSEQUENCE_PATTERNS = _c(
    r"\bwill be (blocked|suspended|disconnected|deactivated|cancelled|canceled|closed|frozen|terminated|seized|cut)\b",
    r"\b(account|card|sim|connection|aadhaar|pan)\b[^.!?\n]{0,20}\b(blocked|suspended|deactivated|frozen)\b",
    r"\b(legal action|arrest|warrant|police case|fir\b|penalty|court notice|digital arrest|cbi|narcotics)",
    r"(முடக்கப்படும்|நிறுத்தப்படும்|துண்டிக்கப்படும்|ரத்து செய்யப்படும்|இடைநிறுத்தப்படும்|கைது|அபராதம்|சட்ட நடவடிக்கை)",
    # Tanglish ("account block aagidum"). Scoped to a service subject so everyday "class cancel aagidum"
    # does not match; "aagum" is left out because it is too common in ordinary chat.
    r"\b(account|card|sim|connection|aadhaar|aadhar|pan|number|pension|kyc|eb|current|power|gas|loan|upi|bank|"
    r"salary|subsidy|benefit)\b[^.!?\n]{0,20}?\b(block|suspend|cancel|cut|disconnect|deactivate|close|stop|freeze|"
    r"expire|terminate)\w*\s+(aagidum|aayidum|agidum|ayidum|aaidum|panniduvom|pannuvom|pannidurom)\b",
)


def rule_urgency(text: str) -> RuleHit | None:
    deadline = _first_affirmative(_DEADLINE_PATTERNS, text)
    consequence = _first_affirmative(_CONSEQUENCE_PATTERNS, text)
    match = consequence or deadline
    if not match:
        return None
    both = bool(deadline and consequence)
    return RuleHit(
        "MSG-URG-01", "urgency_or_threat_language", "high" if both else "medium", _excerpt(text, match),
        "The message uses pressure — a short deadline and/or a threat of suspension, disconnection, "
        "penalty, or arrest. Pressure tactics are used to stop you from checking first.",
        "செய்தி அவசரத்தையும் அச்சுறுத்தலையும் (காலக்கெடு, முடக்கம், துண்டிப்பு, அபராதம் அல்லது கைது) "
        "பயன்படுத்துகிறது. முதலில் சரிபார்ப்பதைத் தடுக்கவே இத்தகைய அழுத்தம் பயன்படுத்தப்படுகிறது.",
    )


# ---- rule: APK / app install instruction ----
_APK_PATTERNS = _c(
    r"\.(apk|xapk|apks)\b",
    r"\b(download|install|update|open)\b[^.!?\n]{0,30}\b(app|application|apk|software)\b[^.!?\n]{0,30}"
    r"\b(link|below|given|from|at|http|www)\b",
    r"(செயலியை|ஆப்|அப்ளிகேஷன்)[^.!?\n]{0,20}?(பதிவிறக்க|நிறுவ|இன்ஸ்டால்|டவுன்லோட்)",
    r"\b(apk|app)\b[^.!?\n]{0,15}\b(install pannunga|download pannunga)\b",
)


def rule_apk_install(text: str) -> RuleHit | None:
    match = _first_affirmative(_APK_PATTERNS, text)
    if not match:
        return None
    return RuleHit(
        "MSG-APK-01", "apk_install_instruction", "high", _excerpt(text, match),
        "The message asks you to download or install an app from a link. Apps sent through "
        "messages can read your SMS/OTPs and take control of your phone. Install apps only from the "
        "official app store.",
        "செய்தி இணைப்பிலிருந்து செயலியைப் பதிவிறக்க/நிறுவக் கேட்கிறது. இத்தகைய செயலிகள் உங்கள் SMS/OTP-களைப் "
        "படித்து தொலைபேசியைக் கட்டுப்படுத்தலாம். அதிகாரப்பூர்வ ஆப் ஸ்டோரிலிருந்து மட்டுமே நிறுவவும்.",
    )


# ---- rule: remote-access app request ----
_REMOTE_PATTERNS = _c(r"\b(anydesk|teamviewer|quick ?support|rustdesk|airdroid|screen ?share|screen sharing)\b")


def rule_remote_access(text: str) -> RuleHit | None:
    match = _first_affirmative(_REMOTE_PATTERNS, text)
    if not match:
        return None
    return RuleHit(
        "MSG-REMOTE-01", "remote_access_app_request", "high", _excerpt(text, match),
        "The message mentions a screen-sharing or remote-access app. Government and bank staff do "
        "not need remote access to your phone.",
        "செய்தி திரைப் பகிர்வு / தொலை அணுகல் செயலியைக் குறிப்பிடுகிறது. அரசு மற்றும் வங்கி ஊழியர்களுக்கு உங்கள் "
        "தொலைபேசியின் தொலை அணுகல் தேவையில்லை.",
    )


# ---- rule: government / identity-service impersonation phrasing ----
_SERVICE = (r"(aadhaar|aadhar|pan card|\bpan\b|passport|kyc|ration card|voter id|electricity|\beb\b|tneb|"
            r"tangedco|pm[- ]?kisan|income tax|it department|\bepf\b|\bpf\b|gas connection|sim card|\bsim\b)")
_IMPERSONATION_HIGH = _c(
    _SERVICE + r"[^.!?\n]{0,40}\b(will be|has been|is|are|shall be)?\s?(blocked|suspended|deactivated|cancelled|"
    r"canceled|disconnected|frozen|terminated|expired|invalid|closed)\b",
    r"(ஆதார்|பான்|பாஸ்போர்ட்|மின் இணைப்பு|மின்சாரம்|ரேஷன்|சிம்)[^.!?\n]{0,30}"
    r"(முடக்கப்படும்|நிறுத்தப்படும்|ரத்து|இடைநிறுத்தப்படும்|துண்டிக்கப்படும்|காலாவதி)",
)
_IMPERSONATION_MEDIUM = _c(
    r"\b(dear (beneficiary|farmer|citizen|taxpayer|customer|consumer)|from (the )?(govt|government|ministry|"
    r"department|uidai|income tax department|electricity board))\b",
    r"\b(scheme|subsidy|benefit|installment|instalment|refund|dbt|pension|scholarship)\b[^.!?\n]{0,40}"
    r"\b(pending|on hold|approved|credited|release|blocked|stuck)\b",
    r"\b(update|verify|link|complete)\b[^.!?\n]{0,20}" + _SERVICE,
    r"(திட்டம்|மானியம்|உதவித்தொகை|நிலுவை|தவணை|ஓய்வூதியம்)[^.!?\n]{0,30}?(நிறுத்த|நிலுவையில்|வெளியிட|தடைப்பட்)",
)


def rule_government_impersonation(text: str) -> RuleHit | None:
    match = _first_affirmative(_IMPERSONATION_HIGH, text)
    confidence: Confidence = "high"
    if not match:
        match = _first_affirmative(_IMPERSONATION_MEDIUM, text)
        confidence = "medium"
    if not match:
        return None
    return RuleHit(
        "MSG-GOVIMP-01", "government_impersonation_phrasing", confidence, _excerpt(text, match),
        "The message uses the name of a government or identity service (for example Aadhaar, PAN, "
        "electricity, a benefit scheme) to create authority. The sender's identity was not verified.",
        "அதிகாரத்தை உருவாக்க செய்தி அரசு அல்லது அடையாளச் சேவையின் பெயரை (ஆதார், பான், மின்சாரம், நலத்திட்டம் "
        "போன்றவை) பயன்படுத்துகிறது. அனுப்புநரின் அடையாளம் சரிபார்க்கப்படவில்லை.",
    )


# ---- rule: sensitive document / financial detail request ----
_DOCUMENT_PATTERNS = _c(
    r"\b(send|share|upload|provide|submit|whatsapp)\b[^.!?\n]{0,30}\b(aadhaar|aadhar|pan|bank details|account number|"
    r"ifsc|debit card|credit card|card number|card details|passbook|selfie|photo of)\b",
    r"(ஆதார்|பான்|வங்கி விவரங்கள்|கணக்கு எண்|அட்டை விவரங்கள்)[^.!?\n]{0,25}?(அனுப்ப|பகிர|பதிவேற்ற)",
)


def rule_sensitive_documents(text: str) -> RuleHit | None:
    match = _first_affirmative(_DOCUMENT_PATTERNS, text)
    if not match:
        return None
    return RuleHit(
        "MSG-DOC-01", "sensitive_document_request", "medium", _excerpt(text, match),
        "The message asks for identity documents or bank/card details. Share these only through an "
        "official portal or office you reach yourself.",
        "செய்தி அடையாள ஆவணங்கள் அல்லது வங்கி/அட்டை விவரங்களைக் கேட்கிறது. நீங்களே அணுகும் அதிகாரப்பூர்வ "
        "இணையதளம் அல்லது அலுவலகம் மூலம் மட்டுமே பகிரவும்.",
    )


# ---- rule: callback number inside the message body ----
_CALLBACK_PATTERNS = _c(
    r"\b(call|contact|whatsapp|dial|ring)\b[^.!?\n]{0,30}(\+?91[\s-]?)?[6-9]\d{4}[\s-]?[\dx]{5}",
    r"(அழைக்க|தொடர்பு கொள்ள|அழையுங்கள்)[^.!?\n]{0,30}(\+?91[\s-]?)?[6-9]\d{4}[\s-]?[\dx]{5}",
    # Tamil / Tanglish word order puts the verb after the number: "9876543210 அழைக்கவும்".
    r"(\+?91[\s-]?)?[6-9]\d{4}[\s-]?[\dx]{5}[^.!?\n]{0,20}?(அழைக்க|தொடர்பு கொள்ள|அழையுங்கள்|\bcall pannunga\b)",
)


def rule_callback_number(text: str) -> RuleHit | None:
    match = _first_affirmative(_CALLBACK_PATTERNS, text)
    if not match:
        return None
    return RuleHit(
        "MSG-CALLBK-01", "unverified_callback_number", "low", _excerpt(text, match),
        "The message asks you to call a mobile number it provides. A number inside a message is not "
        "verified and is not treated as the sender's identity — use the helpline on the official website.",
        "செய்தி அதில் உள்ள கைபேசி எண்ணை அழைக்கக் கேட்கிறது. செய்தியில் உள்ள எண் சரிபார்க்கப்பட்டதல்ல; அதிகாரப்பூர்வ "
        "இணையதளத்தில் உள்ள உதவி எண்ணைப் பயன்படுத்தவும்.",
    )


# Stricter negation for the scheme rules below: also rejects "no registration fee",
# "applications are not accepted on WhatsApp" and Tamil "...ஏற்கப்படாது".
_NEGATION_IN_SPAN = re.compile(r"n't\b|\b(not|never|no)\b")
_NO_BEFORE = re.compile(r"\b(no|zero|nil|without)\s+(\w+\s+){0,2}$")
_NEGATION_AFTER_TA_SUFFIX = re.compile(r"^[^.!?\n]{0,25}(படாது|இல்லை|வேண்டாம்|கூடாது|மாட்டோம்)")


def _first_clean(patterns: list[re.Pattern[str]], text: str) -> re.Match[str] | None:
    for pattern in patterns:
        for m in pattern.finditer(text):
            if (_is_negated(text, m) or _NEGATION_IN_SPAN.search(m.group(0))
                    or _NO_BEFORE.search(text[max(0, m.start() - 30): m.start()])
                    or _NEGATION_AFTER_TA_SUFFIX.search(text[m.end():])):
                continue
            return m
    return None


# ---- rule: payment to a UPI ID / mobile number, in a government, benefit or fee context ----
# A UPI ID alone is ordinary between friends, so this rule needs an official-sounding context.
_UPI_PAYMENT_PATTERNS = _c(
    _UPI_ID,
    r"\b(gpay|google pay|phonepe|phone pe|paytm|upi)\b[^.!?\n]{0,25}(\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}",
    r"(\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}[^.!?\n]{0,20}\b(gpay|google pay|phonepe|phone pe|paytm)\b",
    r"(ஜிபே|போன்பே|கூகுள் பே)[^.!?\n]{0,25}[6-9]\d{4}[\s-]?\d{5}",
)
_OFFICIAL_CONTEXT = re.compile(
    r"\b(govt|government|sarkar|sarkari|scheme|yojana|subsidy|benefit|scholarship|pension|ration|registration|"
    r"processing|activation|fee|fees|charges?|penalty|fine|kyc|refund|installment|instalment|department|ministry|"
    r"official|officer|pm[- ]?kisan|aadhaar|aadhar|electricity|eb bill)\b"
    r"|(அரசு|திட்ட|மானிய|கட்டண|உதவித்தொகை|ஓய்வூதிய|அபராத)"
)


def rule_personal_upi_payment(text: str) -> RuleHit | None:
    match = _first_clean(_UPI_PAYMENT_PATTERNS, text)
    if not match or not _OFFICIAL_CONTEXT.search(re.sub(_UPI_ID, " ", text)):
        return None
    return RuleHit(
        "MSG-UPI-01", "personal_upi_payment", "medium", _excerpt(text, match),
        "The message asks you to pay to a UPI ID or to a mobile number on a payment app. The money goes to "
        "whoever owns that ID, which may be a private person; nothing in the message shows it belongs to a "
        "government office. Pay any government fee only through the official website or app you open yourself.",
        "செய்தி ஒரு UPI ஐடிக்கோ, பணம் செலுத்தும் செயலியில் உள்ள கைபேசி எண்ணுக்கோ பணம் அனுப்பச் சொல்கிறது. அந்தப் "
        "பணம் அந்த ஐடியின் உரிமையாளருக்கே செல்லும்; அவர் ஒரு தனிநபராகவும் இருக்கலாம். அது அரசு அலுவலகத்துடையது "
        "என்பதற்கு செய்தியில் எந்த ஆதாரமும் இல்லை. அரசுக் கட்டணத்தை நீங்களே திறக்கும் அதிகாரப்பூர்வ இணையதளம் அல்லது "
        "செயலி மூலம் மட்டுமே செலுத்தவும்.",
    )


# ---- rule: apply / register through WhatsApp or Telegram ----
_CHAT = r"(whatsapp|whats app|telegram|wa\.me|t\.me|chat\.whatsapp\.com)"
_APPLY = r"(apply|applications?|register|registration|enrol|enroll|enrolment|enrollment|submit)"
_CHANNEL_PATTERNS = _c(
    rf"\b{_APPLY}\b[^.!?\n]{{0,40}}\b{_CHAT}",
    rf"\b{_CHAT}\b[^.!?\n]{{0,30}}\b({_APPLY}|apply pannunga|register pannunga)\b",
    r"\bjoin\b[^.!?\n]{0,20}\b(whatsapp|telegram)\s+(group|channel)\b[^.!?\n]{0,40}"
    r"\b(scheme|yojana|subsidy|benefit|scholarship|pension|loan|job|recruitment)\b",
    r"(வாட்ஸ்அப்|வாட்ஸ்ஆப்|டெலிகிராம்)[^.!?\n]{0,30}?(விண்ணப்ப|பதிவு செய்)",
    r"(விண்ணப்ப|பதிவு செய்)[^.!?\n]{0,30}?(வாட்ஸ்அப்|வாட்ஸ்ஆப்|டெலிகிராம்)",
)


def rule_unofficial_channel(text: str) -> RuleHit | None:
    match = _first_clean(_CHANNEL_PATTERNS, text)
    if not match:
        return None
    return RuleHit(
        "MSG-CHAN-01", "unofficial_channel_application", "medium", _excerpt(text, match),
        "The message asks you to apply or register through WhatsApp or Telegram. Anyone can open a chat "
        "account under a government name. Check how to apply on the official website you open yourself.",
        "செய்தி வாட்ஸ்அப் அல்லது டெலிகிராம் மூலம் விண்ணப்பிக்கவோ பதிவு செய்யவோ சொல்கிறது. அரசின் பெயரில் யார் "
        "வேண்டுமானாலும் அரட்டைக் கணக்கைத் தொடங்கலாம். விண்ணப்பிக்கும் முறையை நீங்களே திறக்கும் அதிகாரப்பூர்வ "
        "இணையதளத்தில் சரிபார்க்கவும்.",
    )


# ---- rule: a fee demanded for a benefit described as free ----
_BENEFIT = (r"(scheme|yojana|benefit|subsidy|laptop|tablet|smartphone|mobile|phone|cycle|bicycle|scooter|scooty|gas|"
            r"cylinder|lpg|ration|house|housing|scholarship|pension|loan|treatment|insurance|solar|pump|"
            r"sewing machine|recharge|electricity|training|coaching|kit|seeds|tractor|money|cash)")
_FREE_PATTERNS = _c(
    rf"\bfree( of cost| of charge)?\s+(\w+\s+){{0,2}}{_BENEFIT}",
    rf"\b{_BENEFIT}s?\b[^.!?\n]{{0,25}}\b(for free|free of cost|free of charge|at no cost|is free|are free)\b",
    r"இலவச",
    r"\b(ilavasa\w*|freeya)\b",
)
_FREE_FEE_PAYMENT = _FEE_PATTERNS + _PAY_PATTERNS + _c(
    r"\b(fee|fees|charge|charges)\b[^.!?\n]{0,20}(₹|\brs\.?\s?\d|\binr\b|\brupees\b)",
    r"(₹|\brs\.?\s?)\s?\d[\d,]*(/-)?\s+(\w+\s+)?(fee|fees|charge|charges)\b",
    r"\b(fees?|charges?|amount)\s+(kattunga|pay pannunga|anuppunga|kattanum)\b",
)


def rule_fee_for_free_benefit(text: str) -> RuleHit | None:
    if not _first_clean(_FREE_PATTERNS, text):
        return None
    match = _first_clean(_FREE_FEE_PAYMENT, text)
    if not match:
        return None
    return RuleHit(
        "MSG-FREEFEE-01", "fee_for_free_benefit", "medium", _excerpt(text, match),
        "The message calls a benefit free but asks you to pay a fee or charge to receive it. Asking for money "
        "to release a 'free' benefit is a common scam pattern. Confirm on the official website whether any fee "
        "applies.",
        "செய்தி ஒரு நலத்திட்டத்தை இலவசம் என்று கூறி, அதைப் பெறக் கட்டணம் செலுத்தச் சொல்கிறது. 'இலவச' நலத்திட்டத்தை "
        "வழங்கப் பணம் கேட்பது பொதுவான மோசடி முறை. ஏதேனும் கட்டணம் உண்டா என்பதை அதிகாரப்பூர்வ இணையதளத்தில் "
        "உறுதிசெய்யவும்.",
    )


RULES: tuple[Callable[[str], RuleHit | None], ...] = (
    rule_credential_request,
    rule_payment_request,
    rule_urgency,
    rule_apk_install,
    rule_remote_access,
    rule_government_impersonation,
    rule_sensitive_documents,
    rule_callback_number,
    rule_personal_upi_payment,
    rule_unofficial_channel,
    rule_fee_for_free_benefit,
)


def run_message_rules(text: str) -> list[RuleHit]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    return [hit for rule in RULES if (hit := rule(normalized)) is not None]
