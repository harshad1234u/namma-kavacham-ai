import type { AnalyzeResponse, ThreatIntelResult } from "../types/analysis";

export function vtResult(overrides: Partial<ThreatIntelResult> = {}): ThreatIntelResult {
  return {
    provider: "virustotal",
    indicator_type: "url",
    indicator: "http://tneb-billupdate.in/pay.apk",
    status: "unavailable",
    available: false,
    unavailable_reason: "timeout",
    engine_stats: null,
    engines_total: null,
    categories: [],
    source_timestamp: null,
    checked_at: "2026-09-24T00:00:00Z",
    from_cache: false,
    note: "The threat-intelligence check could not be completed. The link was not checked, so this must not be read as safe.",
    ...overrides,
  };
}

export function makeResponse(overrides: Partial<AnalyzeResponse> = {}): AnalyzeResponse {
  return {
    schema_version: "1.0",
    analysis_id: "test-id",
    risk: {
      assessment_status: "assessed",
      level: "CRITICAL",
      score: 88,
      score_label: "indicator_strength",
      score_note: "",
      verdict_scope: "This is a message-risk assessment. It does not verify the sender's identity.",
    },
    evidence: [
      {
        signal: "credential_request",
        category: "message",
        source: "deterministic_message_rules",
        kind: "risk",
        confidence: "high",
        rule_id: "MSG-CRED-01",
        description_en: "The message asks you to share or enter an OTP.",
        description_ta: "செய்தி OTP-ஐப் பகிரக் கேட்கிறது.",
        observed: "share the otp",
      },
    ],
    url_intelligence: {
      extracted_urls: ["http://tneb-billupdate.in/pay.apk"],
      primary_url: "http://tneb-billupdate.in/pay.apk",
      domain_checks: [],
      provider_enabled: true,
      provider_result: vtResult(),
      privacy_note: null,
    },
    government_claim: {
      government_related: true,
      claim_status: "unable_to_assess",
      claims: [],
      sources: [],
      findings: [],
      limitations: ["The claim was not checked."],
      disclosure: "This comparison uses a curated static dataset.",
    },
    provenance: {
      content_source: "pasted_text",
      verification_status: "unverified",
      user_confirmed: true,
      attachment_received: false,
      ocr_status: "not_applicable",
      character_count: 120,
    },
    sender_assessment: {
      value_masked: null,
      kind: "unknown",
      provenance: "unavailable",
      verification_status: "unverified",
      evidence_weight: "low",
      warnings: ["The sender was not authenticated."],
    },
    missing_metadata: ["sender_identity_not_supplied", "url_threat_intelligence_unavailable"],
    limitations: [],
    safe_next_steps: ["Do not share any OTP."],
    safe_next_steps_ta: ["எந்த OTP-யையும் பகிர வேண்டாம்."],
    explanation: { en: "Strong scam indicators were detected.", ta: "வலுவான மோசடிக் குறிகள் கண்டறியப்பட்டன.", generated_by: "template", note: null },
    provider_flags: { virustotal_enabled: true, virustotal_available: false, gemini_enabled: false, gemini_available: null },
    ...overrides,
  };
}
