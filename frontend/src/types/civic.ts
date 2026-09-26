// Mirrors backend/app/civic (schemes + development). Keep in sync with /openapi.json.

export type TextStatus = "authored" | "machine_translated" | "english_fallback";
export interface LocText {
  text: string;
  lang: string;
  status: TextStatus;
}
export interface Statement {
  text: LocText;
  source_ref: string;
}
export interface Source {
  id: string;
  publisher: string;
  title: string;
  url: string;
  retrieved: string;
}
export interface SchemeSummary {
  id: string;
  name: LocText;
  abbreviations: string[];
  level: string;
  ministry: string;
  need_tags: string[];
  description: Statement;
  last_verified: string;
  official_domains: string[];
}
export interface Criterion {
  id: string;
  attribute: string;
  kind: "inclusion" | "exclusion";
  statement: Statement;
}
export interface Channel {
  type: string;
  label: LocText;
  official_url: string | null;
  source_ref: string;
}
export interface SchemeDetail extends SchemeSummary {
  benefits: (Statement & { amount_inr: number | null })[];
  eligibility: Criterion[];
  criteria_complete: boolean;
  documents: Statement[];
  application_steps: Statement[];
  channels: Channel[];
  helplines: string[];
  sources: Source[];
  disclosure: LocText;
}
export interface Question {
  attribute: string;
  type: "int" | "enum" | "bool";
  options: string[];
  question: LocText;
}
export type EligibilityOverall =
  | "eligible_on_available_info"
  | "possibly_eligible"
  | "not_enough_information"
  | "criteria_not_satisfied";
export type CriterionOutcome = "satisfied" | "not_satisfied" | "unknown" | "not_machine_checkable";
export interface EligibilityResult {
  scheme_id: string;
  overall: EligibilityOverall;
  criteria: { criterion: Criterion; outcome: CriterionOutcome }[];
  missing_attributes: string[];
  criteria_complete: boolean;
  note: LocText;
}
export type VerifyStatus = "supported" | "partially_supported" | "contradicted" | "not_found" | "unable_to_verify";
export interface Finding {
  aspect: string;
  outcome: "supported" | "contradicted" | "not_covered";
  detail: LocText;
  source_ref: string | null;
  evidence_url: string | null;
}
export interface Evidence {
  url: string;
  title: string;
  domain: string;
  retrieved_at: string;
  quote: string;
  scheme_id: string | null;
  method: string;
}
export interface Explanation {
  text: string;
  lang: string;
  status: "ai_generated" | "template" | "machine_translated" | "english_fallback";
  model: string | null;
}
export interface Suggestion {
  scheme: SchemeSummary;
  matched_need_tags: string[];
  matched_profile: string[];
  eligibility: EligibilityOverall;
  missing_attributes: string[];
}
export interface VerifyResult {
  status: VerifyStatus;
  basis: "curated_kb" | "official_evidence" | "none";
  message: string | null;
  schemes: { scheme: SchemeSummary; findings: Finding[]; sources: Source[] }[];
  evidence_findings: Finding[];
  evidence: Evidence[];
  sources_checked: number | null;
  understanding: {
    scheme_ids: string[];
    scheme_name: string | null;
    need_tags: string[];
    method: "deterministic" | "ai_assisted";
    pii_removed: Record<string, number>;
  };
  explanation: Explanation;
  disclosure: LocText;
  search_portal: string | null;
}
export interface AskResult extends VerifyResult {
  suggestions: Suggestion[];
}
export interface DiscoverResult {
  understood_need_tags: string[];
  understood_profile: Record<string, unknown>;
  extraction: "deterministic" | "ai_assisted" | "provided";
  suggestions: Suggestion[];
  disclosure: LocText;
  search_portal: string;
}
export interface AiStatus {
  ai_enabled: boolean;
  provider: string | null;
  chat_model: string | null;
  embedding_model: string | null;
  official_retrieval: boolean;
}
export interface LanguageInfo {
  code: string;
  name: string;
  native_name: string;
  script: string;
  dir: "ltr" | "rtl";
  scheduled: boolean;
  tier: 1 | 2 | 3;
  support: { ui: string; query_understanding: string; kb_text: string };
}

// ---------- development ----------
export type PriorityLevel = "critical" | "high" | "medium" | "lower" | "unable_to_assess";
export interface Provenance {
  type: "demo" | "official";
  name: string;
  last_updated: string;
  scope?: string | null;
  note?: string | null;
  url?: string | null;
}
export interface DemoArea {
  area_id: string;
  state: string;
  district: string;
  area: string;
  lat: number;
  lng: number;
}
export interface DevMeta {
  categories: { id: string; labels: Record<string, string>; issue_types: { id: string; label: string }[] }[];
  statuses: string[];
  priority_levels: Record<string, string>;
  weights: Record<string, number>;
  hotspot_min_reports: number;
  states_and_uts: string[];
  states_source: Provenance;
  demo_areas: DemoArea[];
  provenance: Provenance;
  disclaimer: string;
}
export interface Classification {
  category: string | null;
  category_label: string | null;
  issue_type: string | null;
  urgency: string;
  confidence: string;
  reason: string;
  language: string;
  method: string;
}
export interface Receipt {
  id: string;
  category: string;
  category_label: string;
  issue_type: string | null;
  state: string;
  district: string;
  locality: string | null;
  urgency: string;
  created_at: string;
  statuses: string[];
  issue_id: string;
  photo_attached: boolean;
  classification: Classification | null;
  note: string;
}
export interface IssueSummary {
  id: string;
  category: string;
  category_label: string;
  state: string;
  district: string;
  locality: string | null;
  lat: number | null;
  lng: number | null;
  report_count: number;
  priority_score: number | null;
  priority_level: PriorityLevel;
  gap_level: string;
  hotspot: boolean;
  high_urgency_reports: number;
  data_completeness: number;
  demo_data: boolean;
}
export interface Component {
  name: string;
  weight: number;
  assessed: boolean;
  value: number | null;
  points: number | null;
  note: string;
}
export interface IssueDetail extends IssueSummary {
  components: Component[];
  gap_reasons: string[];
  population: number | null;
  infrastructure_metric: string | null;
  infrastructure_value: number | null;
  demographics: Record<string, number | string | null> | null;
  infrastructure: Record<string, number | string | null> | null;
  projects: { project_id: string; name: string; status: string; budget_inr: number; expected_completion: string }[];
  themes: [string, number][];
  timeline: [string, number][];
  relevant_schemes: { id: string; name: string }[];
  insight: Explanation;
  provenance: Record<string, Provenance>;
  disclaimer: string;
}
export interface Dashboard {
  total_requests: number;
  active_issues: number;
  hotspots: number;
  high_priority_issues: number;
  by_category: [string, number][];
  by_district: [string, number][];
  requests_over_time: [string, number][];
  priority_distribution: Record<string, number>;
  gap_distribution: Record<string, number>;
  scheme_demand: { scheme_id: string; scheme: string; district: string; mentions: number }[];
  top_hotspots: IssueSummary[];
  provenance: Provenance;
  disclaimer: string;
}
