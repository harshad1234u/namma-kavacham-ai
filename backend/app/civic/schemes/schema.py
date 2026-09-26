"""Scheme knowledge base v2. Every citizen-facing statement is tied to a source and a verbatim quote."""
import re
import unicodedata
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.civic.languages import get_language
from app.civic.schemes.attributes import ATTRIBUTES, NEED_TAGS, OPERATORS

OFFICIAL_SUFFIXES = (".gov.in", ".nic.in")

LangText = dict[str, str]  # language code -> text; "en" is mandatory


def norm(s: str) -> str:
    """Whitespace-, case- and quote-style-insensitive form for comparing quotes with source text."""
    s = unicodedata.normalize("NFKC", s)
    s = s.translate({0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"', 0x2013: "-", 0x2014: "-"})
    return re.sub(r"\s+", " ", s).strip().lower()


def host_of(url: str) -> str:
    m = re.match(r"^https://([^/:?#]+)", url)
    if not m:
        raise ValueError(f"official URL must use https: {url}")
    return m.group(1).lower()


def is_official_host(host: str) -> bool:
    return host.endswith(OFFICIAL_SUFFIXES)


def check_lang_text(v: LangText) -> LangText:
    if not v.get("en", "").strip():
        raise ValueError("English text is required")
    for code, text in v.items():
        if get_language(code) is None:
            raise ValueError(f"unknown language code {code!r}")
        if not text.strip():
            raise ValueError(f"empty text for {code!r}")
    return v


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SchemeSource(_Strict):
    id: str
    publisher: str
    title: str
    url: str
    published: str | None = None
    retrieved: date
    quotes: list[str]

    @field_validator("url")
    @classmethod
    def _official(cls, v: str) -> str:
        if not is_official_host(host_of(v)):
            raise ValueError(f"source is not on an official government domain: {v}")
        return v

    @field_validator("quotes")
    @classmethod
    def _has_quotes(cls, v: list[str]) -> list[str]:
        if not v or any(not q.strip() for q in v):
            raise ValueError("a source must record at least one verbatim quote")
        return v


class Statement(_Strict):
    """A fact shown to citizens: text per language, where it comes from, and the supporting quote."""

    text: LangText
    source_ref: str
    quote: str

    @field_validator("text")
    @classmethod
    def _lang(cls, v: LangText) -> LangText:
        return check_lang_text(v)


class Benefit(Statement):
    amount_inr: int | None = None  # only when the source states the amount


class Criterion(_Strict):
    id: str
    attribute: str  # a key of ATTRIBUTES, or "other" (not machine-checkable)
    operator: str | None = None
    value: Any = None
    kind: Literal["inclusion", "exclusion"] = "inclusion"
    statement: Statement

    @model_validator(mode="after")
    def _shape(self) -> "Criterion":
        if self.attribute == "other":
            if self.operator is not None or self.value is not None:
                raise ValueError("'other' criteria cannot carry an operator or value")
            return self
        attr = ATTRIBUTES.get(self.attribute)
        if attr is None:
            raise ValueError(f"unknown attribute {self.attribute!r}")
        if self.operator not in OPERATORS:
            raise ValueError(f"unknown operator {self.operator!r}")
        if attr.type == "bool" and self.operator not in ("is_true", "is_false"):
            raise ValueError("bool attributes use is_true/is_false")
        if attr.type == "int":
            if self.operator not in ("gte", "lte", "between", "eq"):
                raise ValueError("int attributes use gte/lte/between/eq")
            vals = self.value if self.operator == "between" else [self.value]
            if self.operator == "between" and len(vals) != 2:
                raise ValueError("between needs [low, high]")
            if not all(isinstance(x, int) for x in vals):
                raise ValueError("int criteria need integer values")
        if attr.type == "enum":
            vals = self.value if isinstance(self.value, list) else [self.value]
            if self.operator not in ("eq", "in", "not_in") or any(x not in attr.values for x in vals):
                raise ValueError(f"invalid enum criterion for {self.attribute}")
        return self


class Document(_Strict):
    name: LangText
    statement: Statement

    @field_validator("name")
    @classmethod
    def _lang(cls, v: LangText) -> LangText:
        return check_lang_text(v)


class Channel(_Strict):
    type: Literal["online_portal", "offline_office", "common_service_centre", "bank", "post_office", "mobile_app"]
    label: LangText
    official_url: str | None = None  # None for offline channels
    source_ref: str

    @field_validator("label")
    @classmethod
    def _lang(cls, v: LangText) -> LangText:
        return check_lang_text(v)

    @field_validator("official_url")
    @classmethod
    def _official(cls, v: str | None) -> str | None:
        if v is not None and not is_official_host(host_of(v)):
            raise ValueError("application URL must be on an official .gov.in/.nic.in domain")
        return v


class Helpline(_Strict):
    number: str
    source_ref: str


class Scheme(_Strict):
    id: str
    names: LangText
    abbreviations: list[str] = []
    aliases: list[str] = []
    level: Literal["central", "state"]
    state: str | None = None
    ministry: str
    need_tags: list[str]
    description: Statement
    benefits: list[Benefit]
    eligibility: list[Criterion]
    criteria_complete: bool  # True only when the sources state the full eligibility rules
    documents: list[Document]
    application_steps: list[Statement]
    channels: list[Channel]
    helplines: list[Helpline] = []
    official_domains: list[str]
    sources: list[SchemeSource]
    last_verified: date

    @field_validator("names")
    @classmethod
    def _lang(cls, v: LangText) -> LangText:
        return check_lang_text(v)

    def statements(self) -> list[Statement]:
        return [
            self.description, *self.benefits, *self.application_steps,
            *(c.statement for c in self.eligibility), *(d.statement for d in self.documents),
        ]

    @model_validator(mode="after")
    def _consistent(self) -> "Scheme":
        if (self.level == "state") != bool(self.state):
            raise ValueError("state schemes need a state; central schemes must not have one")
        unknown = [t for t in self.need_tags if t not in NEED_TAGS]
        if unknown or not self.need_tags:
            raise ValueError(f"need_tags must be non-empty and known: {unknown}")
        if not self.official_domains or not all(is_official_host(d) for d in self.official_domains):
            raise ValueError("official_domains must be non-empty .gov.in/.nic.in domains")
        sources = {s.id: s for s in self.sources}
        if len(sources) != len(self.sources):
            raise ValueError("duplicate source id")
        for st in self.statements():
            src = sources.get(st.source_ref)
            if src is None:
                raise ValueError(f"unknown source_ref {st.source_ref!r}")
            if not any(norm(st.quote) in norm(q) for q in src.quotes):
                raise ValueError(f"quote not found in recorded quotes of {src.id}: {st.quote[:60]!r}")
        refs = [c.source_ref for c in self.channels] + [h.source_ref for h in self.helplines]
        if missing := [r for r in refs if r not in sources]:
            raise ValueError(f"unknown source_ref {missing}")
        for ch in self.channels:
            if ch.official_url:
                host = host_of(ch.official_url)
                if not any(host == d or host.endswith("." + d) for d in self.official_domains):
                    raise ValueError(f"channel host {host} is not one of the scheme's official_domains")
        ids = [c.id for c in self.eligibility]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate criterion id")
        if self.criteria_complete and not self.eligibility:
            raise ValueError("criteria_complete requires criteria")
        return self


class SchemeKb(_Strict):
    schema_version: str
    schemes: list[Scheme]

    @model_validator(mode="after")
    def _unique(self) -> "SchemeKb":
        ids = [s.id for s in self.schemes]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate scheme id")
        owner: dict[str, str] = {}
        for s in self.schemes:
            for alias in (*s.abbreviations, *s.aliases, *s.names.values()):
                key = norm(alias)
                if owner.setdefault(key, s.id) != s.id:
                    raise ValueError(f"alias {alias!r} used by both {owner[key]} and {s.id}")
        return self
