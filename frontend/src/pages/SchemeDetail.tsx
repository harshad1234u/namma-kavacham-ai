import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorBox, Loading, Loc, OfficialLink, PageTitle, btnPrimary, btnSecondary, card, input, label } from "../components/civic/ui";
import { useCivic } from "../i18n/civic";
import { useLanguage } from "../i18n/LanguageContext";
import { ApiError } from "../services/api";
import { getJson, postJson, query } from "../services/civicApi";
import { useAiStatus } from "../services/useAi";
import type { EligibilityResult, Question, SchemeDetail as Detail, Statement } from "../types/civic";

function List({ title, items, render }: { title: string; items: unknown[]; render: () => React.ReactNode }) {
  const { c } = useCivic();
  return (
    <section className={card}>
      <h2 className="text-lg font-bold text-navy">{title}</h2>
      {items.length ? render() : <p className="mt-2 text-ink-muted">{c.notListed}</p>}
    </section>
  );
}

function Statements({ items }: { items: Statement[] }) {
  return (
    <ul className="mt-3 list-disc space-y-2 pl-5">
      {items.map((s, i) => <li key={i}><Loc t={s.text} /></li>)}
    </ul>
  );
}

function EligibilityWizard({ schemeId }: { schemeId: string }) {
  const { c } = useCivic();
  const { code } = useLanguage();
  const [questions, setQuestions] = useState<Question[] | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<EligibilityResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setResult(null);
    getJson<Question[]>(`/v1/schemes/${schemeId}/eligibility/questions${query({ lang: code })}`)
      .then(setQuestions)
      .catch(() => setError(c.errorGeneric));
  }, [schemeId, code, c.errorGeneric]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const typed: Record<string, string | number | boolean | null> = {};
    for (const q of questions ?? []) {
      const v = answers[q.attribute];
      if (!v || v === "unknown") continue;
      typed[q.attribute] = q.type === "int" ? Number(v) : q.type === "bool" ? v === "true" : v;
    }
    try {
      setResult(await postJson<EligibilityResult>(`/v1/schemes/${schemeId}/eligibility`, { answers: typed, lang: code }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : c.errorGeneric);
    }
  }

  if (error) return <ErrorBox message={error} />;
  if (!questions) return <Loading />;
  if (questions.length === 0) return <p className="text-ink-muted">{c.noQuestions}</p>;
  return (
    <form onSubmit={submit} className="space-y-4">
      {questions.map((q) => (
        <fieldset key={q.attribute}>
          <legend className={label}><Loc t={q.question} /></legend>
          {q.type === "int" ? (
            <input type="number" min={0} aria-label={q.question.text} value={answers[q.attribute] ?? ""} onChange={(e) => setAnswers({ ...answers, [q.attribute]: e.target.value })} className={`${input} mt-2 max-w-xs`} />
          ) : (
            <div className="mt-2 flex flex-wrap gap-2">
              {[...(q.type === "bool" ? ["true", "false"] : q.options), "unknown"].map((o) => (
                <label key={o} className={`inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-md px-3 ring-1 ${answers[q.attribute] === o ? "bg-navy text-white ring-navy" : "bg-white ring-line-strong"}`}>
                  <input type="radio" className="sr-only" name={q.attribute} value={o} checked={answers[q.attribute] === o} onChange={() => setAnswers({ ...answers, [q.attribute]: o })} />
                  {o === "true" ? c.yes : o === "false" ? c.no : o === "unknown" ? c.dontKnow : c.options[o] ?? o.replace(/_/g, " ")}
                </label>
              ))}
            </div>
          )}
        </fieldset>
      ))}
      <button type="submit" className={btnPrimary}>{c.seeResult}</button>
      {result && (
        <div aria-live="polite" className="rounded-md bg-surface-low p-4">
          <p data-testid="eligibility-overall" className="text-lg font-bold text-navy">{c[`elig_${result.overall}`]}</p>
          <ul className="mt-2 space-y-1 text-sm">
            {result.criteria.map(({ criterion, outcome }) => (
              <li key={criterion.id} className="flex gap-2">
                <span className="w-40 shrink-0 font-semibold">{c[`outcomeCrit_${outcome}`]}</span>
                <Loc t={criterion.statement.text} />
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-ink-muted"><Loc t={result.note} /></p>
        </div>
      )}
    </form>
  );
}

export function SchemeDetail() {
  const { id = "" } = useParams();
  const { c } = useCivic();
  const { code } = useLanguage();
  const ai = useAiStatus();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [translate, setTranslate] = useState(false);

  const load = useCallback(() => {
    setError(null);
    getJson<Detail>(`/v1/schemes/${id}${query({ lang: code, translate: translate || null })}`)
      .then(setDetail)
      .catch((err) => setError(err instanceof ApiError ? err.message : c.errorGeneric));
  }, [id, code, translate, c.errorGeneric]);
  useEffect(load, [load]);

  if (error) return <ErrorBox message={error} onRetry={load} />;
  if (!detail) return <Loading />;
  const inclusion = detail.eligibility.filter((e) => e.kind === "inclusion");
  const exclusion = detail.eligibility.filter((e) => e.kind === "exclusion");
  return (
    <div className="space-y-4">
      <Link to="/schemes/discover" className="text-sm font-semibold text-teal-deep underline">← {c.back}</Link>
      <PageTitle title={detail.name.text} subtitle={detail.description.text.text} />
      <p className="-mt-4 text-sm text-ink-muted">
        {c.ministry}: {detail.ministry} · {c.lastVerified}: {detail.last_verified}
      </p>
      {ai?.ai_enabled && code !== "en" && !translate && (
        <button type="button" onClick={() => setTranslate(true)} className={btnSecondary}>{c.translateAi}</button>
      )}
      <List title={c.benefits} items={detail.benefits} render={() => <Statements items={detail.benefits} />} />
      <List title={c.eligibilityRules} items={detail.eligibility} render={() => (
        <>
          <Statements items={inclusion.map((e) => e.statement)} />
          {exclusion.length > 0 && (<><h3 className="mt-4 font-semibold">{c.exclusion}</h3><Statements items={exclusion.map((e) => e.statement)} /></>)}
        </>
      )} />
      <section className={card}>
        <h2 className="text-lg font-bold text-navy">{c.checkEligibility}</h2>
        <div className="mt-3"><EligibilityWizard schemeId={detail.id} /></div>
      </section>
      <List title={c.documents} items={detail.documents} render={() => <Statements items={detail.documents} />} />
      <List title={c.howToApply} items={detail.application_steps} render={() => <Statements items={detail.application_steps} />} />
      <section className={card}>
        <h2 className="text-lg font-bold text-navy">{c.officialChannels}</h2>
        <ul className="mt-3 space-y-2">
          {detail.channels.map((ch, i) => (
            <li key={i}>{ch.official_url ? <OfficialLink href={ch.official_url}><Loc t={ch.label} /></OfficialLink> : <Loc t={ch.label} />}</li>
          ))}
        </ul>
        {detail.helplines.length > 0 && <p className="mt-3">{c.helplines}: {detail.helplines.map((h) => <a key={h} href={`tel:${h.replace(/\s/g, "")}`} className="mr-3 font-semibold underline">{h}</a>)}</p>}
      </section>
      <section className={card}>
        <h2 className="text-lg font-bold text-navy">{c.sourcesTitle}</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {detail.sources.map((s) => (
            <li key={s.id}><OfficialLink href={s.url}>{s.title}</OfficialLink> <span className="text-ink-muted">· {s.publisher} · {c.retrieved} {s.retrieved}</span></li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-ink-muted"><Loc t={detail.disclosure} /></p>
      </section>
    </div>
  );
}
