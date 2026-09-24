import { ClipboardPaste, Eraser, FileImage, Link2, ShieldCheck, Upload, UserRound, X } from "lucide-react";
import { useId, useRef, type ReactNode } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import type { SenderKind } from "../types/analysis";
import { MAX_BODY_CHARS } from "./ReviewConfirm";

export type InputTab = "text" | "upload" | "url";

export interface FormState {
  tab: InputTab;
  text: string;
  pasted: boolean;
  url: string;
  file: File | null;
  fileUrl: string | null;
  screenshotText: string;
  showSender: boolean;
  senderValue: string;
  senderKind: SenderKind;
}

export const EMPTY_FORM: FormState = {
  tab: "text",
  text: "",
  pasted: false,
  url: "",
  file: null,
  fileUrl: null,
  screenshotText: "",
  showSender: false,
  senderValue: "",
  senderKind: "unknown",
};

export const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp"];
const URL_PATTERN = /^\S+\.\S{2,}$/;

export function isValidUrlInput(value: string): boolean {
  return URL_PATTERN.test(value.trim());
}

export function fileProblem(file: File): "size" | "type" | null {
  if (!ACCEPTED_TYPES.includes(file.type)) return "type";
  if (file.size > MAX_UPLOAD_BYTES) return "size";
  return null;
}

export function isFormReady(form: FormState): boolean {
  if (form.tab === "text") return form.text.trim().length > 0 && form.text.length <= MAX_BODY_CHARS;
  if (form.tab === "url") return isValidUrlInput(form.url);
  return form.file !== null;
}

interface Props {
  form: FormState;
  onChange: (patch: Partial<FormState>) => void;
  onSubmit: () => void;
  fileError: string | null;
  onFileError: (message: string | null) => void;
}

export function InputPanel({ form, onChange, onSubmit, fileError, onFileError }: Props) {
  const { t } = useLanguage();
  const ids = { text: useId(), url: useId(), shot: useId(), sender: useId(), kind: useId() };
  const fileInput = useRef<HTMLInputElement>(null);
  const ready = isFormReady(form);
  const urlTouchedInvalid = form.tab === "url" && form.url.trim() !== "" && !isValidUrlInput(form.url);

  const tabs: { id: InputTab; label: string; icon: ReactNode }[] = [
    { id: "text", label: t.tabPaste, icon: <ClipboardPaste className="size-4" aria-hidden /> },
    { id: "upload", label: t.tabUpload, icon: <Upload className="size-4" aria-hidden /> },
    { id: "url", label: t.tabUrl, icon: <Link2 className="size-4" aria-hidden /> },
  ];

  function pickFile(file: File | undefined) {
    if (!file) return;
    const problem = fileProblem(file);
    if (problem) {
      onFileError(problem === "size" ? t.uploadTooLarge : t.uploadWrongType);
      return;
    }
    onFileError(null);
    if (form.fileUrl) URL.revokeObjectURL(form.fileUrl);
    onChange({ file, fileUrl: URL.createObjectURL(file) });
  }

  function removeFile() {
    if (form.fileUrl) URL.revokeObjectURL(form.fileUrl);
    onChange({ file: null, fileUrl: null });
    if (fileInput.current) fileInput.current.value = "";
  }

  return (
    <section className="rounded-lg border border-line bg-white p-4 shadow-card sm:p-6">
      <div role="tablist" aria-label={t.navCheck} className="grid grid-cols-3 gap-1 rounded-lg bg-surface p-1">
        {tabs.map((tab) => {
          const active = form.tab === tab.id;
          return (
            <button
              key={tab.id}
              role="tab"
              type="button"
              id={`tab-${tab.id}`}
              aria-selected={active}
              aria-controls={`panel-${tab.id}`}
              onClick={() => onChange({ tab: tab.id })}
              className={`flex min-h-11 flex-col items-center justify-center gap-1 rounded-md px-2 py-2 text-xs font-semibold sm:flex-row sm:text-sm ${
                active ? "bg-white text-navy shadow-card" : "text-ink-muted hover:text-navy"
              }`}
            >
              {tab.icon}
              <span className="text-center">{tab.label}</span>
            </button>
          );
        })}
      </div>

      <div id={`panel-${form.tab}`} role="tabpanel" aria-labelledby={`tab-${form.tab}`} className="mt-5">
        {form.tab === "text" && (
          <>
            <div className="flex items-baseline justify-between">
              <label htmlFor={ids.text} className="text-sm font-semibold text-navy">
                {t.messageLabel} <span className="text-red-700">*</span>
              </label>
              <span className={`text-xs ${form.text.length > MAX_BODY_CHARS ? "font-semibold text-red-700" : "text-ink-muted"}`}>
                {form.text.length} / {MAX_BODY_CHARS} {t.characters}
              </span>
            </div>
            <textarea
              id={ids.text}
              value={form.text}
              rows={6}
              placeholder={t.messagePlaceholder}
              onPaste={() => onChange({ pasted: true })}
              onChange={(e) => onChange({ text: e.target.value, ...(e.target.value === "" ? { pasted: false } : {}) })}
              className="mt-2 w-full resize-y rounded-md border-[1.5px] border-line-strong bg-surface-low p-3 text-base focus:border-navy focus:outline-none focus:ring-2 focus:ring-teal/30"
            />
            <button
              type="button"
              onClick={() => onChange({ text: "", pasted: false })}
              className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-ink-muted hover:text-navy"
            >
              <Eraser className="size-3.5" aria-hidden /> {t.clear}
            </button>
          </>
        )}

        {form.tab === "url" && (
          <>
            <label htmlFor={ids.url} className="text-sm font-semibold text-navy">
              {t.urlLabel} <span className="text-red-700">*</span>
            </label>
            <input
              id={ids.url}
              type="text"
              inputMode="url"
              autoComplete="off"
              spellCheck={false}
              value={form.url}
              placeholder={t.urlPlaceholder}
              aria-invalid={urlTouchedInvalid}
              aria-describedby={urlTouchedInvalid ? `${ids.url}-err` : undefined}
              onChange={(e) => onChange({ url: e.target.value })}
              className="mt-2 w-full rounded-md border-[1.5px] border-line-strong bg-surface-low p-3 font-mono text-sm focus:border-navy focus:outline-none focus:ring-2 focus:ring-teal/30"
            />
            {urlTouchedInvalid && (
              <p id={`${ids.url}-err`} role="alert" className="mt-1 text-sm text-red-700">
                {t.urlInvalid}
              </p>
            )}
          </>
        )}

        {form.tab === "upload" && (
          <>
            <p className="text-sm font-semibold text-navy">{t.uploadLabel}</p>
            <p className="text-xs text-ink-muted">{t.uploadHint}</p>
            {form.file && form.fileUrl ? (
              <div className="mt-3 flex items-start gap-3 rounded-md border border-line p-3">
                <img src={form.fileUrl} alt="" className="h-28 w-auto max-w-40 rounded border border-line object-cover" />
                <div className="min-w-0 flex-1 text-sm">
                  <p className="flex items-center gap-1.5 truncate font-semibold text-navy">
                    <FileImage className="size-4 shrink-0" aria-hidden /> {form.file.name}
                  </p>
                  <p className="text-xs text-ink-muted">{Math.ceil(form.file.size / 1024)} KB</p>
                  <button type="button" onClick={removeFile} className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-red-700">
                    <X className="size-3.5" aria-hidden /> {t.uploadRemove}
                  </button>
                </div>
              </div>
            ) : (
              <label
                htmlFor={ids.shot}
                className="mt-3 flex min-h-32 cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed border-slate-400 bg-canvas p-6 text-center hover:border-navy"
              >
                <Upload className="size-6 text-navy-soft" aria-hidden />
                <span className="font-semibold text-navy">{t.uploadChoose}</span>
              </label>
            )}
            <input
              ref={fileInput}
              id={ids.shot}
              type="file"
              accept={ACCEPTED_TYPES.join(",")}
              className="sr-only"
              onChange={(e) => pickFile(e.target.files?.[0])}
            />
            {fileError && (
              <p role="alert" className="mt-2 text-sm text-red-700">
                {fileError}
              </p>
            )}
            {form.file && (
              <div className="mt-4">
                <p className="rounded-md border-l-4 border-amber bg-amber-50 p-3 text-sm text-amber-900">{t.ocrUnavailable}</p>
                <label htmlFor={`${ids.shot}-text`} className="mt-3 block text-sm font-semibold text-navy">
                  {t.screenshotTextLabel}
                </label>
                <textarea
                  id={`${ids.shot}-text`}
                  rows={4}
                  value={form.screenshotText}
                  onChange={(e) => onChange({ screenshotText: e.target.value })}
                  className="mt-2 w-full resize-y rounded-md border-[1.5px] border-line-strong bg-surface-low p-3 text-base focus:border-navy focus:outline-none focus:ring-2 focus:ring-teal/30"
                />
              </div>
            )}
          </>
        )}
      </div>

      <div className="mt-4 rounded-md border border-line">
        <button
          type="button"
          aria-expanded={form.showSender}
          onClick={() => onChange({ showSender: !form.showSender })}
          className="flex min-h-11 w-full items-center gap-2 px-3 text-left text-sm font-semibold text-navy"
        >
          <UserRound className="size-4" aria-hidden /> {t.senderToggle}
        </button>
        {form.showSender && (
          <div className="grid gap-3 border-t border-line p-3 sm:grid-cols-2">
            <p className="text-xs text-ink-muted sm:col-span-2">{t.senderHelp}</p>
            <label className="text-sm font-semibold text-navy" htmlFor={ids.sender}>
              {t.senderValue}
              <input
                id={ids.sender}
                maxLength={64}
                value={form.senderValue}
                onChange={(e) => onChange({ senderValue: e.target.value })}
                className="mt-1 w-full rounded-md border-[1.5px] border-line-strong p-2 font-normal"
              />
            </label>
            <label className="text-sm font-semibold text-navy" htmlFor={ids.kind}>
              {t.senderKind}
              <select
                id={ids.kind}
                value={form.senderKind}
                onChange={(e) => onChange({ senderKind: e.target.value as SenderKind })}
                className="mt-1 w-full rounded-md border-[1.5px] border-line-strong p-2 font-normal"
              >
                {(Object.keys(t.senderKinds) as SenderKind[]).map((k) => (
                  <option key={k} value={k}>
                    {t.senderKinds[k]}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
      </div>

      <div className="mt-4 flex gap-3 rounded-md bg-surface-low p-4">
        <ShieldCheck className="mt-0.5 size-5 shrink-0 text-teal-deep" aria-hidden />
        <div className="text-sm">
          <p className="font-semibold text-navy">{t.protectionTitle}</p>
          <p className="text-ink-muted">{t.protectionBody}</p>
        </div>
      </div>

      <button
        type="button"
        disabled={!ready}
        onClick={onSubmit}
        className="mt-5 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-md bg-navy-deep px-6 font-semibold text-white hover:bg-navy disabled:cursor-not-allowed disabled:opacity-40"
      >
        {t.reviewAndCheck} →
      </button>
    </section>
  );
}
