import { CheckCircle2, CircleHelp, Landmark, MinusCircle, XCircle } from "lucide-react";
import type { ReactNode } from "react";
import { useLanguage } from "../../i18n/LanguageContext";
import { GOV_STATUS_LABELS } from "../../i18n/strings";
import type { FindingOutcome, GovernmentClaimResult, GovernmentClaimStatus } from "../../types/analysis";
import { Section } from "./Section";

// No status uses the teal "safe" styling: even a supported claim does not make a message genuine.
const STATUS_STYLE: Record<GovernmentClaimStatus, string> = {
  contradicted_by_curated_kb: "bg-red-50 text-red-900 ring-red-300",
  partially_supported_by_curated_kb: "bg-amber-50 text-amber-900 ring-amber-300",
  not_found_in_curated_kb: "bg-amber-50 text-amber-900 ring-amber-200",
  unable_to_assess: "bg-slate-100 text-slate-800 ring-slate-300",
  supported_by_curated_kb: "bg-slate-100 text-slate-800 ring-slate-300",
  not_government_related: "bg-surface text-ink-muted ring-line",
};

const OUTCOME_ICON: Record<FindingOutcome, ReactNode> = {
  supported: <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-slate-600" aria-hidden />,
  contradicted: <XCircle className="mt-0.5 size-4 shrink-0 text-red-700" aria-hidden />,
  not_covered: <MinusCircle className="mt-0.5 size-4 shrink-0 text-amber-700" aria-hidden />,
  ambiguous: <CircleHelp className="mt-0.5 size-4 shrink-0 text-amber-700" aria-hidden />,
};

// Mirrors the KB loader's rule (https on a .gov.in / .nic.in domain), so nothing else is ever shown as official.
function isOfficialUrl(url: string | null): url is string {
  try {
    const u = new URL(url ?? "");
    return u.protocol === "https:" && /\.(gov|nic)\.in$/.test(u.hostname);
  } catch {
    return false;
  }
}

export function GovernmentClaimCard({ gov }: { gov: GovernmentClaimResult }) {
  const { lang, t } = useLanguage();
  const limitations = lang === "ta" && gov.limitations_ta?.length ? gov.limitations_ta : gov.limitations;
  const disclosure = lang === "ta" && gov.disclosure_ta ? gov.disclosure_ta : gov.disclosure;
  // Guidance and official sites exist only for claims matched to a curated KB entry.
  const matchedIds = gov.matched_kb_entries ?? [];
  const matched = matchedIds.length > 0;
  const guidance = !matched ? [] : (lang === "ta" && gov.safe_guidance_ta?.length ? gov.safe_guidance_ta : gov.safe_guidance_en) ?? [];
  const officialUrls = !matched
    ? []
    : [...new Set(gov.sources.filter((s) => matchedIds.includes(s.kb_entry_id)).map((s) => s.official_url))].filter(isOfficialUrl);

  return (
    <Section id="gov" icon={<Landmark className="size-5" aria-hidden />} title={t.govTitle}>
      <span
        data-testid="gov-status"
        data-status={gov.claim_status}
        className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ring-1 ${STATUS_STYLE[gov.claim_status]}`}
      >
        {GOV_STATUS_LABELS[lang][gov.claim_status]}
      </span>

      {gov.claims.length > 0 && (
        <div className="mt-4">
          <p className="text-sm font-semibold text-navy">{t.claimsDetected}</p>
          <ul className="mt-2 flex flex-col gap-2">
            {gov.claims.map((claim, i) => (
              <li key={i} className="rounded-md bg-surface-low p-2 text-sm">
                <span className="font-semibold text-navy">{claim.scheme_or_service.value}</span>
                {claim.scheme_or_service.ambiguous && (
                  <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-semibold text-amber-900">{t.ambiguousClaim}</span>
                )}
                {!claim.kb_entry_id && !claim.scheme_or_service.ambiguous && (
                  <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-semibold text-amber-900">{t.notInReference}</span>
                )}
                {claim.requested_actions.length > 0 && (
                  <p className="mt-1 text-xs text-ink-muted">
                    {t.requestedActions}: {claim.requested_actions.map((a) => t.actions[a] ?? a).join(" · ")}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {gov.findings.length > 0 && (
        <div className="mt-4">
          <p className="text-sm font-semibold text-navy">{t.findingsTitle}</p>
          <ul className="mt-2 flex flex-col gap-2">
            {gov.findings.map((f, i) => (
              <li key={i} className="flex gap-2 text-sm" data-testid="kb-finding" data-outcome={f.outcome}>
                {OUTCOME_ICON[f.outcome]}
                <span>
                  <span className="font-semibold text-navy">{t.findingOutcomes[f.outcome]}: </span>
                  {lang === "ta" && f.detail_ta ? f.detail_ta : f.detail_en}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {limitations.map((l) => (
        <p key={l} className="mt-3 text-sm text-ink-muted">
          {l}
        </p>
      ))}

      {guidance.length > 0 && (
        <div className="mt-4" data-testid="gov-guidance">
          <p className="text-sm font-semibold text-navy">{t.govGuidanceTitle}</p>
          <ul className="mt-1 list-disc pl-5 text-sm">
            {guidance.map((g) => (
              <li key={g}>{g}</li>
            ))}
          </ul>
        </div>
      )}

      {officialUrls.length > 0 && (
        <div className="mt-3" data-testid="gov-official-sites">
          <p className="text-sm font-semibold text-navy">{t.officialSitesTitle}</p>
          <ul className="mt-1 flex flex-col gap-1 text-sm">
            {officialUrls.map((url) => (
              <li key={url}>
                <a href={url} target="_blank" rel="noopener noreferrer" className="inline-block break-all py-1 font-mono text-navy underline">
                  {url}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {gov.sources.length > 0 && (
        <details className="mt-3 text-xs text-ink-muted">
          <summary className="cursor-pointer font-semibold text-navy">{t.sourcesTitle}</summary>
          <ul className="mt-2 flex flex-col gap-2">
            {gov.sources.map((s, i) => (
              <li key={i}>
                <span className="font-semibold text-navy">{s.source_citation ?? s.name}</span>
                {s.published && ` · ${t.published} ${s.published}`}
                {s.source_url && <span className="block break-all font-mono">{s.source_url}</span>}
              </li>
            ))}
          </ul>
        </details>
      )}

      {gov.government_related && <p className="mt-3 rounded bg-surface-low p-2 text-xs text-navy-soft">{disclosure}</p>}
    </Section>
  );
}
