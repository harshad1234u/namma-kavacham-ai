import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LanguageToggle } from "../components/LanguageToggle";
import { RiskCard } from "../components/RiskCard";
import { LanguageProvider } from "../i18n/LanguageContext";
import type { AnalyzeResponse, GovernmentClaimResult } from "../types/analysis";
import { makeResponse } from "./fixtures";

function renderCard(result: AnalyzeResponse) {
  render(
    <LanguageProvider>
      <LanguageToggle />
      <RiskCard result={result} onReset={vi.fn()} />
    </LanguageProvider>,
  );
}

const partialGov: GovernmentClaimResult = {
  government_related: true,
  claim_status: "partially_supported_by_curated_kb",
  claims: [
    {
      claim_type: "benefit_or_installment",
      category: "schemes_benefits",
      scheme_or_service: { value: "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)", confidence: "high", ambiguous: false },
      department: { value: null, confidence: "low", ambiguous: false },
      requested_actions: ["pay_money_or_fee"],
      kb_entry_id: "pm_kisan",
    },
  ],
  matched_kb_entries: ["pm_kisan"],
  sources: [
    {
      kb_entry_id: "pm_kisan",
      name: "PM-KISAN",
      authority: null,
      official_url: "https://pmkisan.gov.in/",
      source_citation: "PM-KISAN official website: home page",
      source_url: "https://pmkisan.gov.in/",
      published: null,
    },
  ],
  findings: [
    { aspect: "service_exists", outcome: "supported", detail_en: "PM-KISAN is a real service.", detail_ta: "பிஎம்-கிசான் உண்மையான சேவை." },
    { aspect: "fact:pm_kisan_direct_transfer", outcome: "not_covered", detail_en: "No fee is described.", detail_ta: "கட்டணம் குறிப்பிடப்படவில்லை." },
  ],
  limitations: ["Only part of the message matches."],
  limitations_ta: ["செய்தியின் ஒரு பகுதி மட்டுமே பொருந்துகிறது."],
  disclosure: "This comparison uses a curated static dataset.",
  disclosure_ta: "இந்த ஒப்பீடு தொகுக்கப்பட்ட நிலையான தரவுத்தொகுப்பைப் பயன்படுத்துகிறது.",
};

describe("GovernmentClaimCard", () => {
  it("shows partial support, requested actions, findings and sources", () => {
    renderCard(makeResponse({ government_claim: partialGov }));
    const status = screen.getByTestId("gov-status");
    expect(status).toHaveAttribute("data-status", "partially_supported_by_curated_kb");
    expect(status).toHaveTextContent(/partially consistent/i);
    expect(screen.getByText(/asks you to: pay money or a fee/i)).toBeInTheDocument();
    const outcomes = screen.getAllByTestId("kb-finding").map((f) => f.getAttribute("data-outcome"));
    expect(outcomes).toEqual(["supported", "not_covered"]);
    expect(screen.getByText("PM-KISAN official website: home page")).toBeInTheDocument();
    expect(screen.getByText(/curated static dataset/)).toBeInTheDocument();
  });

  it("never styles a supported claim as safe (teal)", () => {
    renderCard(makeResponse({ government_claim: { ...partialGov, claim_status: "supported_by_curated_kb" } }));
    expect(screen.getByTestId("gov-status").className).not.toMatch(/teal/);
  });

  it("marks ambiguous and out-of-reference claims", () => {
    renderCard(
      makeResponse({
        government_claim: {
          ...partialGov,
          claim_status: "unable_to_assess",
          matched_kb_entries: [],
          claims: [
            { ...partialGov.claims[0], kb_entry_id: null, scheme_or_service: { value: "pm scheme", confidence: "low", ambiguous: true } },
            { ...partialGov.claims[0], kb_entry_id: null, scheme_or_service: { value: "EPFO / Provident Fund", confidence: "medium", ambiguous: false } },
          ],
        },
      }),
    );
    expect(screen.getByText(/too vague to match a specific scheme/i)).toBeInTheDocument();
    expect(screen.getByText(/not in curated reference/i)).toBeInTheDocument();
  });

  it("shows contradicted findings and localises the card in Tamil", async () => {
    renderCard(
      makeResponse({
        government_claim: {
          ...partialGov,
          claim_status: "contradicted_by_curated_kb",
          findings: [{ aspect: "official_link", outcome: "contradicted", detail_en: "Not the official domain.", detail_ta: "அதிகாரப்பூர்வ டொமைன் அல்ல." }],
        },
      }),
    );
    expect(screen.getByText(/conflicts with reference/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "தமிழ்" }));
    expect(screen.getByText("அதிகாரப்பூர்வ டொமைன் அல்ல.")).toBeInTheDocument();
    expect(screen.getByText(/தொகுக்கப்பட்ட நிலையான தரவுத்தொகுப்பைப்/)).toBeInTheDocument();
  });

  it("labels a supported claim cautiously, never as simply 'Verified'", async () => {
    renderCard(makeResponse({ government_claim: { ...partialGov, claim_status: "supported_by_curated_kb" } }));
    const status = screen.getByTestId("gov-status");
    expect(status).toHaveTextContent("Matches official reference — message not confirmed");
    expect(status).not.toHaveTextContent(/^verified$/i);
    await userEvent.click(screen.getByRole("button", { name: "தமிழ்" }));
    expect(status).toHaveTextContent(/செய்தி உறுதிசெய்யப்படவில்லை/);
  });

  it("shows curated guidance and official sites, in Tamil too", async () => {
    renderCard(
      makeResponse({
        government_claim: { ...partialGov, safe_guidance_en: ["Use pmkisan.gov.in."], safe_guidance_ta: ["pmkisan.gov.in-ஐப் பயன்படுத்தவும்."] },
      }),
    );
    expect(screen.getByTestId("gov-guidance")).toHaveTextContent("Use pmkisan.gov.in.");
    const link = within(screen.getByTestId("gov-official-sites")).getByRole("link");
    expect(link).toHaveAttribute("href", "https://pmkisan.gov.in/");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    await userEvent.click(screen.getByRole("button", { name: "தமிழ்" }));
    expect(screen.getByTestId("gov-guidance")).toHaveTextContent("pmkisan.gov.in-ஐப் பயன்படுத்தவும்.");
  });

  it("shows no guidance or official site without a curated match, and drops non-government URLs", () => {
    const { unmount } = render(
      <LanguageProvider>
        <RiskCard
          result={makeResponse({
            government_claim: { ...partialGov, matched_kb_entries: [], safe_guidance_en: ["Should not appear"] },
          })}
          onReset={vi.fn()}
        />
      </LanguageProvider>,
    );
    expect(screen.queryByTestId("gov-guidance")).not.toBeInTheDocument();
    expect(screen.queryByTestId("gov-official-sites")).not.toBeInTheDocument();
    unmount();

    const lookalike = { ...partialGov.sources[0], official_url: "https://pmkisan.gov.in.payment-desk.cc/" };
    renderCard(makeResponse({ government_claim: { ...partialGov, sources: [lookalike] } }));
    expect(screen.queryByTestId("gov-official-sites")).not.toBeInTheDocument();
  });
});

describe("AIExplanation", () => {
  it("labels a Gemini explanation as AI-generated and not official", () => {
    renderCard(makeResponse({ explanation: { en: "AI text", ta: "AI உரை", generated_by: "gemini", ai_status: "generated", note: null } }));
    expect(screen.getByTestId("ai-status")).toHaveTextContent("AI-generated summary");
    expect(screen.getByText(/not an official statement/i)).toBeInTheDocument();
  });

  it.each([
    ["unavailable", /AI explanation unavailable — Standard explanation/],
    ["rejected", /discarded by safety checks/],
    ["disabled", /turned off/],
  ] as const)("shows the %s fallback state", (status, label) => {
    renderCard(
      makeResponse({
        explanation: { en: "Template text", ta: "வார்ப்புரு", generated_by: "template", ai_status: status, note: "Fallback note" },
      }),
    );
    expect(screen.getByTestId("ai-status")).toHaveTextContent(label);
    expect(screen.getByText("Fallback note")).toBeInTheDocument();
  });
});

describe("ProviderStatus and missing data", () => {
  it("summarises provider states without implying safety", () => {
    renderCard(makeResponse({ explanation: { en: "x", ta: "y", generated_by: "template", ai_status: "unavailable", note: null } }));
    const panel = screen.getByTestId("provider-status");
    expect(within(panel).getByText(/link reputation/i).nextSibling).toHaveTextContent("Unavailable");
    // The fixture's configured provider is "template", so no provider name is shown.
    expect(within(panel).getByText("AI explanation").nextSibling).toHaveTextContent(/unavailable/i);
  });

  it.each([
    ["groq", "AI explanation (Groq)"],
    ["gemini", "AI explanation (Gemini)"],
  ] as const)("names the configured AI provider (%s), never a hardcoded one", (provider, label) => {
    const base = makeResponse();
    renderCard(makeResponse({ provider_flags: { ...base.provider_flags, ai_provider: provider, ai_enabled: true } }));
    const panel = screen.getByTestId("provider-status");
    expect(within(panel).getByText(label)).toBeInTheDocument();
    expect(within(panel).queryByText(provider === "groq" ? /Gemini/ : /Groq/)).not.toBeInTheDocument();
  });

  it("renders Phase 2 missing-data codes in both languages", async () => {
    renderCard(makeResponse({ missing_metadata: ["government_records_not_checked_live", "government_claim_too_vague_to_compare"] }));
    const list = screen.getByTestId("missing-data");
    expect(list).toHaveTextContent(/not checked live/);
    await userEvent.click(screen.getByRole("button", { name: "தமிழ்" }));
    expect(list).toHaveTextContent(/நேரடியாகச் சரிபார்க்கப்படவில்லை/);
  });

  it("uses Tamil limitations and verdict scope from the backend", async () => {
    renderCard(
      makeResponse({
        limitations: ["English limitation"],
        limitations_ta: ["தமிழ் வரம்பு"],
        risk: { ...makeResponse().risk, verdict_scope_ta: "தமிழ் வரம்பெல்லை" },
      }),
    );
    await userEvent.click(screen.getByRole("button", { name: "தமிழ்" }));
    expect(screen.getByTestId("limitations")).toHaveTextContent("தமிழ் வரம்பு");
    expect(screen.getByText("தமிழ் வரம்பெல்லை")).toBeInTheDocument();
  });
});
