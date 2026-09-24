import { AlertOctagon, Check, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { EMPTY_FORM, InputPanel, type FormState } from "../components/InputPanel";
import { ReviewConfirm, type Draft } from "../components/ReviewConfirm";
import { RiskCard } from "../components/RiskCard";
import { SAMPLES } from "../data/samples";
import { useLanguage } from "../i18n/LanguageContext";
import type { Strings } from "../i18n/strings";
import { ApiError, submitAnalysis } from "../services/api";
import type { AnalyzeRequest, AnalyzeResponse, ContentSource } from "../types/analysis";

type Phase = "input" | "review" | "analyzing" | "result" | "error";

export function maskSender(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length >= 7 && /^[+\d\s-]+$/.test(value.trim())) return `${"*".repeat(digits.length - 4)}${digits.slice(-4)}`;
  return value;
}

export function draftFromForm(form: FormState): Draft {
  const sender = form.showSender && form.senderValue.trim() ? maskSender(form.senderValue.trim()) : null;
  const base = { screenshot: null, screenshotUrl: null, senderMasked: sender };
  if (form.tab === "url") return { ...base, body: form.url.trim(), source: "url_input" };
  if (form.tab === "upload") {
    return {
      ...base,
      body: form.screenshotText,
      source: form.screenshotText.trim() ? "manual_entry" : "ocr",
      screenshot: form.file,
      screenshotUrl: form.fileUrl,
    };
  }
  return { ...base, body: form.text, source: form.pasted ? "pasted_text" : "manual_entry" };
}

export function buildRequest(form: FormState, body: string, source: ContentSource, hasScreenshot: boolean): AnalyzeRequest {
  const request: AnalyzeRequest = {
    schema_version: "1.0",
    content: { body, source, user_confirmed: true },
    language_preference: "both",
    privacy: { upload_confirmed: true, retention_preference: "delete_after_analysis" },
  };
  if (form.showSender && form.senderValue.trim()) {
    request.sender = {
      value: form.senderValue.trim(),
      kind: form.senderKind,
      provenance: "user_entered",
      verification_status: "unverified",
    };
  }
  if (hasScreenshot && form.file) {
    request.attachment = {
      type: "screenshot",
      provenance: "user_upload",
      original_filename: form.file.name.slice(0, 255),
      declared_mime_type: form.file.type,
    };
  }
  return request;
}

function errorMessage(err: unknown, t: Strings): string {
  if (err instanceof ApiError) {
    if (err.kind === "network") return t.errorNetwork;
    if (err.kind === "timeout") return t.errorTimeout;
    if (err.kind === "server") return t.errorGeneric;
    return err.message;
  }
  return t.errorGeneric;
}

function Stepper({ phase }: { phase: Phase }) {
  const { t } = useLanguage();
  const current = phase === "input" ? 0 : phase === "review" ? 1 : 2;
  const steps = [t.stepInput, t.stepReview, t.stepResult];
  return (
    <ol className="flex flex-wrap items-center gap-2 text-sm" aria-label="Progress">
      {steps.map((label, i) => (
        <li key={label} className="flex items-center gap-2" aria-current={i === current ? "step" : undefined}>
          <span
            className={`grid size-7 place-items-center rounded-full text-xs font-bold ${
              i < current ? "bg-teal/20 text-teal-deep" : i === current ? "bg-navy text-white" : "bg-surface text-ink-muted"
            }`}
          >
            {i < current ? <Check className="size-4" aria-hidden /> : i + 1}
          </span>
          <span className={i === current ? "font-semibold text-navy" : "text-ink-muted"}>{label}</span>
          {i < steps.length - 1 && <span className="text-line-strong" aria-hidden>›</span>}
        </li>
      ))}
    </ol>
  );
}

export function Analyze() {
  const { t } = useLanguage();
  const location = useLocation();
  const [phase, setPhase] = useState<Phase>("input");
  const [form, setForm] = useState<FormState>(() => {
    const sample = SAMPLES.find((s) => s.id === (location.state as { sampleId?: string } | null)?.sampleId);
    return sample ? { ...EMPTY_FORM, text: sample.body, pasted: true } : EMPTY_FORM;
  });
  const [draft, setDraft] = useState<Draft | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const lastSubmission = useRef<{ body: string; source: ContentSource } | null>(null);
  const fileUrlRef = useRef<string | null>(null);
  fileUrlRef.current = form.fileUrl;

  useEffect(() => () => {
    if (fileUrlRef.current) URL.revokeObjectURL(fileUrlRef.current);
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [phase]);

  function reset() {
    if (form.fileUrl) URL.revokeObjectURL(form.fileUrl);
    setForm(EMPTY_FORM);
    setDraft(null);
    setResult(null);
    setError(null);
    setFileError(null);
    lastSubmission.current = null;
    setPhase("input");
  }

  async function run(body: string, source: ContentSource) {
    lastSubmission.current = { body, source };
    setPhase("analyzing");
    setError(null);
    try {
      const hasScreenshot = form.tab === "upload" && form.file !== null;
      const response = await submitAnalysis(buildRequest(form, body, source, hasScreenshot), hasScreenshot ? form.file : null);
      setResult(response);
      setPhase("result");
    } catch (err) {
      setError(errorMessage(err, t));
      setPhase("error");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 rounded-lg border border-line bg-white px-4 py-4 shadow-card sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <h1 className="text-xl font-bold text-navy">{t.navCheck}</h1>
        <Stepper phase={phase} />
      </div>

      {phase === "input" && (
        <InputPanel
          form={form}
          onChange={(patch) => setForm((f) => ({ ...f, ...patch }))}
          onSubmit={() => {
            setDraft(draftFromForm(form));
            setPhase("review");
          }}
          fileError={fileError}
          onFileError={setFileError}
        />
      )}

      {phase === "review" && draft && (
        <ReviewConfirm
          draft={draft}
          onBack={(body) => {
            setForm((f) => (f.tab === "text" ? { ...f, text: body } : f.tab === "url" ? { ...f, url: body } : { ...f, screenshotText: body }));
            setPhase("input");
          }}
          onCancel={reset}
          onConfirm={run}
        />
      )}

      {phase === "analyzing" && (
        <section aria-busy="true" aria-live="polite" className="rounded-lg border border-line bg-white p-6 shadow-card">
          <p className="flex items-center gap-3 text-lg font-semibold text-navy">
            <Loader2 className="size-6 animate-spin" aria-hidden /> {t.analyzingTitle}
          </p>
          <ul className="mt-4 flex flex-col gap-2 text-sm text-ink-muted">
            {t.analyzingStages.map((stage) => (
              <li key={stage} className="flex items-center gap-2">
                <span className="size-1.5 animate-pulse rounded-full bg-teal" aria-hidden /> {stage}
              </li>
            ))}
          </ul>
        </section>
      )}

      {phase === "error" && (
        <section role="alert" className="rounded-lg border border-red-200 bg-red-50 p-6">
          <p className="flex items-center gap-2 text-lg font-semibold text-red-900">
            <AlertOctagon className="size-6" aria-hidden /> {t.errorTitle}
          </p>
          <p className="mt-2 text-red-900">{error}</p>
          <p className="mt-2 text-sm font-semibold text-red-900">{t.errorNote}</p>
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={() => lastSubmission.current && run(lastSubmission.current.body, lastSubmission.current.source)}
              className="min-h-11 rounded-md bg-navy px-5 font-semibold text-white"
            >
              {t.retry}
            </button>
            <button type="button" onClick={reset} className="min-h-11 rounded-md px-5 font-semibold text-navy">
              {t.startOver}
            </button>
          </div>
        </section>
      )}

      {phase === "result" && result && <RiskCard result={result} onReset={reset} />}
    </div>
  );
}
