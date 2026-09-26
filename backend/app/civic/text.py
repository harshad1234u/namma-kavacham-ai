"""Small language-agnostic text helpers shared by the civic services."""
import re
from typing import Literal

from pydantic import BaseModel

from app.civic.schemes.schema import LangText, norm

TextStatus = Literal["authored", "machine_translated", "english_fallback"]


class LocText(BaseModel):
    """Text in the requested language when we have it; otherwise the English original, labelled as such."""

    text: str
    lang: str
    status: TextStatus


def localize(lt: LangText, lang: str) -> LocText:
    if lang in lt:
        return LocText(text=lt[lang], lang=lang, status="authored")
    return LocText(text=lt["en"], lang="en", status="english_fallback" if lang != "en" else "authored")


def term_pattern(term: str) -> re.Pattern[str]:
    """ASCII terms match on word boundaries; Indic/other-script terms as substrings (no reliable boundary)."""
    t = re.escape(norm(term))
    if term.isascii():
        return re.compile(rf"(?<![a-z0-9]){t}(?![a-z0-9])")
    return re.compile(t)


_AMOUNT = re.compile(
    r"(?:₹|\brs\.?|\binr\b|rupees?|रु\.?|रुपये)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(lakh|lakhs|lac|lacs|crore|लाख|करोड़)?"
    r"|([0-9][0-9,]*(?:\.[0-9]+)?)\s*(lakh|lakhs|lac|lacs|crore|लाख|करोड़)"
    r"|([0-9][0-9,]*)\s*(?:/-|rupees|रुपये|ரூபாய்)",
    re.IGNORECASE,
)
_MULT = {"lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000, "लाख": 100_000, "crore": 10_000_000, "करोड़": 10_000_000}


def amounts_inr(text: str) -> set[int]:
    """Rupee amounts written with a currency marker or a lakh/crore unit. Bare numbers are ignored."""
    found: set[int] = set()
    for m in _AMOUNT.finditer(text):
        num = m.group(1) or m.group(3) or m.group(5)
        unit = (m.group(2) or m.group(4) or "").lower()
        try:
            value = float(num.replace(",", ""))
        except ValueError:
            continue
        found.add(round(value * _MULT.get(unit, 1)))
    found.discard(0)
    return found


_PERIODS = {
    "per_year": r"per\s*year|per\s*annum|a\s*year|every\s*year|each\s*year|yearly|annually|annual|/\s*year|saal|salana|सालाना|प्रति\s*वर्ष|हर\s*साल|वार्षिक|ஆண்டுக்கு|ஆண்டுதோறும்|வருடத்திற்கு",
    "per_month": r"per\s*month|a\s*month|every\s*month|monthly|/\s*month|mahina|mahine|मासिक|प्रति\s*माह|हर\s*महीने|महीना|மாதம்|மாதந்தோறும்",
    "per_day": r"per\s*day|a\s*day|daily|every\s*day|प्रति\s*दिन|रोज़?|தினமும்|நாளுக்கு",
    "per_instalment": r"per\s*install?ment|each\s*install?ment|every\s*install?ment|install?ment|kist|किस्त|தவணை",
}
_PERIOD_RE = {k: re.compile(v, re.I) for k, v in _PERIODS.items()}


def amounts_with_period(text: str) -> list[tuple[int, str | None]]:
    """Each claimed rupee amount with the period stated right after it (within ~30 chars), if any."""
    out = []
    for m in _AMOUNT.finditer(text):
        num = m.group(1) or m.group(3) or m.group(5)
        unit = (m.group(2) or m.group(4) or "").lower()
        try:
            amount = round(float(num.replace(",", "")) * _MULT.get(unit, 1))
        except ValueError:
            continue
        tail, head = text[m.end():m.end() + 30], text[max(0, m.start() - 25):m.start()]
        # English usually states the period after the amount; Hindi/Tamil often before it ("हर साल ₹10,000").
        period = next((k for k, rx in _PERIOD_RE.items() if rx.search(tail)), None) or             next((k for k, rx in _PERIOD_RE.items() if rx.search(head)), None)
        if amount:
            out.append((amount, period))
    return out


def inr(amount: int) -> str:
    """Indian digit grouping: 1000000 -> ₹10,00,000."""
    s = str(amount)
    if len(s) <= 3:
        return f"₹{s}"
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return "₹" + ",".join([head, *groups, tail] if head else [*groups, tail])
