import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { isValidUrlInput } from "../components/InputPanel";
import { LanguageProvider } from "../i18n/LanguageContext";
import { Analyze } from "../pages/Analyze";
import { makeResponse } from "./fixtures";

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

function renderAnalyze() {
  render(
    <LanguageProvider>
      <MemoryRouter>
        <Analyze />
      </MemoryRouter>
    </LanguageProvider>,
  );
}

async function typeAndReview(text: string) {
  await userEvent.type(screen.getByLabelText(/message content to analyze/i), text);
  await userEvent.click(screen.getByRole("button", { name: /review & check risk/i }));
}

describe("Analyze flow", () => {
  it("does not call the API before review and confirmation", async () => {
    renderAnalyze();
    expect(screen.getByRole("button", { name: /review & check risk/i })).toBeDisabled();
    await typeAndReview("Share your OTP now");
    expect(screen.getByRole("heading", { name: /review submitted content/i })).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends the confirmed request and renders the report", async () => {
    let resolve!: (r: Response) => void;
    fetchMock.mockReturnValue(new Promise<Response>((r) => (resolve = r)));
    renderAnalyze();
    await typeAndReview("Share your OTP now");
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /confirm & analyze/i }));

    expect(screen.getByText(/analysing your message/i)).toBeInTheDocument();

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/v1\/analyze$/);
    const payload = JSON.parse((init.body as FormData).get("payload") as string);
    expect(payload.content).toEqual({ body: "Share your OTP now", source: "manual_entry", user_confirmed: true });
    expect((init.body as FormData).get("screenshot")).toBeNull();

    resolve(new Response(JSON.stringify(makeResponse()), { status: 200 }));
    await waitFor(() => expect(screen.getByTestId("risk-level")).toHaveTextContent("CRITICAL"));
  });

  it("shows a network failure without implying safety and allows retry", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    renderAnalyze();
    await typeAndReview("hello");
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /confirm & analyze/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/could not be reached/i);
    expect(alert).toHaveTextContent(/not a safe verdict/i);

    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(makeResponse()), { status: 200 }));
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    await waitFor(() => expect(screen.getByTestId("risk-level")).toBeInTheDocument());
  });

  it("surfaces backend validation messages", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ error: "validation_error", detail: "content.body exceeds 8000 characters" }), { status: 422 }));
    renderAnalyze();
    await typeAndReview("hello");
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /confirm & analyze/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/exceeds 8000 characters/);
  });

  it("uses url_input provenance for the URL tab and validates input", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(makeResponse()), { status: 200 }));
    renderAnalyze();
    await userEvent.click(screen.getByRole("tab", { name: /check url/i }));
    const input = screen.getByLabelText(/web address/i);
    await userEvent.type(input, "not a url");
    expect(screen.getByRole("alert")).toHaveTextContent(/single web address/i);
    expect(screen.getByRole("button", { name: /review & check risk/i })).toBeDisabled();

    await userEvent.clear(input);
    await userEvent.type(input, "pm-kisan-gov.in/verify");
    await userEvent.click(screen.getByRole("button", { name: /review & check risk/i }));
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /confirm & analyze/i }));
    const payload = JSON.parse((fetchMock.mock.calls[0][1].body as FormData).get("payload") as string);
    expect(payload.content.source).toBe("url_input");
  });

  it("uploads a screenshot with attachment metadata and rejects bad files", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(makeResponse()), { status: 200 }));
    renderAnalyze();
    await userEvent.click(screen.getByRole("tab", { name: /upload screenshot/i }));
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

    await userEvent.upload(fileInput, new File(["gif"], "x.gif", { type: "image/gif" }), { applyAccept: false });
    expect(screen.getByRole("alert")).toHaveTextContent(/only png, jpeg, or webp/i);

    await userEvent.upload(fileInput, new File([new Uint8Array([137, 80, 78, 71])], "sms.png", { type: "image/png" }));
    expect(screen.getByText(/automatic text extraction is not available/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /review & check risk/i }));
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /confirm & analyze/i }));

    const form = fetchMock.mock.calls[0][1].body as FormData;
    const payload = JSON.parse(form.get("payload") as string);
    expect(payload.content.source).toBe("ocr");
    expect(payload.attachment).toMatchObject({ type: "screenshot", provenance: "user_upload", original_filename: "sms.png" });
    expect(form.get("screenshot")).toBeInstanceOf(File);
  });

  it("validates URL input shape", () => {
    expect(isValidUrlInput("example.in/page")).toBe(true);
    expect(isValidUrlInput("two words.com")).toBe(false);
    expect(isValidUrlInput("nodot")).toBe(false);
  });
});
