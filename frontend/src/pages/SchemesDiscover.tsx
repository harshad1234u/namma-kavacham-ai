import { useEffect, useId, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ErrorBox, Loading, Loc, OfficialLink, PageTitle, btnPrimary, card, input, label } from "../components/civic/ui";
import { useCivic } from "../i18n/civic";
import { useLanguage } from "../i18n/LanguageContext";
import { ApiError } from "../services/api";
import { getJson, postJson, query } from "../services/civicApi";
import { useAiStatus } from "../services/useAi";
import type { DiscoverResult, SchemeSummary } from "../types/civic";

// NEEDS NATIVE REVIEW (hi, ta)
export const NEED_LABELS: Record<string, Record<string, string>> = {
  en: {
    farming_income_support: "Farming income support", crop_insurance: "Crop insurance", health_insurance: "Health insurance",
    housing: "Housing", cooking_fuel: "Cooking gas (LPG)", employment: "Employment", education_scholarship: "Scholarship / education",
    pension_old_age: "Pension", insurance_life_accident: "Life / accident insurance", small_business_loan: "Small business loan",
    street_vendor_credit: "Street vendor loan", artisan_support: "Artisan / craft support", banking_access: "Bank account",
    drinking_water: "Drinking water", maternity_support: "Maternity support", girl_child_savings: "Girl child savings",
    skill_training: "Skill training",
  },
  hi: {
    farming_income_support: "किसान आय सहायता", crop_insurance: "फसल बीमा", health_insurance: "स्वास्थ्य बीमा", housing: "आवास",
    cooking_fuel: "रसोई गैस (एलपीजी)", employment: "रोज़गार", education_scholarship: "छात्रवृत्ति / शिक्षा", pension_old_age: "पेंशन",
    insurance_life_accident: "जीवन / दुर्घटना बीमा", small_business_loan: "छोटे व्यवसाय का ऋण", street_vendor_credit: "रेहड़ी-पटरी ऋण",
    artisan_support: "कारीगर सहायता", banking_access: "बैंक खाता", drinking_water: "पीने का पानी", maternity_support: "मातृत्व सहायता",
    girl_child_savings: "बालिका बचत", skill_training: "कौशल प्रशिक्षण",
  },
  ta: {
    farming_income_support: "விவசாய வருமான உதவி", crop_insurance: "பயிர் காப்பீடு", health_insurance: "மருத்துவக் காப்பீடு", housing: "வீட்டுவசதி",
    cooking_fuel: "சமையல் எரிவாயு (LPG)", employment: "வேலைவாய்ப்பு", education_scholarship: "கல்வி உதவித்தொகை", pension_old_age: "ஓய்வூதியம்",
    insurance_life_accident: "ஆயுள் / விபத்துக் காப்பீடு", small_business_loan: "சிறுதொழில் கடன்", street_vendor_credit: "தெருவோர வியாபாரி கடன்",
    artisan_support: "கைவினைஞர் உதவி", banking_access: "வங்கிக் கணக்கு", drinking_water: "குடிநீர்", maternity_support: "மகப்பேறு உதவி",
    girl_child_savings: "பெண் குழந்தை சேமிப்பு", skill_training: "திறன் பயிற்சி",
  },
};
const OCCUPATIONS = ["farmer", "agricultural_worker", "student", "self_employed", "salaried", "unorganised_worker", "street_vendor", "artisan", "unemployed", "homemaker"];

export function SchemesDiscover() {
  const { c } = useCivic();
  const { code } = useLanguage();
  const ai = useAiStatus();
  const needs = NEED_LABELS[code] ?? NEED_LABELS.en;
  const ids = { text: useId(), age: useId(), gender: useId(), occ: useId(), res: useId() };
  const [text, setText] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [profile, setProfile] = useState<Record<string, string>>({});
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DiscoverResult | null>(null);
  const [all, setAll] = useState<SchemeSummary[]>([]);

  useEffect(() => {
    getJson<SchemeSummary[]>(`/v1/schemes${query({ lang: code })}`).then(setAll).catch(() => setAll([]));
  }, [code]);

  const toggle = (t: string) => setTags((cur) => (cur.includes(t) ? cur.filter((x) => x !== t) : [...cur, t]));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const prof: Record<string, string | number> = {};
    for (const [k, v] of Object.entries(profile)) if (v) prof[k] = k === "age" ? Number(v) : v;
    try {
      setResult(await postJson<DiscoverResult>("/v1/schemes/discover", {
        text: text || null, need_tags: tags.length ? tags : null, profile: prof, lang: code, ai_consent: consent,
      }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : c.errorGeneric);
    } finally {
      setBusy(false);
    }
  }

  const sel = (key: string, id: string, title: string, opts: string[]) => (
    <div>
      <label htmlFor={id} className={label}>{title}</label>
      <select id={id} value={profile[key] ?? ""} onChange={(e) => setProfile({ ...profile, [key]: e.target.value })} className={`${input} mt-1`}>
        <option value="">{c.any}</option>
        {opts.map((o) => <option key={o} value={o}>{o.replace(/_/g, " ")}</option>)}
      </select>
    </div>
  );

  return (
    <div className="space-y-6">
      <PageTitle title={c.discoverTitle} subtitle={c.discoverSubtitle} />
      <form onSubmit={submit} className={`${card} space-y-4`}>
        <div>
          <label htmlFor={ids.text} className={label}>{c.needLabel}</label>
          <textarea id={ids.text} rows={2} maxLength={2000} value={text} onChange={(e) => setText(e.target.value)} placeholder={c.needPlaceholder} className={`${input} mt-2`} />
        </div>
        <fieldset>
          <legend className={label}>{c.orPick}</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {Object.entries(needs).map(([tag, name]) => (
              <button key={tag} type="button" aria-pressed={tags.includes(tag)} onClick={() => toggle(tag)}
                className={`min-h-9 rounded-full px-3 text-sm font-semibold ring-1 ${tags.includes(tag) ? "bg-navy text-white ring-navy" : "bg-white text-navy ring-line-strong"}`}>
                {name}
              </button>
            ))}
          </div>
        </fieldset>
        <fieldset className="grid gap-3 sm:grid-cols-4">
          <legend className={`${label} mb-2 sm:col-span-4`}>{c.profileTitle}</legend>
          <div>
            <label htmlFor={ids.age} className={label}>{c.age}</label>
            <input id={ids.age} type="number" min={0} max={120} value={profile.age ?? ""} onChange={(e) => setProfile({ ...profile, age: e.target.value })} className={`${input} mt-1`} />
          </div>
          {sel("gender", ids.gender, c.gender, ["female", "male", "other"])}
          {sel("occupation", ids.occ, c.occupation, OCCUPATIONS)}
          {sel("residence_type", ids.res, c.residence, ["rural", "urban"])}
        </fieldset>
        {ai?.ai_enabled && (
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-1 size-5" /> {c.aiConsent}
          </label>
        )}
        <button type="submit" disabled={busy || (!text.trim() && tags.length === 0)} className={btnPrimary}>{c.findSchemes}</button>
      </form>

      {busy && <Loading />}
      {error && <ErrorBox message={error} />}
      {result && (
        <section aria-live="polite" className={`${card} space-y-3`}>
          {result.suggestions.length === 0 ? (
            <p>{c.noResults} <OfficialLink href={result.search_portal}>myscheme.gov.in</OfficialLink></p>
          ) : (
            <ul className="space-y-3">
              {result.suggestions.map((s) => (
                <li key={s.scheme.id} className="rounded-md border border-line p-3">
                  <Link to={`/schemes/${s.scheme.id}`} className="text-lg font-bold text-teal-deep underline"><Loc t={s.scheme.name} /></Link>
                  <p className="mt-1 text-sm font-semibold">{c[`elig_${s.eligibility}`]}</p>
                  <p className="mt-1 text-sm text-ink-muted">
                    {s.matched_need_tags.length > 0 && <>{c.matchesNeed}: {s.matched_need_tags.map((t) => needs[t] ?? t).join(", ")}. </>}
                    {s.matched_profile.length > 0 && <>{c.matchesProfile}: {s.matched_profile.join(", ")}.</>}
                  </p>
                </li>
              ))}
            </ul>
          )}
          <p className="text-xs text-ink-muted"><Loc t={result.disclosure} /></p>
        </section>
      )}

      <section className={card}>
        <h2 className="text-lg font-bold text-navy">{c.allSchemes}</h2>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {all.map((s) => (
            <li key={s.id}>
              <Link to={`/schemes/${s.id}`} className="font-semibold text-teal-deep underline"><Loc t={s.name} /></Link>
              <span className="block text-xs text-ink-muted">{s.ministry} · {c.lastVerified} {s.last_verified}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
