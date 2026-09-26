import { Quote } from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ErrorBox, ExplanationBlock, Loading, Loc, OfficialLink, PageTitle, VerificationBadge, btnPrimary, card, formatDate, input, label } from "../components/civic/ui";
import { useCivic } from "../i18n/civic";
import { useLanguage } from "../i18n/LanguageContext";
import { ApiError } from "../services/api";
import { postJson } from "../services/civicApi";
import { useAiStatus } from "../services/useAi";
import type { AskResult, Finding } from "../types/civic";

const EXAMPLES = [
  "Is PM-KISAN giving ₹10,000 every year?",
  "Register for PM Kisan at pmkisan-kyc.online to get your instalment",
  "Is the Stand-Up India scheme giving loans of Rs.10 lakh to women?",
  "क्या उज्ज्वला योजना में मुफ्त गैस कनेक्शन मिलता है?",
];

function FindingRow({ f }: { f: Finding }) {
  const { c } = useCivic();
  const tone = f.outcome === "supported" ? "text-teal-deep" : f.outcome === "contradicted" ? "text-red-700" : "text-amber-800";
  return (
    <li className="flex flex-col gap-1 border-b border-line py-2 last:border-0 sm:flex-row sm:gap-3">
      <span className={`shrink-0 text-sm font-bold sm:w-40 ${tone}`}>{c[`outcome_${f.outcome}`]}</span>
      <span>
        <Loc t={f.detail} />
        {f.evidence_url && (
          <span className="ml-2 text-sm">
            <OfficialLink href={f.evidence_url}>{new URL(f.evidence_url).hostname}</OfficialLink>
          </span>
        )}
      </span>
    </li>
  );
}

export function SchemesAsk() {
  const { c } = useCivic();
  const { code } = useLanguage();
  const ai = useAiStatus();
  const textId = useId();
  const urlId = useId();
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskResult | null>(null);

  async function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await postJson<AskResult>("/v1/schemes/ask", { text, url: url || null, lang: code, ai_consent: consent }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : c.errorGeneric);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageTitle title={c.askTitle} subtitle={c.askSubtitle} />
      <form onSubmit={submit} className={`${card} space-y-4`}>
        <div>
          <label htmlFor={textId} className={label}>
            {c.askLabel}
          </label>
          <textarea id={textId} value={text} onChange={(e) => setText(e.target.value)} maxLength={2000} rows={3}
            placeholder={c.askPlaceholder} className={`${input} mt-2`} />
        </div>
        <div>
          <label htmlFor={urlId} className={label}>
            {c.urlLabel}
          </label>
          <input id={urlId} value={url} onChange={(e) => setUrl(e.target.value)} maxLength={500} className={`${input} mt-2`} inputMode="url" />
        </div>
        {ai?.ai_enabled ? (
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-1 size-5" />
            {c.aiConsent}
          </label>
        ) : (
          <p className="text-sm text-ink-muted">{c.aiOff}</p>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <button type="submit" disabled={busy || !text.trim()} className={btnPrimary}>
            {c.submitAsk}
          </button>
          <span className="text-sm text-ink-muted">{c.examplesTitle}:</span>
          {EXAMPLES.map((ex) => (
            <button key={ex} type="button" onClick={() => setText(ex)} className="rounded-full bg-surface px-3 py-1 text-left text-xs font-semibold text-navy hover:bg-surface-high">
              {ex}
            </button>
          ))}
        </div>
      </form>

      {busy && <Loading text={c.checking} />}
      {error && <ErrorBox message={error} onRetry={() => submit()} />}

      {result && (
        <section aria-live="polite" className="space-y-4">
          <div className={`${card} space-y-3`}>
            <VerificationBadge status={result.status} />
            <p className="text-sm font-semibold text-navy-soft">{c[`basis_${result.basis}`]}</p>
            {(result.status === "not_found" || result.status === "unable_to_verify") && <p className="text-sm">{c.notFake}</p>}
            <ExplanationBlock e={result.explanation} />
            {result.search_portal && (
              <p>
                <OfficialLink href={result.search_portal}>{c.searchPortal}</OfficialLink>
              </p>
            )}
          </div>

          {result.schemes.map((s) => (
            <div key={s.scheme.id} className={`${card} space-y-3`}>
              <h2 className="text-lg font-bold text-navy">
                <Link to={`/schemes/${s.scheme.id}`} className="underline">
                  <Loc t={s.scheme.name} />
                </Link>
              </h2>
              <h3 className="font-semibold">{c.findingsTitle}</h3>
              <ul>{s.findings.map((f, i) => <FindingRow key={i} f={f} />)}</ul>
              <h3 className="font-semibold">{c.sourcesTitle}</h3>
              <ul className="space-y-1 text-sm">
                {s.sources.map((src) => (
                  <li key={src.id}>
                    <OfficialLink href={src.url}>{src.title}</OfficialLink>{" "}
                    <span className="text-ink-muted">· {src.publisher} · {c.retrieved} {src.retrieved}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          {result.evidence_findings.length > 0 && (
            <div className={card}>
              <h3 className="font-semibold">{c.findingsTitle}</h3>
              <ul>{result.evidence_findings.map((f, i) => <FindingRow key={i} f={f} />)}</ul>
            </div>
          )}

          {result.evidence.length > 0 && (
            <div className={`${card} space-y-3`}>
              <h3 className="font-semibold">{c.evidenceTitle}</h3>
              {result.evidence.map((ev) => (
                <blockquote key={ev.url + ev.quote} className="border-l-4 border-teal pl-3">
                  <p className="flex gap-2">
                    <Quote className="size-4 shrink-0 text-teal-deep" aria-hidden />“{ev.quote}”
                  </p>
                  <footer className="mt-1 text-sm">
                    <OfficialLink href={ev.url}>{ev.title || ev.domain}</OfficialLink>{" "}
                    <span className="text-ink-muted">· {c.retrieved} {formatDate(ev.retrieved_at)}</span>
                  </footer>
                </blockquote>
              ))}
            </div>
          )}

          {result.suggestions.length > 0 && (
            <div className={card}>
              <h3 className="font-semibold">{c.suggestionsTitle}</h3>
              <ul className="mt-2 space-y-2">
                {result.suggestions.map((s) => (
                  <li key={s.scheme.id}>
                    <Link to={`/schemes/${s.scheme.id}`} className="font-semibold text-teal-deep underline">
                      <Loc t={s.scheme.name} />
                    </Link>{" "}
                    <span className="text-sm text-ink-muted">· {c[`elig_${s.eligibility}`]}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-xs text-ink-muted">
            <Loc t={result.disclosure} />
          </p>
        </section>
      )}
    </div>
  );
}
