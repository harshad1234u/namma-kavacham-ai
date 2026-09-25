import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const createWorker = vi.fn();
vi.mock("tesseract.js", () => ({ createWorker: (...args: unknown[]) => createWorker(...args) }));

import { OCR_TIMEOUT_MS, recognizeImage } from "../services/ocr";

class FakeWorker {
  static last: FakeWorker | null = null;
  terminate = vi.fn();
  constructor() {
    FakeWorker.last = this;
  }
}

type Opts = { errorHandler: (e: unknown) => void; logger: (m: { status: string; progress: number }) => void };

// Mimics tesseract.js: the Web Worker is spawned synchronously inside createWorker().
function spawnThen(behaviour: (opts: Opts) => Promise<unknown>) {
  createWorker.mockImplementation((_langs: string[], _oem: number, opts: Opts) => {
    new Worker("blob:worker");
    return behaviour(opts);
  });
}

const image = new File(["x"], "sms.png", { type: "image/png" });
const never = () => new Promise<never>(() => {});

beforeEach(() => {
  createWorker.mockReset();
  FakeWorker.last = null;
  vi.stubGlobal("Worker", FakeWorker);
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("recognizeImage", () => {
  it("returns trimmed text and rounded confidence, then terminates the worker", async () => {
    const onProgress = vi.fn();
    spawnThen(async (opts) => ({
      recognize: async () => {
        opts.logger({ status: "recognizing text", progress: 0.5 });
        return { data: { text: "  Pay Rs 50 now \n", confidence: 87.6 } };
      },
    }));
    await expect(recognizeImage(image, "eng+tam", { onProgress })).resolves.toEqual({ text: "Pay Rs 50 now", confidence: 88 });
    expect(createWorker.mock.calls[0][0]).toEqual(["eng", "tam"]);
    expect(onProgress).toHaveBeenCalledWith({ stage: "recognizing", progress: 0.5 });
    expect(FakeWorker.last?.terminate).toHaveBeenCalled();
    expect(globalThis.Worker).toBe(FakeWorker);
  });

  it("reports missing language data as an init failure and still terminates the hung worker", async () => {
    // tesseract.js calls errorHandler but never settles createWorker() when traineddata fails to load.
    spawnThen((opts) => {
      setTimeout(() => opts.errorHandler("Network error while fetching tam.traineddata"));
      return never();
    });
    await expect(recognizeImage(image, "tam")).rejects.toMatchObject({ kind: "init" });
    expect(FakeWorker.last?.terminate).toHaveBeenCalled();
  });

  it("stops on cancel and terminates the worker", async () => {
    spawnThen(async () => ({ recognize: never }));
    const ac = new AbortController();
    const pending = recognizeImage(image, "eng", { signal: ac.signal });
    await Promise.resolve();
    ac.abort();
    await expect(pending).rejects.toMatchObject({ kind: "cancelled" });
    expect(FakeWorker.last?.terminate).toHaveBeenCalled();
  });

  it("times out a stuck run", async () => {
    vi.useFakeTimers();
    spawnThen(never);
    const pending = recognizeImage(image, "eng");
    vi.advanceTimersByTime(OCR_TIMEOUT_MS);
    await expect(pending).rejects.toMatchObject({ kind: "timeout" });
    expect(FakeWorker.last?.terminate).toHaveBeenCalled();
  });

  it("classifies memory failures during recognition", async () => {
    spawnThen(async () => ({ recognize: () => Promise.reject(new RangeError("Array buffer allocation failed")) }));
    await expect(recognizeImage(image, "eng")).rejects.toMatchObject({ kind: "memory" });
  });

  it("classifies other recognition errors as failed", async () => {
    spawnThen(async () => ({ recognize: () => Promise.reject(new Error("bad image")) }));
    await expect(recognizeImage(image, "eng")).rejects.toMatchObject({ kind: "failed" });
  });

  it("reports unsupported browsers without starting OCR", async () => {
    vi.stubGlobal("Worker", undefined);
    await expect(recognizeImage(image, "eng")).rejects.toMatchObject({ kind: "unsupported" });
    expect(createWorker).not.toHaveBeenCalled();
  });
});
