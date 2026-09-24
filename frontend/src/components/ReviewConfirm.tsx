import { ArrowLeft, ArrowRight, FileImage, Lock, PencilLine, ShieldAlert } from "lucide-react";
import { useId, useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import type { ContentSource } from "../types/analysis";

export const MAX_BODY_CHARS = 8000;

export interface Draft {
  body: string;
  source: ContentSource;
  screenshot: File | null;
  screenshotUrl: string | null;
  senderMasked: string | null;
}

interface Props {
  draft: Draft;
  onBack: (body: string) => void;
  onCancel: () => void;
  onConfirm: (body: string, source: ContentSource) => void;
}

export function editedSource(original: ContentSource, edited: boolean): ContentSource {
  if (!edited) return original;
  return original === "ocr" ? "user_corrected_ocr" : original;
}

export function ReviewConfirm({ draft, onBack, onCancel, onConfirm }: Props) {
  const { t } = useLanguage();
  const [body, setBody] = useState(draft.body);
  const [consent, setConsent] = useState(false);
  const textId = useId();
  const consentId = useId();

  const edited = body !== draft.body;
  const source = editedSource(draft.source, edited);
  const hasContent = body.trim().length > 0 || draft.screenshot !== null;
  const overLimit = body.length > MAX_BODY_CHARS;
  const canSubmit = consent && hasContent && !overLimit;

  return (
    <section aria-labelledby="review-title" className="rounded-lg border border-line bg-white p-4 shadow-card sm:p-6">
      <div className="flex flex-wrap gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-teal/15 px-3 py-1 text-xs font-semibold text-teal-deep">
          {t.provenance}: {t.provenanceLabels[source]}
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800 ring-1 ring-amber-200">
          {t.unverifiedBadge}
        </span>
        {edited && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-surface px-3 py-1 text-xs font-semibold text-navy-soft">
            <PencilLine className="size-3.5" aria-hidden /> {t.editedBadge}
          </span>
        )}
      </div>

      <h2 id="review-title" className="mt-5 text-2xl font-bold text-navy sm:text-3xl">
        {t.reviewTitle}
      </h2>
      <p className="mt-2 text-ink-muted">{t.reviewBody}</p>

      {draft.screenshotUrl && (
        <div className="mt-5 flex items-start gap-4 rounded-md border-l-4 border-teal bg-surface-low p-3">
          <img src={draft.screenshotUrl} alt="" className="h-24 w-auto max-w-32 rounded border border-line object-cover" />
          <div className="text-sm">
            <p className="flex items-center gap-1.5 font-semibold text-navy">
              <FileImage className="size-4" aria-hidden /> {t.screenshotAttached}
            </p>
            <p className="mt-1 text-ink-muted">{t.ocrUnavailable}</p>
          </div>
        </div>
      )}

      {draft.senderMasked && (
        <p className="mt-4 text-sm text-ink-muted">
          <span className="font-semibold text-navy">{t.senderTitle}:</span> {draft.senderMasked} · {t.unverifiedBadge}
        </p>
      )}

      <div className="mt-5">
        <label htmlFor={textId} className="text-sm font-semibold text-navy">
          {t.payloadLabel}
        </label>
        <textarea
          id={textId}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={6}
          aria-describedby={`${textId}-count`}
          className="mt-2 w-full resize-y rounded-md border-[1.5px] border-line-strong bg-surface-low p-3 text-base focus:border-navy focus:outline-none focus:ring-2 focus:ring-teal/30"
        />
        <p id={`${textId}-count`} className={`mt-1 text-right text-xs ${overLimit ? "font-semibold text-red-700" : "text-ink-muted"}`}>
          {body.length} / {MAX_BODY_CHARS} {t.characters}
        </p>
      </div>

      <div className="mt-4 flex gap-3 rounded-md bg-surface-low p-4">
        <Lock className="mt-0.5 size-5 shrink-0 text-teal-deep" aria-hidden />
        <div className="text-sm">
          <p className="font-semibold text-navy">{t.privacyTitle}</p>
          <p className="mt-1 text-ink-muted">{t.privacyBody}</p>
        </div>
      </div>

      <label htmlFor={consentId} className="mt-4 flex min-h-11 cursor-pointer items-start gap-3 rounded-md border border-line p-3">
        <input
          id={consentId}
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          className="mt-0.5 size-5 shrink-0 accent-navy"
        />
        <span className="text-sm font-medium text-navy">{t.consent}</span>
      </label>

      {!hasContent && (
        <p role="alert" className="mt-3 flex items-center gap-2 text-sm text-red-700">
          <ShieldAlert className="size-4" aria-hidden /> {t.emptyInput}
        </p>
      )}

      <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:items-center">
        <button
          type="button"
          onClick={() => onBack(body)}
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-surface-high px-5 font-semibold text-navy hover:bg-surface"
        >
          <ArrowLeft className="size-4" aria-hidden /> {t.back}
        </button>
        <button type="button" onClick={onCancel} className="min-h-11 rounded-md px-5 font-semibold text-ink-muted hover:text-navy">
          {t.cancel}
        </button>
        <button
          type="button"
          disabled={!canSubmit}
          onClick={() => onConfirm(body, source)}
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-navy px-6 font-semibold text-white hover:bg-navy-deep disabled:cursor-not-allowed disabled:opacity-40 sm:ml-auto"
        >
          {t.confirmAnalyze} <ArrowRight className="size-4" aria-hidden />
        </button>
      </div>
    </section>
  );
}
