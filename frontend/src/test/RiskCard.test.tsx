import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LanguageToggle } from "../components/LanguageToggle";
import { RiskCard } from "../components/RiskCard";
import { LanguageProvider } from "../i18n/LanguageContext";
import type { AnalyzeResponse } from "../types/analysis";
import { makeResponse, vtResult } from "./fixtures";

function renderCard(result: AnalyzeResponse) {
  render(
    <LanguageProvider>
      <LanguageToggle />
      <RiskCard result={result} onReset={vi.fn()} />
    </LanguageProvider>,
  );
}

describe("RiskCard", () => {
  it("renders level, evidence, and the not-a-probability note", () => {
    renderCard(makeResponse());
    expect(screen.getByTestId("risk-level")).toHaveTextContent("CRITICAL");
    expect(screen.getByText(/not a probability/i)).toBeInTheDocument();
    expect(screen.getByText("MSG-CRED-01")).toBeInTheDocument();
    expect(screen.getByText(/asks you to share or enter an OTP/)).toBeInTheDocument();
  });

  it("shows an unavailable VirusTotal check as NOT checked, never safe", () => {
    renderCard(makeResponse());
    const panel = screen.getByTestId("vt-panel");
    expect(panel).toHaveTextContent(/link NOT checked/i);
    expect(panel).not.toHaveTextContent(/clean|no vendor flagged/i);
    expect(screen.getByText(/could not be completed — the link was not checked/i)).toBeInTheDocument();
  });

  it("shows a disabled lookup as not checked", () => {
    renderCard(
      makeResponse({
        url_intelligence: {
          ...makeResponse().url_intelligence,
          provider_enabled: false,
          provider_result: vtResult({ unavailable_reason: "disabled_by_configuration" }),
        },
      }),
    );
    expect(screen.getByTestId("vt-panel")).toHaveTextContent(/not checked — lookup disabled/i);
  });

  it("labels a not_found report as not proof of safety", () => {
    renderCard(
      makeResponse({
        url_intelligence: {
          ...makeResponse().url_intelligence,
          provider_result: vtResult({ status: "not_found", available: true, unavailable_reason: null, note: "No report." }),
        },
      }),
    );
    expect(screen.getByTestId("vt-panel")).toHaveTextContent(/no report exists — not proof of safety/i);
  });

  it("shows vendor counts for a malicious link", () => {
    renderCard(
      makeResponse({
        url_intelligence: {
          ...makeResponse().url_intelligence,
          provider_result: vtResult({
            status: "malicious",
            available: true,
            unavailable_reason: null,
            engine_stats: { malicious: 4, suspicious: 0, harmless: 60, undetected: 28, timeout: 0 },
            engines_total: 92,
          }),
        },
      }),
    );
    expect(within(screen.getByTestId("vt-panel")).getByText("4 / 92")).toBeInTheDocument();
  });

  it("presents insufficient content as not assessed rather than LOW", () => {
    renderCard(makeResponse({ risk: { ...makeResponse().risk, assessment_status: "insufficient_content", level: "LOW", score: 0 } }));
    expect(screen.getAllByText(/not enough content to assess/i).length).toBeGreaterThan(0);
    expect(screen.queryByTestId("risk-level")).not.toBeInTheDocument();
  });

  it("switches report content to Tamil", async () => {
    renderCard(makeResponse());
    await userEvent.click(screen.getByRole("button", { name: "தமிழ்" }));
    expect(screen.getByText("செய்தி OTP-ஐப் பகிரக் கேட்கிறது.")).toBeInTheDocument();
    expect(screen.getByText("வலுவான மோசடிக் குறிகள் கண்டறியப்பட்டன.")).toBeInTheDocument();
    expect(screen.getByText("எந்த OTP-யையும் பகிர வேண்டாம்.")).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("ta");
  });
});
