import { AlertTriangle, ScanText, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { OcrError, recognizeImage, type OcrErrorKind, type OcrLanguage, type OcrProgress, type OcrResult } from "../services/ocr";
import type { FormState } from "./InputPanel";

export const LOW_OCR_CONFIDENCE = 60;

interface Props {
  file: File;
  lang: OcrLanguage;
  result: OcrResult | null;
  text: string;
  onChange: (patch: Partial<FormState>) => void;
}

export function OcrPanel({ file, lang, result, text, onChange }: Props) {
  const { t } = useLanguage();
  const ids = { lang: useId(), text: useId() };
  const [progress, setProgress] = useState<OcrProgress | null>(null);
  const [error, setError] = useState<OcrErrorKind | null>(null);
  const controller = useRef<AbortController | null>(null);
  const running = progress !== null;

  // Leaving the tab, removing the image, or unmounting stops OCR and frees its worker.
  useEffect(() => () => controller.current?.abort(), []);

  async function run() {
    const ac = new AbortController();
    controller.current = ac;
    setError(null);
    setProgress({ stage: "loading", progress: 0 });
    onChange({ ocrBusy: true });
    try {
      const r = await recognizeImage(file, lang, { signal: ac.signal, onProgress: setProgress });
      // An empty result keeps whatever the user already typed.
      onChange(r.text ? { ocr: r, screenshotText: r.text } : { ocr: r });
    } catch (err) {
      setError(err instanceof OcrError ? err.kind : "failed");
    } finally {
      controller.current = null;
      setProgress(null);
      onChange({ ocrBusy: false });
    }
  }

  const lowQuality = result !== null && result.text !== "" && result.confidence < LOW_OCR_CONFIDENCE;

  return (
    <div className="mt-4 flex flex-col gap-3">
      <div className="flex flex-wrap items-end gap-3">
        <label htmlFor={ids.lang} className="text-sm font-semibold text-navy">
          {t.ocrLanguage}
          <select
            id={ids.lang}
            value={lang}
            disabled={running}
            onChange={(e) => onChange({ ocrLang: e.target.value as OcrLanguage })}
            className="mt-1 block rounded-md border-[1.5px] border-line-strong p-2 font-normal"
          >
            {(Object.keys(t.ocrLanguages) as OcrLanguage[]).map((k) => (
              <option key={k} value={k}>
                {t.ocrLanguages[k]}
              </option>
            ))}
          </select>
        </label>
        {running ? (
          <button
            type="button"
            onClick={() => controller.current?.abort()}
            className="inline-flex min-h-11 items-center gap-2 rounded-md bg-surface-high px-4 font-semibold text-navy hover:bg-surface"
          >
            <X className="size-4" aria-hidden /> {t.ocrCancel}
          </button>
        ) : (
          <button
            type="button"
            onClick={run}
            className="inline-flex min-h-11 items-center gap-2 rounded-md bg-navy px-4 font-semibold text-white hover:bg-navy-deep"
          >
            <ScanText className="size-4" aria-hidden /> {result || error ? t.ocrRerun : t.ocrRun}
          </button>
        )}
      </div>

      <div aria-live="polite">
        {progress && (
          <div className="text-sm text-ink-muted">
            <p>
              {progress.stage === "loading" ? t.ocrLoading : `${t.ocrReading} ${Math.round(progress.progress * 100)}%`}
            </p>
            {/* No value while loading: that stage reports several sub-steps, so show it as indeterminate. */}
            <progress
              aria-label={t.ocrReading}
              max={1}
              {...(progress.stage === "recognizing" ? { value: progress.progress } : {})}
              className="mt-1 w-full accent-teal"
            />
          </div>
        )}
        {!running && !error && result && result.text !== "" && (
          <div
            className={`rounded-md border-l-4 p-3 text-sm ${lowQuality ? "border-amber bg-amber-50 text-amber-900" : "border-teal bg-surface-low text-navy"}`}
          >
            <p>{t.ocrDone}</p>
            <p className="mt-1 font-semibold">
              {t.ocrConfidence}: {result.confidence}%
            </p>
            {lowQuality && (
              <p className="mt-1 flex items-center gap-1.5 font-semibold">
                <AlertTriangle className="size-4 shrink-0" aria-hidden /> {t.ocrLowQuality}
              </p>
            )}
          </div>
        )}
        {!running && !error && result && result.text === "" && (
          <p className="rounded-md border-l-4 border-amber bg-amber-50 p-3 text-sm text-amber-900">{t.ocrEmpty}</p>
        )}
      </div>
      {error && (
        <p role="alert" className="rounded-md border-l-4 border-red-300 bg-red-50 p-3 text-sm text-red-900">
          {t.ocrErrors[error]} {t.ocrManualFallback}
        </p>
      )}

      <div>
        <label htmlFor={ids.text} className="block text-sm font-semibold text-navy">
          {t.screenshotTextLabel}
        </label>
        <textarea
          id={ids.text}
          rows={6}
          value={text}
          disabled={running}
          // Emptying the box after OCR means whatever is typed next is the user's own text, not OCR output.
          onChange={(e) => onChange(e.target.value === "" && result ? { screenshotText: "", ocr: null } : { screenshotText: e.target.value })}
          className="mt-2 w-full resize-y rounded-md border-[1.5px] border-line-strong bg-surface-low p-3 text-base focus:border-navy focus:outline-none focus:ring-2 focus:ring-teal/30 disabled:opacity-60"
        />
      </div>
    </div>
  );
}
