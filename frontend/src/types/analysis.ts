// Mirrors backend/app/schemas/analysis.py. Keep in sync with /openapi.json.

export type ContentSource = "pasted_text" | "manual_entry" | "ocr" | "user_corrected_ocr" | "url_input";
// Where the image behind screenshot text came from. The image itself is never sent.
export type ImageOrigin = "upload" | "camera";
export type Confidence = "low" | "medium" | "high";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Language = "en" | "ta";
export type AiStatus = "generated" | "disabled" | "unavailable" | "rejected";

export type SenderKind = "phone_number" | "alphanumeric_sender_id" | "display_name" | "unknown";

export interface AnalyzeRequest {
  schema_version: "1.0";
  content: { body: string; source: ContentSource; user_confirmed: true; image_origin?: ImageOrigin | null };
  sender?: {
    value: string | null;
    kind: SenderKind;
    provenance: "user_entered" | "ocr" | "user_corrected_ocr" | "unavailable";
    verification_status: "unverified";
  };
  attachment?: {
    type: "screenshot";
    provenance: "user_upload";
    original_filename?: string | null;
    declared_mime_type?: string | null;
  };
  language_preference: "en" | "ta" | "both";
  privacy: { upload_confirmed: boolean; retention_preference: "delete_after_analysis" };
}

export interface EvidenceItem {
  signal: string;
  category: "message" | "url" | "threat_intelligence" | "government_claim" | "provenance";
  source: string;
  kind: "risk" | "info";
  confidence: Confidence;
  rule_id: string | null;
  description_en: string;
  description_ta: string | null;
  observed: string | null;
}

export type ThreatIntelStatus =
  | "malicious"
  | "suspicious"
  | "not_found"
  | "clean_or_harmless"
  | "unavailable"
  | "unknown";

export interface ThreatIntelResult {
  provider: string;
  indicator_type: string;
  indicator: string;
  status: ThreatIntelStatus;
  available: boolean;
  unavailable_reason: string | null;
  engine_stats: { malicious: number; suspicious: number; harmless: number; undetected: number; timeout: number } | null;
  engines_total: number | null;
  categories: string[];
  source_timestamp: string | null;
  checked_at: string;
  from_cache: boolean;
  note: string;
  note_ta?: string | null;
}

export type GovernmentClaimStatus =
  | "supported_by_curated_kb"
  | "partially_supported_by_curated_kb"
  | "contradicted_by_curated_kb"
  | "not_found_in_curated_kb"
  | "not_government_related"
  | "unable_to_assess";

export interface ClaimField {
  value: string | null;
  confidence: Confidence;
  ambiguous: boolean;
}

export interface DetectedClaim {
  claim_type: string;
  category: string | null;
  scheme_or_service: ClaimField;
  department: ClaimField;
  requested_actions: string[];
  kb_entry_id?: string | null;
  amounts_inr?: number[];
}

export type FindingOutcome = "supported" | "contradicted" | "not_covered" | "ambiguous";

export interface KbFinding {
  aspect: string;
  outcome: FindingOutcome;
  detail_en: string;
  detail_ta: string | null;
  kb_entry_id?: string | null;
  source_ref?: string | null;
}

export interface KbSource {
  kb_entry_id: string;
  name: string;
  authority: string | null;
  official_url: string | null;
  source_citation?: string | null;
  last_reviewed?: string | null;
  source_url?: string | null;
  published?: string | null;
}

export interface GovernmentClaimResult {
  government_related: boolean;
  claim_status: GovernmentClaimStatus;
  claims: DetectedClaim[];
  matched_kb_entries?: string[];
  sources: KbSource[];
  findings: KbFinding[];
  limitations: string[];
  limitations_ta?: string[];
  safe_guidance_en?: string[];
  safe_guidance_ta?: string[];
  disclosure: string;
  disclosure_ta?: string;
}

export interface AnalyzeResponse {
  schema_version: string;
  analysis_id: string;
  risk: {
    assessment_status: "assessed" | "insufficient_content";
    level: RiskLevel;
    score: number;
    score_label: "indicator_strength";
    score_note: string;
    score_note_ta?: string;
    verdict_scope: string;
    verdict_scope_ta?: string | null;
  };
  evidence: EvidenceItem[];
  url_intelligence: {
    extracted_urls: string[];
    primary_url: string | null;
    domain_checks: { signal: string; confidence: Confidence; detail: string; url: string }[];
    provider_enabled: boolean;
    provider_result: ThreatIntelResult | null;
    privacy_note: string | null;
  };
  government_claim: GovernmentClaimResult;
  provenance: {
    content_source: ContentSource;
    image_origin: ImageOrigin | null;
    verification_status: "unverified";
    user_confirmed: boolean;
    attachment_received: boolean;
    ocr_status: "not_applicable" | "not_available_in_this_build" | "extracted" | "failed";
    character_count: number;
  };
  sender_assessment: {
    value_masked: string | null;
    kind: string;
    provenance: string;
    verification_status: "unverified";
    evidence_weight: "low";
    warnings: string[];
    warnings_ta?: string[];
  };
  missing_metadata: string[];
  limitations: string[];
  limitations_ta?: string[];
  safe_next_steps: string[];
  safe_next_steps_ta: string[];
  explanation: {
    en: string;
    ta: string;
    generated_by: "groq" | "gemini" | "template";
    ai_status?: AiStatus;
    model?: string | null;
    note: string | null;
    note_ta?: string | null;
  };
  provider_flags: {
    virustotal_enabled: boolean;
    virustotal_available: boolean | null;
    ai_provider: "groq" | "gemini" | "template";
    ai_enabled: boolean;
    ai_available: boolean | null;
  };
}
