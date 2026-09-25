import { AlertTriangle, Ban, FileWarning, Info, Phone, RotateCcw } from "lucide-react";
import { useLanguage } from "../i18n/LanguageContext";
import { LEVEL_ACTIONS, LEVEL_LABELS } from "../i18n/strings";
import type { AnalyzeResponse, RiskLevel } from "../types/analysis";
import { AIExplanation } from "./report/AIExplanation";
import { AudioReport } from "./report/AudioReport";
import { EvidenceList } from "./report/EvidenceList";
import { GovernmentClaimCard } from "./report/GovernmentClaimCard";
import { MissingDataNotice } from "./report/MissingDataNotice";
import { ProviderStatus } from "./report/ProviderStatus";
import { SafeNextSteps } from "./report/SafeNextSteps";

// LOW is deliberately neutral slate, not the design system's teal "safe" state.
const LEVEL_STYLE: Record<RiskLevel, { banner: string; ring: string; badge: string }> = {
  LOW: { banner: "bg-navy-soft", ring: "#475569", badge: "bg-slate-100 text-slate-800 ring-slate-300" },
  MEDIUM: { banner: "bg-amber-700", ring: "#d97706", badge: "bg-amber-50 text-amber-900 ring-amber-300" },
  HIGH: { banner: "bg-vermilion", ring: "#c2410c", badge: "bg-orange-50 text-orange-900 ring-orange-300" },
  CRITICAL: { banner: "bg-red-800", ring: "#b91c1c", badge: "bg-red-50 text-red-900 ring-red-300" },
};

function ScoreRing({ score, color, label }: { score: number; color: string; label: string }) {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  return (
    <svg viewBox="0 0 100 100" className="size-28 shrink-0" role="img" aria-label={`${label}: ${score} / 100`}>
      <circle cx="50" cy="50" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="9" />
      <circle
        cx="50"
        cy="50"
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth="9"
        strokeLinecap="round"
        strokeDasharray={`${(score / 100) * circumference} ${circumference}`}
        transform="rotate(-90 50 50)"
      />
      <text x="50" y="52" textAnchor="middle" className="fill-navy text-2xl font-bold">
        {score}
      </text>
      <text x="50" y="68" textAnchor="middle" className="fill-ink-muted text-[9px]">
        / 100
      </text>
    </svg>
  );
}

interface Props {
  result: AnalyzeResponse;
  onReset: () => void;
}

export function RiskCard({ result, onReset }: Props) {
  const { lang, t } = useLanguage();
  const { risk } = result;
  const insufficient = risk.assessment_status === "insufficient_content";
  const style = LEVEL_STYLE[risk.level];
  const ta = lang === "ta";
  const verdictScope = ta && risk.verdict_scope_ta ? risk.verdict_scope_ta : risk.verdict_scope;
  const limitations = ta && result.limitations_ta?.length ? result.limitations_ta : result.limitations;
  const senderWarnings =
    ta && result.sender_assessment.warnings_ta?.length ? result.sender_assessment.warnings_ta : result.sender_assessment.warnings;

  return (
    // overflow-wrap:anywhere lets long hostnames in explanations and findings break, so narrow screens never
    // scroll sideways (seen at 320px in Tamil); normal words still wrap at spaces.
    <div className="flex flex-col gap-5 [overflow-wrap:anywhere]" aria-live="polite">
      <div className={`flex flex-col gap-3 rounded-lg p-4 text-white sm:flex-row sm:items-center sm:p-5 ${insufficient ? "bg-slate-600" : style.banner}`}>
        <Ban className="size-8 shrink-0" aria-hidden />
        <div className="flex-1">
          <p className="text-xs font-semibold uppercase tracking-wider opacity-90">{t.recommendedAction}</p>
          <p className="text-lg font-bold">{insufficient ? t.insufficientBody : LEVEL_ACTIONS[lang][risk.level]}</p>
        </div>
        <a href="tel:1930" className="inline-flex items-center justify-center gap-2 rounded-md bg-white px-4 py-2 font-semibold text-red-800">
          <Phone className="size-4" aria-hidden /> {t.call1930}
        </a>
      </div>

      <section className="rounded-lg border border-line bg-white p-4 shadow-card sm:p-6" aria-labelledby="risk-heading">
        {insufficient ? (
          <div className="flex gap-4">
            <FileWarning className="size-10 shrink-0 text-slate-600" aria-hidden />
            <div>
              <h2 id="risk-heading" className="text-2xl font-bold text-navy">
                {t.insufficientTitle}
              </h2>
              <p className="mt-2 text-ink-muted">{t.insufficientBody}</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
            <ScoreRing score={risk.score} color={style.ring} label={t.indicatorScore} />
            <div className="flex-1">
              <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ring-1 ${style.badge}`}>
                <AlertTriangle className="size-3.5" aria-hidden /> {t.riskLevel}: {LEVEL_LABELS[lang][risk.level]}
              </span>
              <h2 id="risk-heading" className="mt-2 text-2xl font-bold text-navy sm:text-3xl" data-testid="risk-level">
                {LEVEL_LABELS[lang][risk.level]} ({risk.level})
              </h2>
              <p className="mt-1 text-sm text-ink-muted">
                {t.indicatorScore}: {risk.score}/100 — {t.notProbability}
              </p>
            </div>
          </div>
        )}
        <p className="mt-4 rounded-md bg-surface-low p-3 text-xs text-navy-soft">{verdictScope}</p>
      </section>

      {/* Keyed by report: a new analysis remounts it, and unmounting cancels any speech. */}
      <AudioReport key={result.analysis_id} result={result} />

      <div className="grid gap-5 lg:grid-cols-12">
        <div className="flex flex-col gap-5 lg:col-span-7">
          <EvidenceList evidence={result.evidence} />
          <AIExplanation explanation={result.explanation} />
          <ProviderStatus result={result} />
        </div>
        <div className="flex flex-col gap-5 lg:col-span-5">
          <SafeNextSteps en={result.safe_next_steps} ta={result.safe_next_steps_ta} />
          <GovernmentClaimCard gov={result.government_claim} />
          <MissingDataNotice codes={result.missing_metadata} />
        </div>
      </div>

      <details className="rounded-lg border border-line bg-white p-4 shadow-card sm:p-6">
        <summary className="cursor-pointer font-semibold text-navy">{t.limitationsTitle}</summary>
        <div className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <p className="font-semibold text-navy">{t.senderTitle}</p>
            <p className="text-ink-muted">{result.sender_assessment.value_masked ?? t.senderNone}</p>
            <ul className="mt-1 list-disc pl-5 text-ink-muted">
              {senderWarnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="font-semibold text-navy">{t.provenance}</p>
            <p className="text-ink-muted">
              {t.provenanceLabels[result.provenance.content_source]}
              {result.provenance.image_origin && ` · ${t.imageOrigins[result.provenance.image_origin]}`} · {t.unverifiedBadge} · {result.provenance.character_count} {t.characters}
            </p>
          </div>
          <ul className="list-disc pl-5 text-ink-muted sm:col-span-2" data-testid="limitations">
            {limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
          <p className="font-mono text-xs text-ink-muted sm:col-span-2">ID: {result.analysis_id}</p>
        </div>
      </details>

      <div className="flex flex-col gap-4 rounded-lg border-l-4 border-navy bg-surface-low p-4 sm:flex-row sm:items-center">
        <Info className="size-5 shrink-0 text-navy" aria-hidden />
        <p className="flex-1 text-sm text-navy-soft">{t.disclaimer}</p>
        <button
          type="button"
          onClick={onReset}
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-navy px-5 font-semibold text-white hover:bg-navy-deep"
        >
          <RotateCcw className="size-4" aria-hidden /> {t.checkAnother}
        </button>
      </div>
    </div>
  );
}
