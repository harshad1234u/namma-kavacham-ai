import { AlertTriangle, Info, ListChecks } from "lucide-react";
import { useLanguage } from "../../i18n/LanguageContext";
import { CONFIDENCE_LABELS } from "../../i18n/strings";
import type { Confidence, EvidenceItem } from "../../types/analysis";
import { Section } from "./Section";

const CONFIDENCE_STYLE: Record<Confidence, string> = {
  high: "bg-red-50 text-red-800 ring-red-200",
  medium: "bg-amber-50 text-amber-800 ring-amber-200",
  low: "bg-slate-100 text-slate-700 ring-slate-200",
};

function EvidenceCard({ item }: { item: EvidenceItem }) {
  const { lang, t } = useLanguage();
  const description = lang === "ta" && item.description_ta ? item.description_ta : item.description_en;
  return (
    <li className="rounded-md border border-line p-4" data-testid="evidence-item">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${CONFIDENCE_STYLE[item.confidence]}`}>
          <AlertTriangle className="size-3" aria-hidden /> {CONFIDENCE_LABELS[lang][item.confidence]}
        </span>
        {item.rule_id && <span className="font-mono text-xs text-ink-muted">{item.rule_id}</span>}
      </div>
      <p className="mt-2 text-sm text-ink">{description}</p>
      {item.observed && (
        <p className="mt-2 break-all rounded bg-surface-low px-2 py-1 font-mono text-xs text-navy-soft">
          <span className="font-sans font-semibold">{t.observed}:</span> {item.observed}
        </p>
      )}
    </li>
  );
}

export function EvidenceList({ evidence }: { evidence: EvidenceItem[] }) {
  const { lang, t } = useLanguage();
  const risk = evidence.filter((e) => e.kind === "risk");
  const info = evidence.filter((e) => e.kind === "info");
  return (
    <Section id="why" icon={<ListChecks className="size-5" aria-hidden />} title={t.whyTitle}>
      {risk.length === 0 ? (
        <p className="text-sm text-ink-muted">{t.noIndicators}</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {risk.map((item, i) => (
            <EvidenceCard key={`${item.signal}-${i}`} item={item} />
          ))}
        </ul>
      )}
      {info.length > 0 && (
        <div className="mt-4">
          <p className="text-sm font-semibold text-navy">{t.contextNotes}</p>
          <ul className="mt-2 flex flex-col gap-2">
            {info.map((item, i) => (
              <li key={i} className="flex gap-2 text-sm text-ink-muted">
                <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
                {lang === "ta" && item.description_ta ? item.description_ta : item.description_en}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Section>
  );
}
