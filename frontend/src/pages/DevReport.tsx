import { CheckCircle2, Mic, Square } from "lucide-react";
import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ErrorBox, Loading, PageTitle, btnPrimary, btnSecondary, card, input, label } from "../components/civic/ui";
import { str, useCivic } from "../i18n/civic";
import { useLanguage } from "../i18n/LanguageContext";
import { ApiError } from "../services/api";
import { getJson, postForm, query } from "../services/civicApi";
import { VoiceError, listen, voiceSupported } from "../services/voiceInput";
import type { DevMeta, Receipt } from "../types/civic";

// Report ids live only in this tab's memory (no cookies, no localStorage).
export const sessionReports: string[] = [];

const title = (s: string) => s.toLowerCase().replace(/\b\w/g, (m) => m.toUpperCase());

export function DevReport() {
  const { c } = useCivic();
  const { code } = useLanguage();
  const ids = { text: useId(), state: useId(), district: useId(), area: useId(), loc: useId(), pin: useId(), cat: useId(), photo: useId() };
  const [meta, setMeta] = useState<DevMeta | null>(null);
  const [text, setText] = useState("");
  const [state, setState] = useState("");
  const [district, setDistrict] = useState("");
  const [areaId, setAreaId] = useState("");
  const [locality, setLocality] = useState("");
  const [pincode, setPincode] = useState("");
  const [category, setCategory] = useState("");
  const [urgency, setUrgency] = useState<"" | "low" | "medium" | "high">("");
  const [consent, setConsent] = useState(false);
  const [voiceOk, setVoiceOk] = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceErr, setVoiceErr] = useState<string | null>(null);
  const [source, setSource] = useState<"text" | "voice">("text");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const stopRef = useRef<() => void>(() => {});
  const photoRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getJson<DevMeta>("/v1/development/meta").then(setMeta).catch(() => setError(c.errorGeneric));
  }, [c.errorGeneric]);

  const demoDistricts = meta ? [...new Set(meta.demo_areas.filter((a) => a.state === state).map((a) => a.district))] : [];
  const demoAreas = meta?.demo_areas.filter((a) => a.state === state && a.district === district) ?? [];

  async function speak() {
    setVoiceErr(null);
    setListening(true);
    const { result, stop } = listen(code);
    stopRef.current = stop;
    try {
      const said = await result;
      setText((t) => (t ? `${t} ${said}` : said));
      setSource("voice");
    } catch (err) {
      setVoiceErr(c[`voice_${err instanceof VoiceError ? err.kind : "failed"}`]);
    } finally {
      setListening(false);
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData();
    form.append("payload", JSON.stringify({
      text, lang: code, state, district, area_id: areaId || null, locality: locality || null, pincode: pincode || null,
      category: category || null, urgency: urgency || null, source, consent: true, ai_consent: false,
    }));
    const photo = photoRef.current?.files?.[0];
    if (photo) form.append("photo", photo);
    try {
      const r = await postForm<Receipt>("/v1/development/requests", form);
      sessionReports.push(r.id);
      setReceipt(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : c.errorGeneric);
    } finally {
      setBusy(false);
    }
  }

  if (receipt) {
    return (
      <div className="space-y-4">
        <div className={`${card} space-y-3`} role="status">
          <p className="flex items-center gap-2 text-xl font-bold text-teal-deep"><CheckCircle2 className="size-6" aria-hidden /> {c.received}</p>
          <dl className="grid gap-2 sm:grid-cols-2">
            <div><dt className="text-sm text-ink-muted">{c.category}</dt><dd className="font-semibold">{receipt.category_label}</dd></div>
            <div><dt className="text-sm text-ink-muted">{c.area}</dt><dd className="font-semibold">{[receipt.locality, receipt.district, title(receipt.state)].filter(Boolean).join(", ")}</dd></div>
          </dl>
          <ol className="flex flex-wrap gap-2" aria-label="Status">
            {receipt.statuses.map((s) => <li key={s} className="rounded-full bg-teal/15 px-3 py-1 text-sm font-semibold text-teal-deep">{str(c, `status_${s}`)}</li>)}
          </ol>
          <p className="text-sm text-ink-muted">{receipt.note}</p>
          <p className="font-mono text-sm">#{receipt.id}</p>
          <div className="flex flex-wrap gap-2">
            <Link to={`/dev/hotspots/${receipt.issue_id}`} className={btnSecondary}>{c.viewIssue}</Link>
            <Link to="/dev/my-reports" className={btnSecondary}>{c.myReports}</Link>
            <button type="button" className={btnSecondary} onClick={() => { setReceipt(null); setText(""); setConsent(false); }}>{c.reportTitle}</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageTitle title={c.reportTitle} subtitle={c.reportSubtitle} />
      {!meta && !error && <Loading />}
      {error && <ErrorBox message={error} />}
      {meta && (
        <form onSubmit={submit} className={`${card} space-y-5`}>
          <div>
            <label htmlFor={ids.text} className={label}>{c.issueLabel} <span className="text-red-600">*</span></label>
            <textarea id={ids.text} required minLength={3} maxLength={2000} rows={4} value={text} onChange={(e) => setText(e.target.value)} placeholder={c.issuePlaceholder} className={`${input} mt-2`} />
            <div className="mt-2 space-y-2">
              {!voiceSupported() ? (
                <p className="text-sm text-ink-muted">{c.voice_unsupported}</p>
              ) : !voiceOk ? (
                <div className="rounded-md bg-surface-low p-3 text-sm">
                  <p>{c.voiceNotice}</p>
                  <button type="button" onClick={() => setVoiceOk(true)} className={`${btnSecondary} mt-2`}>{c.voiceAllow}</button>
                </div>
              ) : listening ? (
                <button type="button" onClick={() => stopRef.current()} className={btnSecondary}><Square className="size-4" aria-hidden /> {c.stopListening} · {c.listening}</button>
              ) : (
                <button type="button" onClick={speak} className={btnSecondary}><Mic className="size-4" aria-hidden /> {c.speak}</button>
              )}
              {voiceErr && <p role="alert" className="text-sm text-red-700">{voiceErr}</p>}
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor={ids.state} className={label}>{c.state} <span className="text-red-600">*</span></label>
              <select id={ids.state} required value={state} onChange={(e) => { setState(e.target.value); setDistrict(""); setAreaId(""); }} className={`${input} mt-1`}>
                <option value="" />
                {meta.states_and_uts.map((s) => <option key={s} value={s}>{title(s)}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor={ids.district} className={label}>{c.district} <span className="text-red-600">*</span></label>
              <input id={ids.district} required minLength={2} maxLength={60} list={`${ids.district}-list`} value={district} onChange={(e) => { setDistrict(e.target.value); setAreaId(""); }} className={`${input} mt-1`} />
              <datalist id={`${ids.district}-list`}>{demoDistricts.map((d) => <option key={d} value={d} />)}</datalist>
            </div>
            {demoAreas.length > 0 ? (
              <div>
                <label htmlFor={ids.area} className={label}>{c.locality}</label>
                <select id={ids.area} value={areaId} onChange={(e) => setAreaId(e.target.value)} className={`${input} mt-1`}>
                  <option value="" />
                  {demoAreas.map((a) => <option key={a.area_id} value={a.area_id}>{a.area}</option>)}
                </select>
              </div>
            ) : (
              <div>
                <label htmlFor={ids.loc} className={label}>{c.localityText}</label>
                <input id={ids.loc} maxLength={80} value={locality} onChange={(e) => setLocality(e.target.value)} className={`${input} mt-1`} />
              </div>
            )}
            <div>
              <label htmlFor={ids.pin} className={label}>{c.pincode}</label>
              <input id={ids.pin} inputMode="numeric" pattern="[1-9][0-9]{5}" maxLength={6} value={pincode} onChange={(e) => setPincode(e.target.value)} className={`${input} mt-1`} />
            </div>
            <div>
              <label htmlFor={ids.cat} className={label}>{c.category}</label>
              <select id={ids.cat} value={category} onChange={(e) => setCategory(e.target.value)} className={`${input} mt-1`}>
                <option value="">{c.autoDetect}</option>
                {meta.categories.map((k) => <option key={k.id} value={k.id}>{k.labels[code] ?? k.labels.en}</option>)}
              </select>
            </div>
            <fieldset>
              <legend className={label}>{c.urgency}</legend>
              <div className="mt-1 flex gap-2">
                {(["low", "medium", "high"] as const).map((u) => (
                  <button key={u} type="button" aria-pressed={urgency === u} onClick={() => setUrgency(urgency === u ? "" : u)}
                    className={`min-h-11 flex-1 rounded-md px-3 font-semibold ring-1 ${urgency === u ? "bg-navy text-white ring-navy" : "bg-white text-navy ring-line-strong"}`}>{c[u]}</button>
                ))}
              </div>
            </fieldset>
          </div>
          <div>
            <label htmlFor={ids.photo} className={label}>{c.addPhoto}</label>
            <input id={ids.photo} ref={photoRef} type="file" accept="image/jpeg,image/png,image/webp" className="mt-1 block w-full text-sm" />
            <p className="mt-1 text-xs text-ink-muted">{c.photoNote}</p>
          </div>
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" required checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-1 size-5" /> {c.consent}
          </label>
          <button type="submit" disabled={busy || !consent || text.trim().length < 3 || !state || district.trim().length < 2} className={btnPrimary}>
            {busy ? c.submitting : c.submitReport}
          </button>
        </form>
      )}
    </div>
  );
}

export function DevMyReports() {
  const { c } = useCivic();
  const [items, setItems] = useState<Receipt[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!sessionReports.length) return setItems([]);
    getJson<Receipt[]>(`/v1/development/requests${query({ ids: sessionReports.join(",") })}`).then(setItems).catch(() => setError(c.errorGeneric));
  }, [c.errorGeneric]);
  return (
    <div className="space-y-4">
      <PageTitle title={c.myReports} subtitle={c.sessionOnly} />
      {error && <ErrorBox message={error} />}
      {!items && !error && <Loading />}
      {items?.length === 0 && <p className={card}>{c.myReportsEmpty} <Link to="/dev/report" className="font-semibold underline">{c.reportTitle}</Link></p>}
      {items?.map((r) => (
        <div key={r.id} className={card}>
          <p className="font-bold text-navy">{r.category_label} · {r.district}</p>
          <p className="font-mono text-xs">#{r.id} · {r.created_at}</p>
          <ol className="mt-2 flex flex-wrap gap-2">{r.statuses.map((s) => <li key={s} className="rounded-full bg-teal/15 px-3 py-1 text-xs font-semibold text-teal-deep">{str(c, `status_${s}`)}</li>)}</ol>
          <Link to={`/dev/hotspots/${r.issue_id}`} className="mt-2 inline-block text-sm font-semibold underline">{c.viewIssue}</Link>
        </div>
      ))}
    </div>
  );
}
