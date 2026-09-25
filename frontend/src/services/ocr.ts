import { createWorker } from "tesseract.js";

// Runs entirely in the browser: the image never leaves the device. The OCR engine and language
// models are static public files fetched from the jsDelivr CDN on first use (then browser-cached).
export type OcrLanguage = "eng" | "tam" | "eng+tam";
export type OcrErrorKind = "unsupported" | "init" | "timeout" | "memory" | "failed" | "cancelled";

export interface OcrResult {
  text: string;
  confidence: number; // 0–100, Tesseract's mean word confidence
}

export interface OcrProgress {
  stage: "loading" | "recognizing";
  progress: number; // 0–1 within the stage
}

export class OcrError extends Error {
  constructor(public readonly kind: OcrErrorKind) {
    super(`OCR ${kind}`);
    this.name = "OcrError";
  }
}

export const OCR_TIMEOUT_MS = 120_000; // first run includes downloading language data on slow mobile links

function classify(err: unknown, stage: "loading" | "recognizing"): OcrErrorKind {
  const text = String((err as Error)?.message ?? err);
  if (err instanceof RangeError || /memory|allocat/i.test(text)) return "memory";
  return stage === "loading" ? "init" : "failed";
}

export async function recognizeImage(
  image: File,
  langs: OcrLanguage,
  { onProgress, signal }: { onProgress?: (p: OcrProgress) => void; signal?: AbortSignal } = {},
): Promise<OcrResult> {
  if (typeof Worker === "undefined" || typeof WebAssembly === "undefined") throw new OcrError("unsupported");
  if (signal?.aborted) throw new OcrError("cancelled");

  let stage: "loading" | "recognizing" = "loading";
  let fail!: (e: OcrError) => void;
  const failed = new Promise<never>((_, reject) => (fail = reject));
  failed.catch(() => {}); // a late error after success must not surface as an unhandled rejection
  const timer = window.setTimeout(() => fail(new OcrError("timeout")), OCR_TIMEOUT_MS);
  const onAbort = () => fail(new OcrError("cancelled"));
  signal?.addEventListener("abort", onAbort);

  // tesseract.js never settles createWorker() when language data fails to load, leaving its Web Worker
  // unreachable. It spawns that Worker synchronously, so capture it here to always terminate it.
  // ponytail: relies on tesseract.js spawning synchronously; re-check on major upgrades.
  const RealWorker = globalThis.Worker;
  let spawned: Worker | null = null;
  globalThis.Worker = class extends RealWorker {
    constructor(...args: ConstructorParameters<typeof Worker>) {
      super(...args);
      spawned = this;
    }
  };
  let pending: ReturnType<typeof createWorker>;
  try {
    pending = createWorker(langs.split("+"), 1, {
      logger: (m) => onProgress?.({ stage: m.status === "recognizing text" ? "recognizing" : "loading", progress: m.progress }),
      errorHandler: (e) => fail(new OcrError(classify(e, stage))),
    });
  } finally {
    globalThis.Worker = RealWorker;
  }

  try {
    const worker = await Promise.race([pending, failed]);
    stage = "recognizing";
    const { data } = await Promise.race([worker.recognize(image), failed]);
    return { text: data.text.trim(), confidence: Math.round(data.confidence) };
  } catch (err) {
    throw err instanceof OcrError ? err : new OcrError(classify(err, stage));
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
    (spawned as Worker | null)?.terminate();
  }
}
