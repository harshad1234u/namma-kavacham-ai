"""API request/response models for /v1/schemes. All citizen-facing text is localised with a status label."""
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.civic.schemes.eligibility import CriterionOutcome, Overall
from app.civic.schemes.verify import VerifyStatus
from app.civic.text import LocText

MAX_TEXT = 2000


class _Req(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lang: str = "en"


class SourceOut(BaseModel):
    id: str
    publisher: str
    title: str
    url: str
    retrieved: date


class StatementOut(BaseModel):
    text: LocText
    source_ref: str


class BenefitOut(StatementOut):
    amount_inr: int | None


class ChannelOut(BaseModel):
    type: str
    label: LocText
    official_url: str | None
    source_ref: str


class CriterionOut(BaseModel):
    id: str
    attribute: str
    kind: Literal["inclusion", "exclusion"]
    statement: StatementOut


class SchemeSummary(BaseModel):
    id: str
    name: LocText
    abbreviations: list[str]
    level: str
    ministry: str
    need_tags: list[str]
    description: StatementOut
    last_verified: date
    official_domains: list[str]


class SchemeDetail(SchemeSummary):
    benefits: list[BenefitOut]
    eligibility: list[CriterionOut]
    criteria_complete: bool
    documents: list[StatementOut]
    application_steps: list[StatementOut]
    channels: list[ChannelOut]
    helplines: list[str]
    sources: list[SourceOut]
    disclosure: LocText


class QuestionOut(BaseModel):
    attribute: str
    type: Literal["int", "enum", "bool"]
    options: list[str]
    question: LocText


class EligibilityRequest(_Req):
    answers: dict[str, int | bool | str | None] = Field(default_factory=dict, max_length=30)


class CriterionResult(BaseModel):
    criterion: CriterionOut
    outcome: CriterionOutcome


class EligibilityResult(BaseModel):
    scheme_id: str
    overall: Overall
    criteria: list[CriterionResult]
    missing_attributes: list[str]
    criteria_complete: bool
    note: LocText


class VerifyRequest(_Req):
    text: str = Field(min_length=1, max_length=MAX_TEXT)
    url: str | None = Field(default=None, max_length=500)


class FindingOut(BaseModel):
    aspect: str
    outcome: Literal["supported", "contradicted", "not_covered"]
    detail: LocText
    source_ref: str | None


class SchemeVerificationOut(BaseModel):
    scheme: SchemeSummary
    findings: list[FindingOut]
    sources: list[SourceOut]


class VerifyResult(BaseModel):
    status: VerifyStatus
    schemes: list[SchemeVerificationOut]
    disclosure: LocText
    search_portal: str | None  # official national search portal, offered when we hold nothing on the claim


class DiscoverRequest(_Req):
    text: str | None = Field(default=None, max_length=MAX_TEXT)
    need_tags: list[str] | None = Field(default=None, max_length=17)
    profile: dict[str, int | bool | str | None] = Field(default_factory=dict, max_length=30)


class SuggestionOut(BaseModel):
    scheme: SchemeSummary
    matched_need_tags: list[str]
    matched_profile: list[str]
    eligibility: Overall
    missing_attributes: list[str]


class DiscoverResult(BaseModel):
    understood_need_tags: list[str]
    understood_profile: dict[str, Any]
    extraction: Literal["deterministic", "ai_assisted", "provided"]
    suggestions: list[SuggestionOut]
    disclosure: LocText
    search_portal: str
