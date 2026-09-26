"""Find which verified schemes a piece of text names (names, abbreviations, curated aliases)."""
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from app.civic.schemes.kb import load_scheme_kb
from app.civic.schemes.schema import norm
from app.civic.text import term_pattern

# Words that signal the text is about *some* government scheme, even when none of ours is named.
_SCHEME_WORDS = re.compile(
    r"(?<![a-z])(scheme|yojana|yojna|abhiyan|mission|subsidy|pension|scholarship|government benefit)(?![a-z])"
    r"|योजना|सब्सिडी|पेंशन|छात्रवृत्ति|திட்டம்|மானியம்|உதவித்தொகை|ওজনা|প্রকল্প|పథకం|ಯೋಜನೆ|പദ്ധതി|योजना|ଯୋଜନା|ਯੋਜਨਾ|યોજના|اسکیم|یوجنا"
)


@dataclass(frozen=True)
class SchemeMatch:
    scheme_id: str
    matched_term: str
    confidence: Literal["high", "medium"]


@lru_cache
def _patterns() -> list[tuple[str, str, re.Pattern[str], Literal["high", "medium"]]]:
    out = []
    for s in load_scheme_kb().schemes:
        for term in (*s.names.values(), *s.abbreviations):
            out.append((s.id, term, term_pattern(term), "high"))
        for term in s.aliases:
            out.append((s.id, term, term_pattern(term), "medium"))
    return out


def identify_schemes(text: str) -> list[SchemeMatch]:
    t = norm(text)
    best: dict[str, SchemeMatch] = {}
    for sid, term, pat, conf in _patterns():
        if pat.search(t) and (sid not in best or (conf == "high" and best[sid].confidence == "medium")):
            best[sid] = SchemeMatch(sid, term, conf)
    return list(best.values())


def mentions_a_scheme(text: str) -> bool:
    return bool(_SCHEME_WORDS.search(norm(text)))
