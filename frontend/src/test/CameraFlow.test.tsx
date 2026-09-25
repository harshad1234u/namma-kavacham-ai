import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LanguageProvider } from "../i18n/LanguageContext";
import { Analyze } from "../pages/Analyze";
import { recognizeImage } from "../services/ocr";
import { makeResponse } from "./fixtures";

vi.mock("../services/ocr", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/ocr")>()),
  recognizeImage: vi.fn(),
}));
const ocrMock = vi.mocked(recognizeImage);
const fetchMock = vi.fn();
const getUserMedia = vi.fn();
const frame = { w: 1280, h: 720 };
let blob: Blob | null;

type FakeStream = MediaStream & { track: { stop: ReturnType<typeof vi.fn> } };
function fakeStream(): FakeStream {
  const track = { stop: vi.fn() };
  return { track, getTracks: () => [track] } as unknown as FakeStream;
}
const domError = (name: string, message = "") => Object.assign(new Error(message), { name });

beforeEach(() => {
  fetchMock.mockReset();
  ocrMock.mockReset();
  getUserMedia.mockReset();
  frame.w = 1280;
  frame.h = 720;
  blob = new Blob(["jpeg-bytes"], { type: "image/jpeg" });
  vi.stubGlobal("fetch", fetchMock);
  Object.defineProperty(window, "isSecureContext", { value: true, configurable: true });
  Object.defineProperty(navigator, "mediaDevices", { value: { getUserMedia }, configurable: true });
  Object.defineProperty(HTMLVideoElement.prototype, "videoWidth", { get: () => frame.w, configurable: true });
  Object.defineProperty(HTMLVideoElement.prototype, "videoHeight", { get: () => frame.h, configurable: true });
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({ drawImage: vi.fn() } as unknown as CanvasRenderingContext2D);
  vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation((cb) => cb(blob));
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function renderAnalyze() {
  return render(
    <LanguageProvider>
      <MemoryRouter>
        <Analyze />
      </MemoryRouter>
    </LanguageProvider>,
  );
}

const imageTab = () => screen.getByRole("tab", { name: /screenshot \/ photo/i });
const status = () => screen.getByRole("status");

async function openCameraUi(stream: FakeStream | Error = fakeStream()) {
  if (stream instanceof Error) getUserMedia.mockRejectedValueOnce(stream);
  else getUserMedia.mockResolvedValueOnce(stream);
  const view = renderAnalyze();
  await userEvent.click(imageTab());
  await userEvent.click(screen.getByRole("button", { name: /take a photo/i }));
  return view;
}

async function captureAndUse() {
  await waitFor(() => expect(screen.getByRole("button", { name: /^capture$/i })).toBeEnabled());
  await userEvent.click(screen.getByRole("button", { name: /^capture$/i }));
  await userEvent.click(await screen.findByRole("button", { name: /use photo/i }));
}

async function extract(text: string) {
  ocrMock.mockResolvedValueOnce({ text, confidence: 90 });
  await userEvent.click(screen.getByRole("button", { name: /extract text/i }));
  await waitFor(() => expect(screen.getByLabelText(/text from the screenshot/i)).toHaveValue(text));
}

async function confirmAndSend() {
  fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(makeResponse()), { status: 200 }));
  await userEvent.click(screen.getByRole("button", { name: /review & check risk/i }));
  expect(fetchMock).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: /confirm & analyze/i })).toBeDisabled();
  await userEvent.click(screen.getByRole("checkbox"));
  await userEvent.click(screen.getByRole("button", { name: /confirm & analyze/i }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  const form = fetchMock.mock.calls[0][1].body as FormData;
  return { form, payload: JSON.parse(form.get("payload") as string) };
}

describe("Camera capture", () => {
  it("does not request the camera on load or when opening the tab, only after the user taps", async () => {
    renderAnalyze();
    await userEvent.click(imageTab());
    expect(getUserMedia).not.toHaveBeenCalled();
    expect(screen.getByText(/choose screenshot/i)).toBeInTheDocument();

    getUserMedia.mockResolvedValueOnce(fakeStream());
    await userEvent.click(screen.getByRole("button", { name: /take a photo/i }));
    expect(getUserMedia).toHaveBeenCalledTimes(1);
    expect(getUserMedia.mock.calls[0][0]).toMatchObject({ audio: false, video: { facingMode: { ideal: "environment" } } });
  });

  it("shows the live preview once the stream starts", async () => {
    const stream = fakeStream();
    let resolve!: (s: MediaStream) => void;
    getUserMedia.mockReturnValueOnce(new Promise<MediaStream>((r) => (resolve = r)));
    renderAnalyze();
    await userEvent.click(imageTab());
    await userEvent.click(screen.getByRole("button", { name: /take a photo/i }));
    expect(status()).toHaveTextContent(/starting the camera/i);
    expect(screen.getByRole("button", { name: /^capture$/i })).toBeDisabled(); // permission prompt still open

    await act(async () => resolve(stream));
    await waitFor(() => expect(status()).toHaveTextContent(/camera is on/i));
    const video = screen.getByLabelText(/live camera preview/i) as HTMLVideoElement;
    expect(video.srcObject).toBe(stream);
    expect(video).toHaveAttribute("playsinline");
    expect(screen.getByRole("button", { name: /^capture$/i })).toBeEnabled();
  });

  it("stops the camera on capture, shows the photo, and restarts cleanly on retake", async () => {
    const first = fakeStream();
    await openCameraUi(first);
    await waitFor(() => expect(screen.getByRole("button", { name: /^capture$/i })).toBeEnabled());
    await userEvent.click(screen.getByRole("button", { name: /^capture$/i }));

    expect(first.track.stop).toHaveBeenCalled();
    expect(screen.getByRole("img", { name: /captured photo/i })).toBeInTheDocument();
    expect(status()).toHaveTextContent(/camera is now off/i);
    expect(screen.queryByLabelText(/live camera preview/i)).not.toBeInTheDocument();
    expect(ocrMock).not.toHaveBeenCalled(); // nothing runs until the user chooses to

    const second = fakeStream();
    getUserMedia.mockResolvedValueOnce(second);
    await userEvent.click(screen.getByRole("button", { name: /retake/i }));
    await waitFor(() => expect(status()).toHaveTextContent(/camera is on/i));
    expect(getUserMedia).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("img", { name: /captured photo/i })).not.toBeInTheDocument();
    expect((screen.getByLabelText(/live camera preview/i) as HTMLVideoElement).srcObject).toBe(second);
  });

  it("feeds the photo into local OCR and sends only confirmed text with camera provenance", async () => {
    await openCameraUi();
    await captureAndUse();
    expect(screen.getByText("Camera photo")).toBeInTheDocument();
    expect(screen.getByLabelText(/language in the screenshot/i)).toBeInTheDocument();
    expect(ocrMock).not.toHaveBeenCalled();

    await extract("Pay Rs 50 fee now");
    expect(ocrMock.mock.calls[0][0]).toMatchObject({ type: "image/jpeg" });
    const { form, payload } = await confirmAndSend();
    expect(payload.content).toEqual({ body: "Pay Rs 50 fee now", source: "ocr", user_confirmed: true, image_origin: "camera" });
    expect(payload.attachment).toBeUndefined();
    expect([...form.keys()]).toEqual(["payload"]);
  });

  it("marks corrected camera OCR as user_corrected_ocr", async () => {
    await openCameraUi();
    await captureAndUse();
    await extract("Pay Rs 5O fee");
    await userEvent.type(screen.getByLabelText(/text from the screenshot/i), "{Backspace}{Backspace}{Backspace}{Backspace}{Backspace}0 fee");
    const { payload } = await confirmAndSend();
    expect(payload.content).toMatchObject({ body: "Pay Rs 50 fee", source: "user_corrected_ocr", image_origin: "camera" });
  });

  it("marks camera OCR text the user replaced as manual_entry tied to the camera photo", async () => {
    await openCameraUi();
    await captureAndUse();
    await extract("garbled");
    const box = screen.getByLabelText(/text from the screenshot/i);
    await userEvent.clear(box);
    await userEvent.type(box, "Share OTP now");
    const { payload } = await confirmAndSend();
    expect(payload.content).toMatchObject({ source: "manual_entry", image_origin: "camera" });
  });

  it("uses plain manual_entry with no image origin when the camera is abandoned", async () => {
    const stream = fakeStream();
    await openCameraUi(stream);
    await waitFor(() => expect(status()).toHaveTextContent(/camera is on/i));
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(stream.track.stop).toHaveBeenCalled();
    expect(screen.queryByTestId("camera")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: /paste \/ type/i }));
    await userEvent.type(screen.getByLabelText(/message content to analyze/i), "Share OTP now");
    const { payload } = await confirmAndSend();
    expect(payload.content).toEqual({ body: "Share OTP now", source: "manual_entry", user_confirmed: true });
  });

  it("explains a denied permission and offers upload instead", async () => {
    const click = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => {});
    await openCameraUi(domError("NotAllowedError", "Permission denied"));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/permission was denied/i);
    expect(alert).toHaveTextContent(/upload a screenshot instead/i);

    await userEvent.click(screen.getByRole("button", { name: /upload instead/i }));
    expect(screen.queryByTestId("camera")).not.toBeInTheDocument();
    expect(click).toHaveBeenCalled();
    expect(screen.getByText(/choose screenshot/i)).toBeInTheDocument();
  });

  it.each([
    [domError("NotAllowedError", "Permission dismissed"), /permission was not given/i],
    [domError("NotFoundError"), /no camera was found/i],
    [domError("NotReadableError"), /in use by another app/i],
    [new Error("weird"), /could not be started/i],
  ])("shows a clear message for %s", async (err, message) => {
    await openCameraUi(err as Error);
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.getByRole("button", { name: /upload instead/i })).toBeInTheDocument();
  });

  it("lets the user retry after a dismissed prompt", async () => {
    await openCameraUi(domError("NotAllowedError", "Permission dismissed"));
    await screen.findByRole("alert");
    getUserMedia.mockResolvedValueOnce(fakeStream());
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    await waitFor(() => expect(status()).toHaveTextContent(/camera is on/i));
  });

  it("reports unsupported browsers and insecure pages without calling getUserMedia", async () => {
    Object.defineProperty(navigator, "mediaDevices", { value: undefined, configurable: true });
    const view = renderAnalyze();
    await userEvent.click(imageTab());
    await userEvent.click(screen.getByRole("button", { name: /take a photo/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/does not support camera access/i);
    view.unmount();

    Object.defineProperty(window, "isSecureContext", { value: false, configurable: true });
    renderAnalyze();
    await userEvent.click(imageTab());
    await userEvent.click(screen.getByRole("button", { name: /take a photo/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/secure \(https\) connection/i);
    expect(getUserMedia).not.toHaveBeenCalled();
  });

  it("stops the camera and shows an error when there is no frame to capture", async () => {
    const stream = fakeStream();
    await openCameraUi(stream);
    await waitFor(() => expect(status()).toHaveTextContent(/camera is on/i));
    frame.w = 0;
    await userEvent.click(screen.getByRole("button", { name: /^capture$/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/photo could not be taken/i);
    expect(stream.track.stop).toHaveBeenCalled();
  });

  it("stops the camera and shows an error when the frame cannot be converted", async () => {
    const stream = fakeStream();
    await openCameraUi(stream);
    await waitFor(() => expect(status()).toHaveTextContent(/camera is on/i));
    blob = null;
    await userEvent.click(screen.getByRole("button", { name: /^capture$/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/could not be saved as an image/i);
    expect(stream.track.stop).toHaveBeenCalled();
  });

  it("stops the camera when switching tabs and does not restart it on return", async () => {
    const stream = fakeStream();
    await openCameraUi(stream);
    await waitFor(() => expect(status()).toHaveTextContent(/camera is on/i));
    await userEvent.click(screen.getByRole("tab", { name: /check url/i }));
    expect(stream.track.stop).toHaveBeenCalled();
    await userEvent.click(imageTab());
    expect(screen.queryByTestId("camera")).not.toBeInTheDocument();
    expect(getUserMedia).toHaveBeenCalledTimes(1);
  });

  it("stops the camera on unmount (navigating away)", async () => {
    const stream = fakeStream();
    const view = await openCameraUi(stream);
    await waitFor(() => expect(status()).toHaveTextContent(/camera is on/i));
    view.unmount();
    expect(stream.track.stop).toHaveBeenCalled();
  });

  it("releases a stream that arrives after unmount during initialisation", async () => {
    let resolve!: (s: MediaStream) => void;
    getUserMedia.mockReturnValueOnce(new Promise<MediaStream>((r) => (resolve = r)));
    const view = renderAnalyze();
    await userEvent.click(imageTab());
    await userEvent.click(screen.getByRole("button", { name: /take a photo/i }));
    expect(status()).toHaveTextContent(/starting the camera/i);
    view.unmount();

    const late = fakeStream();
    await act(async () => resolve(late));
    expect(late.track.stop).toHaveBeenCalled();
  });

  it("scrolls the camera into view without breaking when scrollIntoView returns a Promise", async () => {
    // Newer Chromium returns a Promise here; returning it from an effect crashed the component on unmount.
    const scroll = vi.fn(() => Promise.resolve());
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", { value: scroll, configurable: true, writable: true });
    const stream = fakeStream();
    const view = await openCameraUi(stream);
    await waitFor(() => expect(status()).toHaveTextContent(/camera is on/i));
    expect(scroll).toHaveBeenCalledWith({ block: "start", behavior: "smooth" });
    expect(() => view.unmount()).not.toThrow();
    expect(stream.track.stop).toHaveBeenCalled();
    delete (HTMLElement.prototype as { scrollIntoView?: unknown }).scrollIntoView;
  });

  it("keeps the preview and controls within a phone-width layout", async () => {
    await openCameraUi();
    await waitFor(() => expect(status()).toHaveTextContent(/camera is on/i));
    const video = screen.getByLabelText(/live camera preview/i);
    // jsdom has no layout engine: assert the constraints that keep it inside a 390px viewport.
    expect(video).toHaveClass("w-full", "max-h-[50vh]", "object-contain");
    const controls = screen.getByRole("button", { name: /^capture$/i }).parentElement;
    expect(controls).toHaveClass("flex-wrap");
    for (const button of controls?.querySelectorAll("button") ?? []) expect(button).toHaveClass("min-h-11");
  });
});
