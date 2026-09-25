import { CircleHelp, Link2, ShieldAlert } from "lucide-react";
import { useLanguage } from "../../i18n/LanguageContext";
import { VT_STATUS_LABELS } from "../../i18n/strings";
import type { AnalyzeResponse, ThreatIntelResult } from "../../types/analysis";
import { Section } from "./Section";

function ThreatIntelPanel({ result, enabled }: { result: ThreatIntelResult; enabled: boolean }) {
  const { lang, t } = useLanguage();
  const disabled =
    !enabled || result.unavailable_reason === "disabled_by_configuration" || result.unavailable_reason === "api_key_not_configured";
  const key = disabled ? "disabled" : result.status;
  const flagged = result.status === "malicious" || result.status === "suspicious";
  const tone = flagged
    ? "border-red-300 bg-red-50"
    : result.available && result.status !== "unknown"
      ? "border-line bg-surface-low"
      : "border-amber-300 bg-amber-50";
  const count = result.status === "malicious" ? result.engine_stats?.malicious : result.engine_stats?.suspicious;
  const note = lang === "ta" && result.note_ta ? result.note_ta : result.note;

  return (
    <div className={`rounded-md border p-4 ${tone}`} data-testid="vt-panel">
      <p className="text-sm font-semibold text-navy">{t.vtTitle}</p>
      <p className="mt-1 flex items-center gap-2 font-semibold">
        {flagged ? <ShieldAlert className="size-4 text-red-700" aria-hidden /> : <CircleHelp className="size-4 text-amber-700" aria-hidden />}
        {VT_STATUS_LABELS[lang][key]}
      </p>
      {flagged && result.engines_total != null && (
        <p className="mt-1 text-sm">
          <span className="text-xl font-bold text-red-800">
            {count} / {result.engines_total}
          </span>{" "}
          {t.vendorsFlagged}
        </p>
      )}
      <p className="mt-2 text-xs text-ink-muted">{note}</p>
    </div>
  );
}

const PROVIDER_NAMES = { groq: "Groq", gemini: "Gemini" } as const;

function StatusRow({ label, value, tone }: { label: string; value: string; tone: "ok" | "warn" | "muted" }) {
  const style = { ok: "bg-slate-100 text-slate-800", warn: "bg-amber-50 text-amber-900 ring-1 ring-amber-200", muted: "bg-surface text-ink-muted" }[tone];
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-ink">{label}</span>
      <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${style}`}>{value}</span>
    </div>
  );
}

export function ProviderStatus({ result }: { result: AnalyzeResponse }) {
  const { t } = useLanguage();
  const { url_intelligence: urls, provider_flags: flags, explanation } = result;
  const hasUrl = urls.extracted_urls.length > 0;
  const vt = !hasUrl
    ? { value: t.statusNotNeeded, tone: "muted" as const }
    : !flags.virustotal_enabled
      ? { value: t.statusOff, tone: "warn" as const }
      : flags.virustotal_available
        ? { value: t.statusOn, tone: "ok" as const }
        : { value: t.statusUnavailable, tone: "warn" as const };
  const aiStatus = explanation.ai_status ?? "disabled";
  // Named from the configured provider, so the row never claims a provider that is not in use.
  const aiLabel = flags.ai_provider === "template" ? t.aiRow : `${t.aiRow} (${PROVIDER_NAMES[flags.ai_provider]})`;
  const ai =
    aiStatus === "generated"
      ? { value: t.statusOn, tone: "ok" as const }
      : { value: t.aiStates[aiStatus], tone: aiStatus === "disabled" ? ("muted" as const) : ("warn" as const) };

  return (
    <Section id="links" icon={<Link2 className="size-5" aria-hidden />} title={t.urlIntelTitle}>
      <div className="flex flex-col gap-2 rounded-md border border-line p-3" data-testid="provider-status">
        <p className="text-xs font-semibold uppercase tracking-wide text-navy-soft">{t.providerStatusTitle}</p>
        <StatusRow label={t.vtRow} {...vt} />
        <StatusRow label={aiLabel} {...ai} />
      </div>
      {hasUrl ? (
        <div className="mt-4 flex flex-col gap-3">
          <div>
            <p className="text-sm font-semibold text-navy">{t.linksFound}</p>
            <ul className="mt-1 flex flex-col gap-1">
              {urls.extracted_urls.map((url) => (
                <li key={url} className="break-all font-mono text-xs text-navy-soft">
                  {url}
                </li>
              ))}
            </ul>
          </div>
          {urls.provider_result && <ThreatIntelPanel result={urls.provider_result} enabled={urls.provider_enabled} />}
          {urls.privacy_note && <p className="text-xs text-ink-muted">{urls.privacy_note}</p>}
        </div>
      ) : (
        <p className="mt-4 text-sm text-ink-muted">{t.noLinks}</p>
      )}
    </Section>
  );
}
