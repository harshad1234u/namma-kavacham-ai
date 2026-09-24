from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.government_claim import GovernmentClaimResult
from app.schemas.threat_intelligence import ThreatIntelResult

SCHEMA_VERSION = "1.0"
HARD_MAX_BODY_CHARS = 20_000

ContentSource = Literal["pasted_text", "manual_entry", "ocr", "user_corrected_ocr", "url_input"]
Confidence = Literal["low", "medium", "high"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- request ----------


class ContentIn(_Strict):
    body: str = Field(default="", max_length=HARD_MAX_BODY_CHARS)
    source: ContentSource
    user_confirmed: Literal[True] = Field(
        description="Must be true: the user reviewed this exact content and chose to submit it."
    )


class SenderIn(_Strict):
    value: str | None = Field(default=None, max_length=64)
    kind: Literal["phone_number", "alphanumeric_sender_id", "display_name", "unknown"] = "unknown"
    provenance: Literal["user_entered", "ocr", "user_corrected_ocr", "unavailable"] = "unavailable"
    # No auditable authority exists in this MVP, so nothing may be submitted as verified.
    verification_status: Literal["unverified"] = "unverified"


class AttachmentMeta(_Strict):
    type: Literal["screenshot"] = "screenshot"
    provenance: Literal["user_upload"] = "user_upload"
    original_filename: str | None = Field(default=None, max_length=255)
    declared_mime_type: str | None = Field(default=None, max_length=100)


class PrivacyIn(_Strict):
    upload_confirmed: bool
    retention_preference: Literal["delete_after_analysis"] = "delete_after_analysis"


class AnalyzeRequest(_Strict):
    schema_version: str = SCHEMA_VERSION
    content: ContentIn
    sender: SenderIn | None = None
    attachment: AttachmentMeta | None = None
    language_preference: Literal["en", "ta", "both"] = "both"
    privacy: PrivacyIn

    @model_validator(mode="after")
    def _body_required_unless_screenshot(self) -> "AnalyzeRequest":
        ocr_path = self.content.source in ("ocr", "user_corrected_ocr") or self.attachment is not None
        if not self.content.body.strip() and not ocr_path:
            raise ValueError("content.body must not be empty for text or URL input")
        if self.attachment is not None and not self.privacy.upload_confirmed:
            raise ValueError("privacy.upload_confirmed must be true when a screenshot is attached")
        return self


# ---------- response ----------


class RiskOut(BaseModel):
    assessment_status: Literal["assessed", "insufficient_content"] = Field(
        description="`insufficient_content` means there was no text to analyse; the level must not be read as safe."
    )
    level: RiskLevel
    score: int = Field(ge=0, le=100)
    score_label: Literal["indicator_strength"] = "indicator_strength"
    score_note: str = (
        "The score reflects the strength of detected risk indicators. It is not a probability "
        "that the message is a scam."
    )
    score_note_ta: str = (
        "இந்த மதிப்பெண் கண்டறியப்பட்ட ஆபத்துக் குறிகளின் வலிமையைக் காட்டுகிறது. இது செய்தி மோசடி என்பதற்கான "
        "நிகழ்தகவு அல்ல."
    )
    verdict_scope: str
    verdict_scope_ta: str | None = None


class EvidenceItem(BaseModel):
    signal: str
    category: Literal["message", "url", "threat_intelligence", "government_claim", "provenance"]
    source: str
    kind: Literal["risk", "info"] = "risk"
    confidence: Confidence
    rule_id: str | None = None
    description_en: str
    description_ta: str | None = None
    observed: str | None = Field(
        default=None, description="Short excerpt of what triggered the rule, echoed back only to this user"
    )


class DomainCheckOut(BaseModel):
    signal: str
    confidence: Confidence
    detail: str
    url: str


class UrlIntelligenceOut(BaseModel):
    extracted_urls: list[str]
    primary_url: str | None
    domain_checks: list[DomainCheckOut]
    provider_enabled: bool
    provider_result: ThreatIntelResult | None
    privacy_note: str | None = None


class ProvenanceOut(BaseModel):
    content_source: ContentSource
    verification_status: Literal["unverified"] = "unverified"
    user_confirmed: bool
    attachment_received: bool
    ocr_status: Literal["not_applicable", "not_available_in_this_build", "extracted", "failed"]
    character_count: int


class SenderAssessmentOut(BaseModel):
    value_masked: str | None
    kind: str
    provenance: str
    verification_status: Literal["unverified"] = "unverified"
    evidence_weight: Literal["low"] = "low"
    warnings: list[str]
    warnings_ta: list[str] = Field(default_factory=list)


class ExplanationOut(BaseModel):
    en: str
    ta: str
    generated_by: Literal["gemini", "template"]
    ai_status: Literal["generated", "disabled", "unavailable", "rejected"] = Field(
        default="disabled",
        description="`generated`: AI explanation passed validation. Otherwise the template explanation is shown.",
    )
    model: str | None = None
    note: str | None = None
    note_ta: str | None = None


class ProviderFlags(BaseModel):
    virustotal_enabled: bool
    virustotal_available: bool | None = Field(description="None when no URL was checked")
    gemini_enabled: bool
    gemini_available: bool | None = Field(description="None when no explanation call was attempted")


class AnalyzeResponse(BaseModel):
    schema_version: str = SCHEMA_VERSION
    analysis_id: str
    risk: RiskOut
    evidence: list[EvidenceItem]
    url_intelligence: UrlIntelligenceOut
    government_claim: GovernmentClaimResult
    provenance: ProvenanceOut
    sender_assessment: SenderAssessmentOut
    missing_metadata: list[str]
    limitations: list[str]
    limitations_ta: list[str] = Field(default_factory=list)
    safe_next_steps: list[str]
    safe_next_steps_ta: list[str]
    explanation: ExplanationOut
    provider_flags: ProviderFlags


class ErrorResponse(BaseModel):
    error: str
    detail: str
    analysis_id: str | None = None
