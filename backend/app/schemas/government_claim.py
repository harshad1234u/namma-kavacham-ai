from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

KB_DISCLOSURE = (
    "This comparison uses a curated static dataset. It is not live verification of current "
    "government records. A scheme or service existing in this dataset does not prove that a "
    "particular message is genuine."
)
KB_DISCLOSURE_TA = (
    "இந்த ஒப்பீடு தொகுக்கப்பட்ட நிலையான தரவுத்தொகுப்பைப் பயன்படுத்துகிறது. இது தற்போதைய அரசுப் பதிவுகளின் நேரடிச் "
    "சரிபார்ப்பு அல்ல. ஒரு திட்டம் அல்லது சேவை இந்தத் தரவில் இருப்பது, குறிப்பிட்ட செய்தி உண்மையானது என்பதை நிரூபிக்காது."
)


class GovernmentClaimStatus(str, Enum):
    SUPPORTED = "supported_by_curated_kb"
    PARTIALLY_SUPPORTED = "partially_supported_by_curated_kb"
    CONTRADICTED = "contradicted_by_curated_kb"
    NOT_FOUND = "not_found_in_curated_kb"
    NOT_GOVERNMENT_RELATED = "not_government_related"
    UNABLE_TO_ASSESS = "unable_to_assess"


Confidence = Literal["low", "medium", "high"]


class ClaimField(BaseModel):
    value: str | None = None
    confidence: Confidence = "low"
    ambiguous: bool = False


class DetectedClaim(BaseModel):
    claim_type: str
    category: str | None = None
    scheme_or_service: ClaimField = Field(default_factory=ClaimField)
    department: ClaimField = Field(default_factory=ClaimField)
    requested_actions: list[str] = Field(default_factory=list)
    kb_entry_id: str | None = None
    amounts_inr: list[int] = Field(default_factory=list)


class KbSource(BaseModel):
    kb_entry_id: str
    name: str
    authority: str | None = None
    official_url: str | None = None
    source_citation: str | None = None
    last_reviewed: str | None = None
    source_url: str | None = None
    published: str | None = None


class KbFinding(BaseModel):
    aspect: str
    outcome: Literal["supported", "contradicted", "not_covered", "ambiguous"]
    detail_en: str
    detail_ta: str | None = None
    kb_entry_id: str | None = None
    source_ref: str | None = None


class GovernmentClaimResult(BaseModel):
    government_related: bool
    claim_status: GovernmentClaimStatus
    claims: list[DetectedClaim] = Field(default_factory=list)
    matched_kb_entries: list[str] = Field(default_factory=list)
    sources: list[KbSource] = Field(default_factory=list)
    findings: list[KbFinding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    limitations_ta: list[str] = Field(default_factory=list)
    safe_guidance_en: list[str] = Field(default_factory=list)
    safe_guidance_ta: list[str] = Field(default_factory=list)
    disclosure: str = KB_DISCLOSURE
    disclosure_ta: str = KB_DISCLOSURE_TA
