import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AudioReport } from "../components/report/AudioReport";
import { RiskCard } from "../components/RiskCard";
import { LanguageProvider } from "../i18n/LanguageContext";
import { Analyze } from "../pages/Analyze";
import type { AnalyzeResponse } from "../types/analysis";
import { makeResponse } from "./fixtures";

class FakeUtterance {
  lang = "";
  voice: SpeechSynthesisVoice | null = null;
  rate = 1;
  onend: (() => void) | null = null;
  onerror: ((e: { error: string }) => void) | null = null;
  constructor(public text: string) {}
}

const voice = (lang: string, name: string, localService = true) => ({ lang, name, localService }) as SpeechSynthesisVoice;
const EN = voice("en-IN", "Local English (India)");
const TA = voice("ta-IN", "Local Tamil");

function makeSynth(initialVoices: SpeechSynthesisVoice[]) {
  const listeners = new Set<() => void>();
  const synth = {
    voices: initialVoices,
    paused: false,
    getVoices: vi.fn(() => synth.voices),
    speak: vi.fn((_u: FakeUtterance) => {}),
    cancel: vi.fn(),
    pause: vi.fn(() => (synth.paused = true)),
    resume: vi.fn(() => (synth.paused = false)),
    addEventListener: (_type: string, fn: () => void) => listeners.add(fn),
    removeEventListener: (_type: string, fn: () => void) => listeners.delete(fn),
    loadVoices(voices: SpeechSynthesisVoice[]) {
      synth.voices = voices;
      listeners.forEach((fn) => fn());
    },
    last: () => synth.speak.mock.calls.at(-1)?.[0] as FakeUtterance,
    spoken: () => synth.speak.mock.calls.map(([u]) => (u as FakeUtterance).text),
  };
  return synth;
}
let synth: ReturnType<typeof makeSynth>;

function install(voices: SpeechSynthesisVoice[] = [EN]) {
  synth = makeSynth(voices);
  vi.stubGlobal("speechSynthesis", synth);
  vi.stubGlobal("SpeechSynthesisUtterance", FakeUtterance);
}

beforeEach(() => install());
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function renderAudio(result: AnalyzeResponse = makeResponse()) {
  return render(
    <LanguageProvider>
      <AudioReport key={result.analysis_id} result={result} />
    </LanguageProvider>,
  );
}

const button = (name: RegExp) => screen.getByRole("button", { name });
const finishCurrent = () => act(() => synth.last().onend?.());

describe("Audio report", () => {
  it("renders controls and never speaks on its own", () => {
    renderAudio();
    expect(screen.getByRole("heading", { name: /listen to this report/i })).toBeInTheDocument();
    expect(button(/^listen$/i)).toBeEnabled();
    expect(screen.getByLabelText(/audio language/i)).toHaveValue("en");
    expect(screen.getByLabelText(/speed/i)).toHaveValue("1");
    expect(screen.getByText(/local english \(india\).*nothing is sent online/i)).toBeInTheDocument();
    expect(synth.speak).not.toHaveBeenCalled();
  });

  it("speaks only after Listen, with the English voice, one utterance at a time", async () => {
    renderAudio();
    await userEvent.click(button(/^listen$/i));
    expect(synth.cancel).toHaveBeenCalled(); // clears anything queued before starting
    expect(synth.speak).toHaveBeenCalledTimes(1);
    expect(synth.last()).toMatchObject({ text: "Namma Kavacham risk report.", lang: "en-IN", voice: EN, rate: 1 });
    expect(screen.getByRole("status")).toHaveTextContent(/reading the report aloud/i);
    expect(screen.queryByRole("button", { name: /^listen$/i })).not.toBeInTheDocument();

    // The next sentence is queued only when the previous one ends: no overlap.
    finishCurrent();
    expect(synth.speak).toHaveBeenCalledTimes(2);
    while (!screen.getByRole("status").textContent?.match(/finished/i)) finishCurrent();
    expect(synth.spoken().join(" ")).toContain("1. Do not share any OTP.");
    expect(button(/^listen$/i)).toBeInTheDocument();
  });

  it("pauses and resumes", async () => {
    renderAudio();
    await userEvent.click(button(/^listen$/i));
    await userEvent.click(button(/pause/i));
    expect(synth.pause).toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent(/paused/i);
    await userEvent.click(button(/resume/i));
    expect(synth.resume).toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent(/reading/i);
  });

  it("stops, and ignores callbacks from the stopped speech", async () => {
    renderAudio();
    await userEvent.click(button(/^listen$/i));
    const stale = synth.last();
    synth.cancel.mockClear();
    await userEvent.click(button(/stop/i));
    expect(synth.cancel).toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent(/stopped/i);
    act(() => stale.onend?.());
    expect(synth.speak).toHaveBeenCalledTimes(1);
  });

  it("clears a paused state before cancelling, so the next speech is not stuck", async () => {
    renderAudio();
    await userEvent.click(button(/^listen$/i));
    await userEvent.click(button(/pause/i));
    synth.resume.mockClear();
    await userEvent.click(button(/stop/i));
    expect(synth.cancel).toHaveBeenCalled();
    expect(synth.resume).toHaveBeenCalled();
  });

  it("restarts from the beginning without overlapping", async () => {
    renderAudio();
    await userEvent.click(button(/^listen$/i));
    finishCurrent();
    finishCurrent();
    const stale = synth.last();
    synth.cancel.mockClear();
    await userEvent.click(button(/restart/i));
    expect(synth.cancel).toHaveBeenCalled();
    expect(synth.last().text).toBe("Namma Kavacham risk report.");
    const calls = synth.speak.mock.calls.length;
    act(() => stale.onend?.());
    expect(synth.speak).toHaveBeenCalledTimes(calls);
  });

  it("applies the chosen speed", async () => {
    renderAudio();
    await userEvent.selectOptions(screen.getByLabelText(/speed/i), "1.5");
    await userEvent.click(button(/^listen$/i));
    expect(synth.last().rate).toBe(1.5);
  });

  it("uses a ta-IN voice and Tamil text for Tamil", async () => {
    install([EN, TA]);
    renderAudio();
    await userEvent.selectOptions(screen.getByLabelText(/audio language/i), "ta");
    await userEvent.click(button(/^listen$/i));
    expect(synth.last()).toMatchObject({ text: "நம்ம கவசம் ஆபத்து அறிக்கை.", lang: "ta-IN", voice: TA });
  });

  it("follows the page language by default", () => {
    localStorage.setItem("nk-language", "ta");
    install([EN, TA]);
    renderAudio();
    expect(screen.getByLabelText(/ஒலி மொழி/)).toHaveValue("ta");
  });

  it("says clearly when no Tamil voice exists and does not pretend to speak Tamil", async () => {
    install([EN, voice("ta-IN", "Google Tamil (online)", false)]);
    renderAudio();
    await userEvent.selectOptions(screen.getByLabelText(/audio language/i), "ta");
    expect(screen.getByRole("alert")).toHaveTextContent(/no tamil voice is available/i);
    expect(button(/^listen$/i)).toBeDisabled();
    expect(screen.queryByText(/voice on this device/i)).not.toBeInTheDocument();
    expect(synth.speak).not.toHaveBeenCalled();
  });

  it("cancels speech when the language changes", async () => {
    install([EN, TA]);
    renderAudio();
    await userEvent.click(button(/^listen$/i));
    synth.cancel.mockClear();
    await userEvent.selectOptions(screen.getByLabelText(/audio language/i), "ta");
    expect(synth.cancel).toHaveBeenCalled();
    expect(button(/^listen$/i)).toBeInTheDocument();
  });

  it("waits for voices that load late, then reports none after a timeout", async () => {
    install([]);
    renderAudio();
    expect(screen.getByText(/checking the voices/i)).toBeInTheDocument();
    expect(button(/^listen$/i)).toBeDisabled();
    act(() => synth.loadVoices([EN]));
    expect(button(/^listen$/i)).toBeEnabled();
  });

  it("reports no voice when the browser never provides any", () => {
    vi.useFakeTimers();
    install([]);
    renderAudio();
    act(() => vi.advanceTimersByTime(2000));
    expect(screen.getByRole("alert")).toHaveTextContent(/no english voice/i);
  });

  it("retries a spurious interruption once, then moves on instead of stalling", async () => {
    renderAudio();
    await userEvent.click(button(/^listen$/i));
    const first = synth.last().text;
    act(() => synth.last().onerror?.({ error: "interrupted" }));
    expect(synth.last().text).toBe(first); // retried
    act(() => synth.last().onerror?.({ error: "interrupted" }));
    expect(synth.last().text).not.toBe(first); // skipped after one retry
    expect(screen.getByRole("status")).toHaveTextContent(/reading/i);
  });

  it("shows a real synthesis error", async () => {
    renderAudio();
    await userEvent.click(button(/^listen$/i));
    act(() => synth.last().onerror?.({ error: "synthesis-failed" }));
    expect(screen.getByRole("status")).toHaveTextContent(/could not be read aloud/i);
    expect(button(/^listen$/i)).toBeInTheDocument();
  });

  it("explains when the browser has no speech synthesis", () => {
    vi.stubGlobal("speechSynthesis", undefined);
    delete (window as { speechSynthesis?: unknown }).speechSynthesis;
    renderAudio();
    expect(screen.getByText(/cannot read text aloud/i)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("cancels speech on unmount and when leaving the page", async () => {
    const view = renderAudio();
    await userEvent.click(button(/^listen$/i));
    synth.cancel.mockClear();
    act(() => window.dispatchEvent(new Event("pagehide")));
    expect(synth.cancel).toHaveBeenCalled();
    synth.cancel.mockClear();
    const stale = synth.last();
    view.unmount();
    expect(synth.cancel).toHaveBeenCalled();
    stale.onend?.();
    expect(synth.speak).toHaveBeenCalledTimes(1);
  });

  it("cancels speech when a different report is shown", async () => {
    const view = render(
      <LanguageProvider>
        <RiskCard result={makeResponse({ analysis_id: "a" })} onReset={() => {}} />
      </LanguageProvider>,
    );
    await userEvent.click(button(/^listen$/i));
    synth.cancel.mockClear();
    view.rerender(
      <LanguageProvider>
        <RiskCard result={makeResponse({ analysis_id: "b" })} onReset={() => {}} />
      </LanguageProvider>,
    );
    expect(synth.cancel).toHaveBeenCalled();
    expect(button(/^listen$/i)).toBeInTheDocument();
    expect(synth.speak).toHaveBeenCalledTimes(1);
  });

  it("speaks redacted text, never the raw identifiers", async () => {
    renderAudio(makeResponse({ explanation: { en: "Do not call 98765 43210 or share OTP 4829.", ta: "", generated_by: "groq", note: null } }));
    await userEvent.click(button(/^listen$/i));
    while (!screen.getByRole("status").textContent?.match(/finished/i)) finishCurrent();
    const spoken = synth.spoken().join(" ");
    expect(spoken).not.toMatch(/98765|4829/);
    expect(spoken).toContain("(hidden)");
  });

  it("keeps controls usable at phone width", async () => {
    renderAudio();
    await userEvent.click(button(/^listen$/i));
    const controls = button(/pause/i).parentElement as HTMLElement;
    expect(controls).toHaveClass("flex-wrap");
    for (const b of controls.querySelectorAll("button")) expect(b).toHaveClass("min-h-11");
  });
});

describe("Audio report in the analysis flow", () => {
  it("does not autoplay when the report appears, and stops when starting a new check", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(makeResponse()), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(
      <LanguageProvider>
        <MemoryRouter>
          <Analyze />
        </MemoryRouter>
      </LanguageProvider>,
    );
    await userEvent.type(screen.getByLabelText(/message content to analyze/i), "Share OTP now");
    await userEvent.click(button(/review & check risk/i));
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(button(/confirm & analyze/i));
    await waitFor(() => expect(screen.getByTestId("risk-level")).toBeInTheDocument());
    expect(synth.speak).not.toHaveBeenCalled();

    await userEvent.click(button(/^listen$/i));
    synth.cancel.mockClear();
    await userEvent.click(button(/check another/i));
    expect(synth.cancel).toHaveBeenCalled();
    expect(synth.speak).toHaveBeenCalledTimes(1);
  });
});
