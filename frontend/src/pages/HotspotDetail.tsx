import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Bars, ErrorBox, ExplanationBlock, LevelBadge, Loading, PageTitle, ProvenanceBadge, card } from "../components/civic/ui";
import { useCivic } from "../i18n/civic";
import { useLanguage } from "../i18n/LanguageContext";
import { ApiError } from "../services/api";
import { getJson, query } from "../services/civicApi";
import type { IssueDetail } from "../types/civic";

const title = (s: string) => s.toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase());

export function HotspotDetail() {
  const { id = "" } = useParams();
  const { c } = useCivic();
  const { code } = useLanguage();
  const [d, setD] = useState<IssueDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    setError(null);
    getJson<IssueDetail>(`/v1/development/hotspots/${encodeURIComponent(id)}${query({ lang: code })}`)
      .then(setD)
      .catch((err) => setError(err instanceof ApiError ? err.message : c.errorGeneric));
  }, [id, code, c.errorGeneric]);
  useEffect(load, [load]);

  if (error) return <ErrorBox message={error} onRetry={load} />;
  if (!d) return <Loading />;
  const place = [d.locality, d.district, title(d.state)].filter(Boolean).join(", ");
  return (
    <div className="space-y-4">
      <Link to="/dev" className="text-sm font-semibold text-teal-deep underline">← {c.back}</Link>
      <PageTitle title={`${place} — ${d.category_label}`} />
      <div className="-mt-3 flex flex-wrap items-center gap-2">
        <LevelBadge level={d.priority_level} score={d.priority_score} />
        <span className="rounded-full bg-surface px-3 py-1 text-xs font-semibold">{c[`gap_${d.gap_level}` as keyof typeof c]}</span>
        <span className="rounded-full bg-surface px-3 py-1 text-xs font-semibold">{d.report_count} {c.reports}</span>
        {Object.entries(d.provenance).slice(0, 1).map(([k, p]) => <ProvenanceBadge key={k} source={p} />)}
      </div>

      <section className={card}>
        <h2 className="text-lg font-bold text-navy">{c.insight}</h2>
        <div className="mt-2"><ExplanationBlock e={d.insight} /></div>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className={card}>
          <h2 className="text-lg font-bold text-navy">{c.scoreBreakdown}</h2>
          <p className="text-sm text-ink-muted">{c.dataCompleteness}: {Math.round(d.data_completeness * 100)}%</p>
          <ul className="mt-3 space-y-3">
            {d.components.map((comp) => (
              <li key={comp.name}>
                <div className="flex justify-between text-sm font-semibold">
                  <span>{c[`comp_${comp.name}` as keyof typeof c] ?? comp.name}</span>
                  <span className="tabular-nums">{comp.assessed ? `+${comp.points}` : c.notAssessed}</span>
                </div>
                <div className="mt-1 h-2 rounded bg-surface" aria-hidden>
                  {comp.assessed && <div className="h-2 rounded bg-teal" style={{ width: `${(comp.value ?? 0) * 100}%` }} />}
                </div>
                <p className="mt-1 text-xs text-ink-muted">{comp.note}</p>
              </li>
            ))}
          </ul>
        </section>
        <section className={card}>
          <h2 className="text-lg font-bold text-navy">{c.whyPriority}</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5">{d.gap_reasons.map((r) => <li key={r}>{r}</li>)}</ul>
        </section>
        <section className={card}>
          <h2 className="text-lg font-bold text-navy">{c.context}</h2>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
            <dt className="text-ink-muted">{c.population}</dt>
            <dd className="font-semibold">{d.population?.toLocaleString("en-IN") ?? c.notAssessed}</dd>
            <dt className="text-ink-muted">{c.infrastructure}</dt>
            <dd className="font-semibold">{d.infrastructure_value !== null && d.infrastructure_metric ? `${d.infrastructure_value} ${d.infrastructure_metric.replace(/_/g, " ")}` : c.notAssessed}</dd>
          </dl>
          <h3 className="mt-4 font-semibold">{c.projects}</h3>
          {d.projects.length === 0 ? <p className="text-sm text-ink-muted">{c.noProjects}</p> : (
            <ul className="mt-1 space-y-1 text-sm">{d.projects.map((p) => <li key={p.project_id}>{p.name} — <strong>{p.status}</strong> · ₹{p.budget_inr.toLocaleString("en-IN")}</li>)}</ul>
          )}
        </section>
        <section className={card}>
          <h2 className="text-lg font-bold text-navy">{c.complaintThemes}</h2>
          <div className="mt-3"><Bars rows={d.themes} color="#c2410c" /></div>
        </section>
        <section className={card}>
          <h2 className="text-lg font-bold text-navy">{c.timeline}</h2>
          <div className="mt-3"><Bars rows={d.timeline.map(([w, n]) => [w.slice(5), n])} color="#354763" /></div>
        </section>
        {d.relevant_schemes.length > 0 && (
          <section className={card}>
            <h2 className="text-lg font-bold text-navy">{c.relevantSchemes}</h2>
            <ul className="mt-3 space-y-1">{d.relevant_schemes.map((s) => <li key={s.id}><Link to={`/schemes/${s.id}`} className="font-semibold text-teal-deep underline">{s.name}</Link></li>)}</ul>
          </section>
        )}
      </div>
      <p className="text-xs text-ink-muted">{d.disclaimer}</p>
    </div>
  );
}
