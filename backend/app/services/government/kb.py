"""Loads and validates the curated government knowledge base (app/data/government_kb.json)."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

KB_PATH = Path(__file__).resolve().parents[2] / "data" / "government_kb.json"

REQUIRED_CATEGORIES = frozenset(
    {"aadhaar_identity", "schemes_benefits", "income_tax", "passport", "cybercrime_reporting"}
)
OFFICIAL_SUFFIXES = (".gov.in", ".nic.in")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class KbSourceDoc(_Strict):
    id: str
    publisher: str
    title: str
    url: str
    published: str | None
    retrieved: str
    quotes: list[str]


class KbFact(_Strict):
    id: str
    applies_to_signal: str | None = None
    applies_to_claim: Literal["installment_amount"] | None = None
    effect: Literal["contradicts", "not_covered", "compare_amount"]
    expected_amount_inr: int | None = None
    statement_en: str
    statement_ta: str
    source_ref: str

    @model_validator(mode="after")
    def _one_trigger(self) -> "KbFact":
        if (self.applies_to_signal is None) == (self.applies_to_claim is None):
            raise ValueError(f"fact {self.id} must set exactly one of applies_to_signal / applies_to_claim")
        if self.effect == "compare_amount" and self.expected_amount_inr is None:
            raise ValueError(f"fact {self.id} compares an amount but has no expected_amount_inr")
        return self


class KbHelpline(_Strict):
    number: str
    source_ref: str


class KbEntry(_Strict):
    id: str
    category: str
    service_name: str
    service_name_ta: str
    authority: str
    aliases: list[str] = Field(min_length=1)
    official_domains: list[str] = Field(min_length=1)
    official_urls: list[str] = Field(min_length=1)
    helplines: list[KbHelpline]
    facts: list[KbFact]
    safe_guidance_en: str
    safe_guidance_ta: str
    sources: list[KbSourceDoc] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> "KbEntry":
        source_ids = {s.id for s in self.sources}
        refs = [f.source_ref for f in self.facts] + [h.source_ref for h in self.helplines]
        missing = [r for r in refs if r not in source_ids]
        if missing:
            raise ValueError(f"entry {self.id} cites unknown sources: {missing}")
        for domain in self.official_domains:
            if not domain.endswith(OFFICIAL_SUFFIXES):
                raise ValueError(f"entry {self.id}: '{domain}' is not a government-reserved domain")
        for url in self.official_urls:
            if not url.startswith("https://") or not any(d in url for d in self.official_domains):
                raise ValueError(f"entry {self.id}: official URL {url} is not https on an official domain")
        return self


class GovernmentKb(_Strict):
    schema_version: str
    last_reviewed: str
    scope_note: str
    entries: list[KbEntry]

    @model_validator(mode="after")
    def _all_categories(self) -> "GovernmentKb":
        present = {e.category for e in self.entries}
        if missing := REQUIRED_CATEGORIES - present:
            raise ValueError(f"knowledge base is missing required categories: {sorted(missing)}")
        ids = [e.id for e in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate entry ids")
        return self

    def source(self, entry: KbEntry, source_id: str) -> KbSourceDoc:
        return next(s for s in entry.sources if s.id == source_id)


def parse_kb(raw: str) -> GovernmentKb:
    return GovernmentKb.model_validate(json.loads(raw))


@lru_cache
def load_kb() -> GovernmentKb:
    return parse_kb(KB_PATH.read_text(encoding="utf-8"))
