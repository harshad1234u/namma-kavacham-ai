"""Deterministic extraction of need tags and self-described profile facts from citizen text.

Covers English, Hindi, Tamil and common romanised forms. Anything it cannot read stays unknown -
it never guesses a value. The LLM layer (when enabled) can add tags for other languages, but only
from the same closed vocabularies, and the citizen can always edit what was extracted.
"""
import re
from dataclasses import dataclass, field

from app.civic.schemes.schema import norm
from app.civic.text import term_pattern

_NEED_TERMS: dict[str, tuple[str, ...]] = {
    "farming_income_support": ("farmer", "farming", "kisan", "agriculture", "किसान", "खेती", "कृषि", "விவசாய", "விவசாயி"),
    "crop_insurance": ("crop insurance", "crop loss", "फसल बीमा", "பயிர் காப்பீடு"),
    "health_insurance": ("health insurance", "hospital", "treatment", "medical", "इलाज", "अस्पताल", "स्वास्थ्य बीमा", "மருத்துவ", "மருத்துவமனை"),
    "housing": ("house", "housing", "home", "shelter", "ghar", "makan", "घर", "मकान", "आवास", "வீடு", "veedu"),
    "cooking_fuel": ("lpg", "gas connection", "cooking gas", "gas cylinder", "chulha", "गैस", "सिलेंडर", "எரிவாயு", "சிலிண்டர்"),
    "employment": ("job", "employment", "work", "naukri", "rozgar", "रोजगार", "नौकरी", "काम", "வேலை", "velai"),
    "education_scholarship": ("scholarship", "study", "studies", "college", "school fees", "छात्रवृत्ति", "पढ़ाई", "உதவித்தொகை", "படிப்பு"),
    "pension_old_age": ("pension", "retirement", "old age", "पेंशन", "बुढ़ापा", "ஓய்வூதிய"),
    "insurance_life_accident": ("life insurance", "accident insurance", "insurance", "bima", "बीमा", "காப்பீடு"),
    "small_business_loan": ("loan", "business", "shop", "credit", "karz", "लोन", "कर्ज", "ऋण", "व्यवसाय", "कारोबार", "கடன்", "தொழில்"),
    "street_vendor_credit": ("street vendor", "hawker", "vendor", "thela", "ठेला", "रेहड़ी", "फेरीवाला", "தெரு வியாபாரி"),
    "artisan_support": ("artisan", "craft", "carpenter", "blacksmith", "potter", "tailor", "barber", "goldsmith", "mason", "cobbler", "कारीगर", "बढ़ई", "दर्जी", "कुम्हार", "கைவினை", "தச்சர்"),
    "banking_access": ("bank account", "open account", "बैंक खाता", "வங்கிக் கணக்கு"),
    "drinking_water": ("drinking water", "पीने का पानी", "குடிநீர்"),
    "maternity_support": ("pregnant", "pregnancy", "maternity", "गर्भवती", "கர்ப்ப"),
    "girl_child_savings": ("girl child", "daughter", "बेटी", "மகள்"),
    "skill_training": ("training", "skill", "प्रशिक्षण", "कौशल", "பயிற்சி"),
}

_OCCUPATION_TERMS: dict[str, tuple[str, ...]] = {
    "farmer": ("farmer", "kisan", "किसान", "விவசாயி"),
    "student": ("student", "छात्र", "छात्रा", "विद्यार्थी", "மாணவ"),
    "street_vendor": ("street vendor", "hawker", "thela", "ठेला", "रेहड़ी", "फेरीवाला", "தெரு வியாபாரி"),
    "artisan": ("artisan", "carpenter", "blacksmith", "potter", "goldsmith", "cobbler", "कारीगर", "बढ़ई", "कुम्हार", "கைவினைஞர்", "தச்சர்"),
    "unemployed": ("unemployed", "no job", "बेरोजगार", "வேலையில்லா"),
}
_GENDER_TERMS: dict[str, tuple[str, ...]] = {
    "female": ("woman", "women", "female", "lady", "widow", "mahila", "महिला", "औरत", "विधवा", "பெண்"),
    "male": ("man", "male", "पुरुष", "ஆண்"),
}
_RESIDENCE_TERMS: dict[str, tuple[str, ...]] = {
    "rural": ("village", "rural", "gaon", "gram panchayat", "गांव", "गाँव", "ग्रामीण", "கிராம"),
    "urban": ("city", "urban", "town", "शहर", "शहरी", "நகர"),
}
_AGE = re.compile(r"(?:age[d]?\s*(?:is\s*)?|उम्र\s*|वयस\s*)?(\d{1,3})\s*(?:years?|yrs?|वर्ष|साल|வயது)")


def _compile(table: dict[str, tuple[str, ...]]) -> list[tuple[str, re.Pattern[str]]]:
    return [(key, term_pattern(term)) for key, terms in table.items() for term in terms]


_NEED_P, _OCC_P, _GEN_P, _RES_P = map(_compile, (_NEED_TERMS, _OCCUPATION_TERMS, _GENDER_TERMS, _RESIDENCE_TERMS))


@dataclass
class Extraction:
    need_tags: list[str] = field(default_factory=list)
    profile: dict[str, object] = field(default_factory=dict)


def _first(patterns: list[tuple[str, re.Pattern[str]]], t: str) -> str | None:
    hits = {key for key, p in patterns if p.search(t)}
    return next(iter(hits)) if len(hits) == 1 else None  # ambiguous -> unknown


def extract(text: str) -> Extraction:
    t = norm(text)
    tags = sorted({key for key, p in _NEED_P if p.search(t)})
    # "insurance" alone also fires on "crop/health insurance"; keep only the specific tag then.
    if {"crop_insurance", "health_insurance"} & set(tags):
        tags = [x for x in tags if x != "insurance_life_accident"]
    profile: dict[str, object] = {}
    for attr, patterns in (("occupation", _OCC_P), ("gender", _GEN_P), ("residence_type", _RES_P)):
        if (value := _first(patterns, t)) is not None:
            profile[attr] = value
    if m := _AGE.search(t):
        age = int(m.group(1))
        if 0 < age < 120:
            profile["age"] = age
    return Extraction(tags, profile)
