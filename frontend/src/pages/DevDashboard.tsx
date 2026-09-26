import { AlertTriangle, Flame } from "lucide-react";
import { useEffect, useId, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { HotspotMap } from "../components/civic/HotspotMap";
import { Bars, ErrorBox, LevelBadge, Loading, PageTitle, ProvenanceBadge, Stat, btnPrimary, btnSecondary, card, input, label } from "../components/civic/ui";
import { useCivic } from "../i18n/civic";
import { useLanguage } from "../i18n/LanguageContext";
import { getJson, query } from "../services/civicApi";
import type { Dashboard, DevMeta, IssueSummary } from "../types/civic";

const LEVELS = ["unable_to_assess", "lower", "medium", "high", "critical"] as const;
const FILTER_KEYS = ["state", "district", "category", "min_level", "date_from", "date_to"] as const;
const title = (s: string) => s.toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase());

export function DevDashboard() {
  const { c } = useCivic();
  const { code } = useLanguage();
  const [params, setParams] = useSearchParams();
  const [meta, setMeta] = useState<DevMeta | null>(null);
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [issues, setIssues] = useState<IssueSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState("priority");
  const fid = useId();
  const filters = Object.fromEntries(FILTER_KEYS.map((k) => [k, params.get(k) ?? ""])) as Record<(typeof FILTER_KEYS)[number], string>;
  const [draft, setDraft] = useState(filters);

  useEffect(() => {
    getJson<DevMeta>("/v1/development/meta").then(setMeta).catch(() => undefined);
  }, []);

  const qs = params.toString();
  useEffect(() => {
    const f = Object.fromEntries(new URLSearchParams(qs));
    setError(null);
    const common = { state: f.state, district: f.district, category: f.category, date_from: f.date_from, date_to: f.date_to };
    Promise.all([
      getJson<Dashboard>(`/v1/development/dashboard${query(common)}`),
      getJson<IssueSummary[]>(`/v1/development/issues${query({ ...common, min_level: f.min_level, sort })}`),
    ])
      .then(([d, i]) => { setDash(d); setIssues(i); })
      .catch(() => setError(c.errorGeneric));
  }, [qs, sort, c.errorGeneric]);

  function apply(e: FormEvent) {
    e.preventDefault();
    setParams(Object.fromEntries(Object.entries(draft).filter(([, v]) => v)));
  }

  const catLabel = (id: string) => meta?.categories.find((k) => k.id === id)?.labels[code] ?? id;
  return (
    <div className="space-y-6">
      <PageTitle title={c.dashTitle} subtitle={c.dashSubtitle} />
      <p role="note" className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-900">
        <AlertTriangle className="size-5 shrink-0" aria-hidden /> {c.demoBanner}
      </p>

      <form onSubmit={apply} className={`${card} grid gap-3 sm:grid-cols-3 lg:grid-cols-6`} aria-label={c.filters}>
        <div>
          <label htmlFor={`${fid}s`} className={label}>{c.state}</label>
          <select id={`${fid}s`} value={draft.state} onChange={(e) => setDraft({ ...draft, state: e.target.value })} className={`${input} mt-1`}>
            <option value="">{c.all}</option>
            {meta?.states_and_uts.map((s) => <option key={s} value={s}>{title(s)}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor={`${fid}d`} className={label}>{c.district}</label>
          <input id={`${fid}d`} value={draft.district} onChange={(e) => setDraft({ ...draft, district: e.target.value })} className={`${input} mt-1`} />
        </div>
        <div>
          <label htmlFor={`${fid}c`} className={label}>{c.category}</label>
          <select id={`${fid}c`} value={draft.category} onChange={(e) => setDraft({ ...draft, category: e.target.value })} className={`${input} mt-1`}>
            <option value="">{c.all}</option>
            {meta?.categories.map((k) => <option key={k.id} value={k.id}>{k.labels[code] ?? k.labels.en}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor={`${fid}l`} className={label}>{c.minPriority}</label>
          <select id={`${fid}l`} value={draft.min_level} onChange={(e) => setDraft({ ...draft, min_level: e.target.value })} className={`${input} mt-1`}>
            <option value="">{c.all}</option>
            {LEVELS.slice(1).map((l) => <option key={l} value={l}>{c[`level_${l}`]}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor={`${fid}f`} className={label}>{c.from}</label>
          <input id={`${fid}f`} type="date" value={draft.date_from} onChange={(e) => setDraft({ ...draft, date_from: e.target.value })} className={`${input} mt-1`} />
        </div>
        <div>
          <label htmlFor={`${fid}t`} className={label}>{c.to}</label>
          <input id={`${fid}t`} type="date" value={draft.date_to} onChange={(e) => setDraft({ ...draft, date_to: e.target.value })} className={`${input} mt-1`} />
        </div>
        <div className="flex gap-2 sm:col-span-3 lg:col-span-6">
          <button type="submit" className={btnPrimary}>{c.apply}</button>
          <button type="button" className={btnSecondary} onClick={() => { setDraft(Object.fromEntries(FILTER_KEYS.map((k) => [k, ""])) as typeof draft); setParams({}); }}>{c.reset}</button>
        </div>
      </form>

      {error && <ErrorBox message={error} />}
      {!dash && !error && <Loading />}
      {dash && issues && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label={c.totalRequests} value={dash.total_requests.toLocaleString("en-IN")} />
            <Stat label={c.activeIssues} value={dash.active_issues} />
            <Stat label={c.hotspots} value={dash.hotspots} />
            <Stat label={c.highPriority} value={dash.high_priority_issues} />
          </div>

          <section className={`${card} space-y-3`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-bold text-navy">{c.hotspotList}</h2>
              <ProvenanceBadge source={dash.provenance} />
            </div>
            <HotspotMap issues={issues} />
            <div className="flex items-center gap-2 text-sm">
              <label htmlFor={`${fid}sort`}>Sort</label>
              <select id={`${fid}sort`} value={sort} onChange={(e) => setSort(e.target.value)} className="rounded-md border border-line-strong px-2 py-1">
                <option value="priority">{c.priority}</option>
                <option value="reports">{c.reports}</option>
                <option value="urgency">{c.urgency}</option>
              </select>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[36rem] text-left text-sm">
                <thead>
                  <tr className="border-b border-line text-navy-soft">
                    <th scope="col" className="py-2 pr-3">{c.area}</th>
                    <th scope="col" className="py-2 pr-3">{c.category}</th>
                    <th scope="col" className="py-2 pr-3 text-right">{c.reports}</th>
                    <th scope="col" className="py-2 pr-3">{c.priority}</th>
                    <th scope="col" className="py-2">{c.gap}</th>
                  </tr>
                </thead>
                <tbody>
                  {issues.map((i) => (
                    <tr key={i.id} className="border-b border-line last:border-0">
                      <td className="py-2 pr-3">
                        <Link to={`/dev/hotspots/${i.id}`} className="font-semibold text-teal-deep underline">
                          {[i.locality, i.district].filter(Boolean).join(", ")}
                        </Link>
                        {i.hotspot && <Flame className="ml-1 inline size-4 text-red-600" aria-label={c.hotspots} />}
                      </td>
                      <td className="py-2 pr-3">{catLabel(i.category)}</td>
                      <td className="py-2 pr-3 text-right tabular-nums">{i.report_count}</td>
                      <td className="py-2 pr-3"><LevelBadge level={i.priority_level} score={i.priority_score} /></td>
                      <td className="py-2">{c[`gap_${i.gap_level}` as keyof typeof c]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            <section className={card}><h2 className="mb-3 font-bold text-navy">{c.topNeeds}</h2><Bars rows={dash.by_category.slice(0, 8)} /></section>
            <section className={card}><h2 className="mb-3 font-bold text-navy">{c.requestsOverTime}</h2><Bars rows={dash.requests_over_time.map(([d, n]) => [d.slice(5), n])} color="#354763" /></section>
            <section className={card}>
              <h2 className="mb-3 font-bold text-navy">{c.priorityDistribution}</h2>
              <Bars rows={LEVELS.slice().reverse().map((l) => [c[`level_${l}`], dash.priority_distribution[l] ?? 0])} color="#f97316" />
            </section>
            <section className={card}><h2 className="mb-3 font-bold text-navy">{c.byDistrict}</h2><Bars rows={dash.by_district.map(([d, n]) => [title(d), n])} color="#0f233d" /></section>
            {dash.scheme_demand.length > 0 && (
              <section className={card}>
                <h2 className="mb-3 font-bold text-navy">{c.schemeDemand}</h2>
                <Bars rows={dash.scheme_demand.map((s) => [`${s.scheme} · ${s.district}`, s.mentions])} color="#006a61" />
              </section>
            )}
          </div>
          <p className="text-xs text-ink-muted">{dash.disclaimer}</p>
        </>
      )}
    </div>
  );
}
