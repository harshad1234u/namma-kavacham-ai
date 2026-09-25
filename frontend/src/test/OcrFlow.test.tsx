import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LanguageProvider } from "../i18n/LanguageContext";
import { Analyze } from "../pages/Analyze";
import { OcrError, recognizeImage, type OcrProgress } from "../services/ocr";
import { makeResponse } from "./fixtures";

vi.mock("../services/ocr", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/ocr")>()),
  recognizeImage: vi.fn(),
}));
const ocrMock = vi.mocked(recognizeImage);
const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  ocrMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

const png = () => new File([new Uint8Array([137, 80, 78, 71])], "sms.png", { type: "image/png" });
const textBox = () => screen.getByLabelText(/text from the screenshot/i);
const reviewButton = () => screen.getByRole("button", { name: /review & check risk/i });

async function uploadImage(file: File = png()) {
  render(
    <LanguageProvider>
      <MemoryRouter>
        <Analyze />
      </MemoryRouter>
    </LanguageProvider>,
  );
  await userEvent.click(screen.getByRole("tab", { name: /screenshot \/ photo/i }));
  await userEvent.upload(document.querySelector('input[type="file"]') as HTMLInputElement, file, { applyAccept: false });
}

async function confirmAndSend() {
  fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(makeResponse()), { status: 200 }));
  await userEvent.click(reviewButton());
  await userEvent.click(screen.getByRole("checkbox"));
  await userEvent.click(screen.getByRole("button", { name: /confirm & analyze/i }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  const form = fetchMock.mock.calls[0][1].body as FormData;
  return { form, payload: JSON.parse(form.get("payload") as string) };
}

describe("Screenshot OCR", () => {
  it("rejects unsupported and oversized images", async () => {
    await uploadImage(new File(["gif"], "x.gif", { type: "image/gif" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/only png, jpeg, or webp/i);
    const big = png();
    Object.defineProperty(big, "size", { value: 8 * 1024 * 1024 + 1 });
    await userEvent.upload(document.querySelector('input[type="file"]') as HTMLInputElement, big);
    expect(screen.getByRole("alert")).toHaveTextContent(/larger than 8 mb/i);
    expect(ocrMock).not.toHaveBeenCalled();
  });

  it("shows a preview and language choice, and does not start OCR or allow review until text exists", async () => {
    await uploadImage();
    expect(screen.getByText("sms.png")).toBeInTheDocument();
    expect(screen.getByLabelText(/language in the screenshot/i)).toHaveValue("eng+tam");
    expect(ocrMock).not.toHaveBeenCalled();
    expect(reviewButton()).toBeDisabled();
  });

  it("reads text locally and sends only the confirmed text with ocr provenance", async () => {
    ocrMock.mockResolvedValueOnce({ text: "Pay Rs 50 fee now", confidence: 91 });
    await uploadImage();
    await userEvent.selectOptions(screen.getByLabelText(/language in the screenshot/i), "tam");
    await userEvent.click(screen.getByRole("button", { name: /extract text/i }));

    expect(ocrMock.mock.calls[0][1]).toBe("tam");
    await waitFor(() => expect(textBox()).toHaveValue("Pay Rs 50 fee now"));
    expect(screen.getByText(/can contain mistakes/i)).toBeInTheDocument();
    expect(screen.getByText(/recognition confidence/i)).toHaveTextContent("91%");

    await userEvent.click(reviewButton());
    expect(screen.getByText(/screenshot text, read automatically/i)).toBeInTheDocument();
    expect(screen.getByText(/image stays on this device/i)).toBeInTheDocument();
    expect(screen.getByText("Uploaded image")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /confirm & analyze/i })).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalled();

    fetchMock.mockReset();
    await userEvent.click(screen.getByRole("button", { name: /back/i }));
    const { form, payload } = await confirmAndSend();
    expect(payload.content).toEqual({ body: "Pay Rs 50 fee now", source: "ocr", user_confirmed: true, image_origin: "upload" });
    expect(payload.attachment).toBeUndefined();
    expect(form.get("screenshot")).toBeNull();
  });

  it("marks corrected OCR text as user_corrected_ocr", async () => {
    ocrMock.mockResolvedValueOnce({ text: "Pay Rs 5O fee", confidence: 72 });
    await uploadImage();
    await userEvent.click(screen.getByRole("button", { name: /extract text/i }));
    await waitFor(() => expect(textBox()).toHaveValue("Pay Rs 5O fee"));
    // Fix the misread "O" in place.
    await userEvent.type(textBox(), "{Backspace}{Backspace}{Backspace}{Backspace}{Backspace}0 fee");

    const { payload } = await confirmAndSend();
    expect(payload.content.body).toBe("Pay Rs 50 fee");
    expect(payload.content.source).toBe("user_corrected_ocr");
  });

  it("marks OCR text the user emptied and retyped as manual_entry, still tied to the image", async () => {
    ocrMock.mockResolvedValueOnce({ text: "garbled 0CR", confidence: 30 });
    await uploadImage();
    await userEvent.click(screen.getByRole("button", { name: /extract text/i }));
    await waitFor(() => expect(textBox()).toHaveValue("garbled 0CR"));
    await userEvent.clear(textBox());
    await userEvent.type(textBox(), "Share OTP now");

    const { payload } = await confirmAndSend();
    expect(payload.content).toMatchObject({ source: "manual_entry", image_origin: "upload" });
  });

  it("marks OCR text replaced during review as manual_entry", async () => {
    ocrMock.mockResolvedValueOnce({ text: "garbled 0CR", confidence: 30 });
    await uploadImage();
    await userEvent.click(screen.getByRole("button", { name: /extract text/i }));
    await waitFor(() => expect(textBox()).toHaveValue("garbled 0CR"));
    await userEvent.click(reviewButton());
    const payloadBox = screen.getByLabelText(/message payload/i);
    await userEvent.clear(payloadBox);
    await userEvent.type(payloadBox, "Share OTP now");
    expect(screen.getByText(/input provenance/i)).toHaveTextContent(/typed by you/i);

    // Going back keeps the replacement: the text is no longer OCR output.
    await userEvent.click(screen.getByRole("button", { name: /back/i }));
    const { payload } = await confirmAndSend();
    expect(payload.content).toMatchObject({ body: "Share OTP now", source: "manual_entry", image_origin: "upload" });
  });

  it("shows progress, locks the text while running, and can be cancelled", async () => {
    ocrMock.mockImplementationOnce((_file, _lang, opts) => {
      opts?.onProgress?.({ stage: "recognizing", progress: 0.4 } satisfies OcrProgress);
      return new Promise((_, reject) => opts?.signal?.addEventListener("abort", () => reject(new OcrError("cancelled"))));
    });
    await uploadImage();
    await userEvent.click(screen.getByRole("button", { name: /extract text/i }));

    expect(screen.getByRole("progressbar")).toHaveAttribute("value", "0.4");
    expect(screen.getByText(/reading text on this device… 40%/i)).toBeInTheDocument();
    expect(textBox()).toBeDisabled();
    expect(reviewButton()).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: /^cancel$/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/cancelled/i);
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    expect(textBox()).toBeEnabled();
    expect(screen.getByRole("button", { name: /extract again/i })).toBeInTheDocument();
  });

  it("handles an empty result and falls back to manual entry", async () => {
    ocrMock.mockResolvedValueOnce({ text: "", confidence: 0 });
    await uploadImage();
    await userEvent.click(screen.getByRole("button", { name: /extract text/i }));
    expect(await screen.findByText(/no text was found/i)).toBeInTheDocument();
    expect(reviewButton()).toBeDisabled();

    await userEvent.type(textBox(), "Share OTP now");
    const { payload } = await confirmAndSend();
    expect(payload.content.source).toBe("manual_entry");
  });

  it("explains an OCR failure and keeps manual entry available", async () => {
    ocrMock.mockRejectedValueOnce(new OcrError("init"));
    await uploadImage();
    await userEvent.click(screen.getByRole("button", { name: /extract text/i }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/language data could not be loaded/i);
    expect(alert).toHaveTextContent(/type or paste the message text/i);

    ocrMock.mockResolvedValueOnce({ text: "Share OTP now", confidence: 80 });
    await userEvent.click(screen.getByRole("button", { name: /extract again/i }));
    await waitFor(() => expect(textBox()).toHaveValue("Share OTP now"));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("warns when recognition quality is low", async () => {
    ocrMock.mockResolvedValueOnce({ text: "P4y R5 fe", confidence: 41 });
    await uploadImage();
    await userEvent.click(screen.getByRole("button", { name: /extract text/i }));
    expect(await screen.findByText(/low recognition quality/i)).toBeInTheDocument();
  });

  it("clears text from a previous image when a new one is chosen", async () => {
    ocrMock.mockResolvedValueOnce({ text: "Old screenshot text", confidence: 90 });
    await uploadImage();
    await userEvent.click(screen.getByRole("button", { name: /extract text/i }));
    await waitFor(() => expect(textBox()).toHaveValue("Old screenshot text"));

    await userEvent.click(screen.getByRole("button", { name: /remove/i }));
    await userEvent.upload(document.querySelector('input[type="file"]') as HTMLInputElement, png());
    expect(textBox()).toHaveValue("");
    expect(screen.getByRole("button", { name: /extract text/i })).toBeInTheDocument();
  });
});
