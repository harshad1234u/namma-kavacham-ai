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
