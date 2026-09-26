import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { LanguageProvider } from "../i18n/LanguageContext";
import { resetAiStatusCache } from "../services/useAi";
import { listen, VoiceError } from "../services/voiceInput";

const loc = (text: string, status = "authored") => ({ text, lang: "en", status });
const scheme = {
  id: "pm_kisan", name: loc("Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)"), abbreviations: ["PM-KISAN"], level: "central",
  ministry: "Ministry of Agriculture and Farmers Welfare", need_tags: ["farming_income_support"],
  description: { text: loc("Income support to land-holding farmer families."), source_ref: "s" }, last_verified: "2026-09-26",
  official_domains: ["pmkisan.gov.in"],
};
const ASK = {
  status: "contradicted", basis: "curated_kb", message: null,
  schemes: [{ scheme, findings: [{ aspect: "amount", outcome: "contradicted", detail: loc("The official source states ₹6,000 per year, not ₹10,000."), source_ref: "s", evidence_url: null }],
    sources: [{ id: "s", publisher: "PM-KISAN", title: "PM-Kisan home", url: "https://pmkisan.gov.in/", retrieved: "2026-09-26" }] }],
  evidence_findings: [], evidence: [], sources_checked: null,
  understanding: { scheme_ids: ["pm_kisan"], scheme_name: null, need_tags: [], method: "deterministic", pii_removed: {} },
  explanation: { text: "An official source says something different from this claim.", lang: "en", status: "template", model: null },
  disclosure: loc("Information comes from official pages."), search_portal: null, suggestions: [],
};
const META = {
  categories: [{ id: "water", labels: { en: "Water", hi: "पानी", ta: "குடிநீர்" }, issue_types: [] }],
  statuses: [], priority_levels: {}, weights: {}, hotspot_min_reports: 20, states_and_uts: ["TAMIL NADU", "ASSAM"],
  states_source: { type: "official", name: "DBT", last_updated: "2026-09-26" },
  demo_areas: [{ area_id: "tiruchirappalli-a", state: "TAMIL NADU", district: "Tiruchirappalli", area: "Demo Area A", lat: 10.8, lng: 78.7 }],
  provenance: { type: "demo", name: "demo", last_updated: "2026-09-26" }, disclaimer: "not a government decision",
};
const ISSUE = {
  id: "tiruchirappalli-a__water", category: "water", category_label: "Water", state: "TAMIL NADU", district: "Tiruchirappalli",
  locality: "Demo Area A", lat: 10.8, lng: 78.7, report_count: 132, priority_score: 87, priority_level: "critical", gap_level: "high",
  hotspot: true, high_urgency_reports: 72, data_completeness: 1, demo_data: true,
};
const DASH = {
  total_requests: 535, active_issues: 24, hotspots: 4, high_priority_issues: 11, by_category: [["Water", 158]],
  by_district: [["Tiruchirappalli, Tamil Nadu", 200]], requests_over_time: [["2026-09-21", 30]], priority_distribution: { critical: 1 },
  gap_distribution: { high: 2 }, scheme_demand: [], top_hotspots: [ISSUE], provenance: META.provenance, disclaimer: "not a government decision",
};

type Handler = (url: string, init?: RequestInit) => unknown;
let routes: [RegExp, Handler | unknown, number?][];
const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
  const hit = routes.find(([re]) => re.test(url));
  if (!hit) return new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 });
  const [, body, status = 200] = hit;
  const payload = typeof body === "function" ? (body as Handler)(url, init) : body;
  return new Response(JSON.stringify(payload), { status });
});

function renderAt(path: string) {
  return render(
    <LanguageProvider>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </LanguageProvider>,
  );
}

beforeEach(() => {
  resetAiStatusCache();
  routes = [
    [/\/v1\/meta\/ai/, { ai_enabled: false, provider: null, chat_model: null, embedding_model: null, official_retrieval: true }],
    [/\/v1\/schemes\?|\/v1\/schemes$/, [scheme]],
  ];
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockClear();
});
afterEach(() => vi.unstubAllGlobals());

describe("platform", () => {
  it("brands the app and shows the verified-scheme count", async () => {
    renderAt("/");
    expect(screen.getAllByText("CivicInsight AI").length).toBeGreaterThan(0);
    expect(await screen.findByText(/1 central schemes verified/)).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
  });

  it("switches to Hindi UI, sets RTL for Urdu and shows the English-fallback notice", async () => {
    const user = userEvent.setup();
    renderAt("/");
    const picker = screen.getByRole("combobox", { name: /language/i });
    await user.selectOptions(picker, "hi");
    expect(screen.getByRole("link", { name: "योजनाएँ खोजें" })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("hi");
    await user.selectOptions(picker, "ur");
    expect(document.documentElement.dir).toBe("rtl");
    expect(screen.getByRole("note")).toHaveTextContent(/not yet available in Urdu/);
  });

  it("keeps the existing scam checker reachable under Stay Safe", async () => {
    renderAt("/safety");
    expect(await screen.findByRole("link", { name: /start a check/i })).toHaveAttribute("href", "/analyze");
  });
});

describe("schemes", () => {
  it("shows the deterministic verdict, explanation label and official source", async () => {
    routes.push([/\/v1\/schemes\/ask/, ASK]);
    const user = userEvent.setup();
    renderAt("/schemes");
    expect(await screen.findByText(/AI is currently off/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Your question or claim"), "Is PM-KISAN giving ₹10,000 every year?");
    await user.click(screen.getByRole("button", { name: "Check" }));
    expect(await screen.findByTestId("verify-status")).toHaveTextContent("Contradicted by an official source");
    expect(screen.getByText("Standard explanation")).toBeInTheDocument();
    const src = screen.getByRole("link", { name: /PM-Kisan home/ });
    expect(src).toHaveAttribute("href", "https://pmkisan.gov.in/");
    expect(within(src).getByText("Official")).toBeInTheDocument();
    const body = JSON.parse(fetchMock.mock.calls.find(([u]) => String(u).includes("/ask"))![1]!.body as string);
    expect(body.ai_consent).toBe(false);
  });

  it("never implies fake when unable to verify, and offers the official portal", async () => {
    routes.push([/\/v1\/schemes\/ask/, { ...ASK, status: "unable_to_verify", basis: "none", schemes: [], search_portal: "https://www.myscheme.gov.in/" }]);
    const user = userEvent.setup();
    renderAt("/schemes");
    await user.type(await screen.findByLabelText("Your question or claim"), "Mystery Yojana?");
    await user.click(screen.getByRole("button", { name: "Check" }));
    expect(await screen.findByText(/does not mean fake/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /official national scheme portal/ })).toHaveAttribute("href", "https://www.myscheme.gov.in/");
  });

  it("recovers from a server error", async () => {
    routes.push([/\/v1\/schemes\/ask/, { detail: "x" }, 500]);
    const user = userEvent.setup();
    renderAt("/schemes");
    await user.type(await screen.findByLabelText("Your question or claim"), "PM-KISAN?");
    await user.click(screen.getByRole("button", { name: "Check" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("discovers schemes and shows why they match", async () => {
    routes.push([/\/v1\/schemes\/discover/, { understood_need_tags: ["farming_income_support"], understood_profile: {}, extraction: "deterministic",
      suggestions: [{ scheme, matched_need_tags: ["farming_income_support"], matched_profile: [], eligibility: "not_enough_information", missing_attributes: [] }],
      disclosure: loc("d"), search_portal: "https://www.myscheme.gov.in/" }]);
    const user = userEvent.setup();
    renderAt("/schemes/discover");
    await user.click(screen.getByRole("button", { name: "Farming income support" }));
    await user.click(screen.getByRole("button", { name: "Find schemes" }));
    expect(await screen.findByText(/Matches your need: Farming income support/)).toBeInTheDocument();
    expect(screen.getByText("Not enough information")).toBeInTheDocument();
  });

  it("walks through the eligibility questions", async () => {
    routes.push(
      [/\/eligibility\/questions/, [{ attribute: "owns_agricultural_land", type: "bool", options: ["true", "false"], question: loc("Does your family own cultivable agricultural land?") }]],
      [/\/eligibility$/, { scheme_id: "pm_kisan", overall: "possibly_eligible", criteria: [], missing_attributes: [], criteria_complete: false, note: loc("guidance, not a decision") }],
      [/\/v1\/schemes\/pm_kisan/, { ...scheme, benefits: [{ text: loc("₹6,000 per year."), source_ref: "s", amount_inr: 6000 }], eligibility: [], criteria_complete: false,
        documents: [], application_steps: [], channels: [{ type: "online_portal", label: loc("New Farmer Registration"), official_url: "https://pmkisan.gov.in/RegistrationFormupdated.aspx", source_ref: "s" }],
        helplines: [], sources: [], disclosure: loc("d") }],
    );
    const user = userEvent.setup();
    renderAt("/schemes/pm_kisan");
    expect(await screen.findByText("₹6,000 per year.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /New Farmer Registration/ })).toHaveAttribute("href", "https://pmkisan.gov.in/RegistrationFormupdated.aspx");
    await user.click(await screen.findByText("Yes"));
    await user.click(screen.getByRole("button", { name: "See result" }));
    expect(await screen.findByTestId("eligibility-overall")).toHaveTextContent("Possibly eligible");
    const call = fetchMock.mock.calls.find(([u]) => String(u).endsWith("/eligibility"))!;
    expect(JSON.parse(call[1]!.body as string).answers).toEqual({ owns_agricultural_land: true });
  });
});

describe("development", () => {
  it("submits a report with consent and shows transparent statuses", async () => {
    let sent: FormData | null = null;
    routes.push(
      [/\/v1\/development\/meta/, META],
      [/\/v1\/development\/requests$/, (_u: string, init?: RequestInit) => {
        sent = init!.body as FormData;
        return { id: "REQ-ABC", category: "water", category_label: "Water", issue_type: "no_supply", state: "TAMIL NADU",
          district: "Tiruchirappalli", locality: "Demo Area A", urgency: "high", created_at: "2026-09-26",
          statuses: ["received", "aggregated", "priority_assessed", "included_in_insight"], issue_id: ISSUE.id, photo_attached: false,
          classification: null, note: "It has not been sent to any government office." };
      }],
    );
    const user = userEvent.setup();
    renderAt("/dev/report");
    await user.type(await screen.findByLabelText(/Describe the problem/), "No drinking water, we walk 4 km every day");
    await user.selectOptions(screen.getByLabelText(/State \/ UT/), "TAMIL NADU");
    await user.type(screen.getByLabelText(/District/), "Tiruchirappalli");
    await user.selectOptions(screen.getByLabelText("Locality (demo areas)"), "tiruchirappalli-a");
    const submit = screen.getByRole("button", { name: "Submit development request" });
    expect(submit).toBeDisabled(); // consent first
    await user.click(screen.getByRole("checkbox"));
    await user.click(submit);
    expect(await screen.findByText("Request received")).toBeInTheDocument();
    expect(screen.getByText("Included in development insight")).toBeInTheDocument();
    expect(screen.getByText(/not been sent to any government office/)).toBeInTheDocument();
    const payload = JSON.parse((sent as unknown as FormData).get("payload") as string);
    expect(payload).toMatchObject({ consent: true, area_id: "tiruchirappalli-a", state: "TAMIL NADU", ai_consent: false });
  });

  it("says voice is unavailable instead of pretending", async () => {
    routes.push([/\/v1\/development\/meta/, META]);
    renderAt("/dev/report");
    expect(await screen.findByText(/Voice input is not available in this browser/)).toBeInTheDocument();
  });

  it("renders the dashboard with demo banner, hotspot table and no map until asked", async () => {
    routes.push([/\/v1\/development\/meta/, META], [/\/v1\/development\/dashboard/, DASH], [/\/v1\/development\/issues/, [ISSUE]]);
    const user = userEvent.setup();
    renderAt("/dev");
    expect(await screen.findByText("535")).toBeInTheDocument();
    expect(screen.getAllByText(/Demonstration data/).length).toBeGreaterThan(0);
    const row = screen.getByRole("link", { name: "Demo Area A, Tiruchirappalli" });
    expect(row).toHaveAttribute("href", "/dev/hotspots/tiruchirappalli-a__water");
    expect(within(row.closest("tr")!).getByText(/Critical/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Show map" })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Category"), "water");
    await user.click(screen.getByRole("button", { name: "Apply" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => String(u).includes("dashboard?category=water"))).toBe(true));
  });

  it("shows unassessed components honestly on the hotspot page", async () => {
    routes.push([/\/v1\/development\/hotspots\//, { ...ISSUE, priority_score: null, priority_level: "unable_to_assess", data_completeness: 0.4,
      components: [{ name: "population_impact", weight: 25, assessed: false, value: null, points: null, note: "Population impact cannot be assessed from available data." }],
      gap_reasons: ["Infrastructure data unavailable."], population: null, infrastructure_metric: null, infrastructure_value: null, demographics: null,
      infrastructure: null, projects: [], themes: [["No or irregular supply", 3]], timeline: [["2026-09-21", 3]], relevant_schemes: [],
      insight: { text: "No priority score, because too little context data is available.", lang: "en", status: "template", model: null },
      provenance: { requests: META.provenance }, disclaimer: "not a government decision" }]);
    renderAt("/dev/hotspots/x");
    expect(await screen.findByText("Unable to assess")).toBeInTheDocument();
    expect(screen.getAllByText("Not assessed").length).toBeGreaterThan(0);
    expect(screen.getByText("Population impact cannot be assessed from available data.")).toBeInTheDocument();
  });
});

describe("voice input service", () => {
  it("returns the transcript and maps permission errors", async () => {
    class FakeRec {
      lang = ""; interimResults = false; continuous = false;
      onresult: ((e: unknown) => void) | null = null; onerror: ((e: { error: string }) => void) | null = null; onend: (() => void) | null = null;
      static mode: "ok" | "denied" = "ok";
      start() {
        setTimeout(() => {
          if (FakeRec.mode === "denied") this.onerror?.({ error: "not-allowed" });
          else this.onresult?.({ results: [[{ transcript: "குடிநீர் இல்லை" }]] });
          this.onend?.();
        }, 0);
      }
      stop() {}
    }
    vi.stubGlobal("webkitSpeechRecognition", FakeRec);
    await expect(listen("ta").result).resolves.toBe("குடிநீர் இல்லை");
    FakeRec.mode = "denied";
    await expect(listen("ta").result).rejects.toEqual(new VoiceError("denied"));
  });
});
