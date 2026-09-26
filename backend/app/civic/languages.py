"""Registry of India's 22 Scheduled Languages (+ English) and script-based language hints.

Support is per capability and never overstated: a language is `machine` (AI-generated, unreviewed)
or `none` (English fallback) until someone adds a review record. Script detection only narrows the
candidates; it never claims to tell Hindi from Marathi (both Devanagari) - the LLM layer disambiguates.
"""
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

LANGUAGES_PATH = Path(__file__).resolve().parents[1] / "data" / "civic" / "languages.json"

SupportStatus = Literal["authored", "reviewed", "machine", "none"]

# Unicode blocks per script (start, end inclusive).
_SCRIPT_RANGES: dict[str, tuple[tuple[int, int], ...]] = {
    "devanagari": ((0x0900, 0x097F), (0xA8E0, 0xA8FF)),
    "bengali": ((0x0980, 0x09FF),),
    "gurmukhi": ((0x0A00, 0x0A7F),),
    "gujarati": ((0x0A80, 0x0AFF),),
    "odia": ((0x0B00, 0x0B7F),),
    "tamil": ((0x0B80, 0x0BFF),),
    "telugu": ((0x0C00, 0x0C7F),),
    "kannada": ((0x0C80, 0x0CFF),),
    "malayalam": ((0x0D00, 0x0D7F),),
    "arabic": ((0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)),
    "ol_chiki": ((0x1C50, 0x1C7F),),
    "meetei_mayek": ((0xAAE0, 0xAAFF), (0xABC0, 0xABFF)),
    "latin": ((0x0041, 0x005A), (0x0061, 0x007A), (0x00C0, 0x024F)),
}
_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_MIXED_SHARE = 0.15  # a second script above this share makes the text "mixed"


class LanguageSupport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ui: SupportStatus
    query_understanding: SupportStatus
    kb_text: SupportStatus


class Language(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    code: str
    name: str
    native_name: str
    script: str
    dir: Literal["ltr", "rtl"]
    scheduled: bool
    tier: Literal[1, 2, 3]
    support: LanguageSupport


class LanguageRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: str
    note: str
    languages: list[Language]


@lru_cache
def load_languages() -> LanguageRegistry:
    reg = LanguageRegistry.model_validate(json.loads(LANGUAGES_PATH.read_text(encoding="utf-8")))
    codes = [lang.code for lang in reg.languages]
    if len(codes) != len(set(codes)):
        raise ValueError("duplicate language code")
    if sum(lang.scheduled for lang in reg.languages) != 22:
        raise ValueError("registry must contain exactly the 22 Scheduled Languages")
    return reg


def get_language(code: str) -> Language | None:
    return next((lang for lang in load_languages().languages if lang.code == code), None)


def normalize_code(code: str | None) -> str:
    """Unknown or missing codes fall back to English; never raises."""
    return code if code and get_language(code) else "en"


def _script_of(ch: str) -> str | None:
    cp = ord(ch)
    for script, ranges in _SCRIPT_RANGES.items():
        if any(lo <= cp <= hi for lo, hi in ranges):
            return script
    return None


def script_profile(text: str) -> dict[str, float]:
    """Share of letters per script (URLs, digits, punctuation, emoji ignored)."""
    counts: dict[str, int] = {}
    for ch in _URL.sub(" ", text):
        if ch.isalpha():
            script = _script_of(ch)
            if script:
                counts[script] = counts.get(script, 0) + 1
    total = sum(counts.values())
    return {s: n / total for s, n in counts.items()} if total else {}


@dataclass(frozen=True)
class ScriptGuess:
    script: str | None  # dominant script, None when no letters
    candidates: tuple[str, ...]  # language codes written in that script
    confidence: Literal["high", "low", "none"]  # high only when exactly one language uses the script
    mixed: bool


def guess_from_script(text: str) -> ScriptGuess:
    profile = script_profile(text)
    if not profile:
        return ScriptGuess(None, (), "none", False)
    dominant = max(profile, key=profile.get)
    mixed = any(share >= _MIXED_SHARE for s, share in profile.items() if s != dominant)
    if dominant == "latin":
        # Latin can be English or romanized Indic text (Hinglish, Tanglish); scripts cannot tell.
        return ScriptGuess("latin", ("en",), "low", mixed)
    candidates = tuple(lang.code for lang in load_languages().languages if lang.script == dominant)
    return ScriptGuess(dominant, candidates, "high" if len(candidates) == 1 else "low", mixed)
