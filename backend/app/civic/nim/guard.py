"""Safety layer around every NIM call: PII minimisation in, grounding validation out."""
import re
import unicodedata

from app.civic.languages import get_language, script_profile

CANARY = "CI-NIM-3B7E"

# ---------- PII minimisation (applied before any citizen text leaves the server) ----------
_PII = [
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("pan", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I)),
    ("aadhaar", re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)")),
    ("phone", re.compile(r"(?<!\d)(?:\+?91[ -]?|0)?[6-9]\d{4}[ -]?\d{5}(?!\d)")),
    ("otp", re.compile(r"(?i)(?:otp|pin|code|ओटीपी|பின்)\D{0,12}(\d{4,8})")),
    ("upi", re.compile(r"\b[\w.-]{2,}@(?:ok\w+|ybl|paytm|upi|apl|ibl|axl|sbi|icici|hdfcbank)\b", re.I)),
]


def minimise_pii(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for kind, pat in _PII:
        text, n = pat.subn(f"[{kind}]", text)
        if n:
            counts[kind] = n
    return text, counts


# ---------- grounding helpers ----------
_URL = re.compile(r"https?://[^\s<>\"')\]]+|\b(?:[a-z0-9-]+\.)+(?:gov\.in|nic\.in|in|com|org|net)\b", re.I)


def ascii_digits(text: str) -> str:
    """Indian-script digits (०-९, ০-৯, ௦-௯ ...) -> ASCII, so numbers compare across scripts."""
    return "".join(str(unicodedata.digit(ch)) if ch.isdigit() and not ch.isascii() else ch for ch in text)


def numbers(text: str) -> set[str]:
    return {n.replace(",", "").lstrip("0") or "0" for n in re.findall(r"\d[\d,]*(?:\.\d+)?", ascii_digits(text))}


def urls(text: str) -> set[str]:
    return {u.lower().rstrip("./") for u in _URL.findall(text)}


def ungrounded(output: str, evidence: str, secret: str = "") -> list[str]:
    """Reasons an AI output is not grounded in the evidence it was given (empty list = acceptable)."""
    problems = []
    if CANARY in output:
        problems.append("canary_leak")
    if secret and secret in output:
        problems.append("secret_leak")
    extra_numbers = numbers(output) - numbers(evidence)
    if extra_numbers:
        problems.append("invented_numbers")
    ev_urls = urls(evidence)
    if any(u not in ev_urls and not any(u in e or e in u for e in ev_urls) for u in urls(output)):
        problems.append("invented_urls")
    return problems


def wrong_script(output: str, lang: str) -> bool:
    """True when the output is not mainly in the requested language's script (English/Latin always allowed for 'en')."""
    language = get_language(lang)
    if language is None or lang == "en":
        return False
    profile = script_profile(output)
    return not profile or max(profile, key=profile.get) != language.script


def missing_protected(source: str, translated: str, protected: list[str]) -> list[str]:
    """Tokens that must survive translation unchanged: numbers, URLs/domains and given names/ids."""
    lost = [f"number:{n}" for n in numbers(source) - numbers(translated)]
    lost += [f"url:{u}" for u in urls(source) - urls(translated)]
    lost += [f"term:{t}" for t in protected if t in source and t not in translated]
    return lost


def delimit(tag: str, content: str) -> str:
    """Wrap untrusted content; any attempt to close the tag early is neutralised."""
    safe = content.replace(f"</{tag}>", "").replace(f"<{tag}>", "")
    return f"<{tag}>\n{safe}\n</{tag}>"
