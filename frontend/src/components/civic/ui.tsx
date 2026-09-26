import { AlertTriangle, BadgeCheck, CircleHelp, ExternalLink, Info, Loader2, ShieldAlert, XCircle } from "lucide-react";
import type { ReactNode } from "react";
import { useCivic } from "../../i18n/civic";
import type { Explanation, LocText, PriorityLevel, Provenance, VerifyStatus } from "../../types/civic";

export const card = "rounded-lg border border-line bg-white p-4 shadow-card sm:p-6";
export const btnPrimary =
  "inline-flex min-h-12 items-center justify-center gap-2 rounded-md bg-navy-deep px-6 font-semibold text-white hover:bg-navy disabled:opacity-40";
export const btnSecondary =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-md border border-line-strong bg-white px-4 font-semibold text-navy hover:bg-surface-low";
export const input =
  "w-full rounded-md border-[1.5px] border-line-strong bg-surface-low p-3 focus:border-navy focus:outline-none focus:ring-2 focus:ring-teal/30";
export const label = "text-sm font-semibold text-navy";

export function PageTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="mb-6">
      <h1 className="text-2xl font-bold text-navy sm:text-3xl">{title}</h1>
      {subtitle && <p className="mt-2 max-w-3xl text-ink-muted">{subtitle}</p>}
    </header>
  );
}

export function Loading({ text }: { text?: string }) {
  const { c } = useCivic();
  return (
    <p role="status" aria-live="polite" className="flex items-center gap-2 py-6 text-navy-soft">
      <Loader2 className="size-5 animate-spin" aria-hidden /> {text ?? c.loading}
    </p>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { c } = useCivic();
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-900">
      <p className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden /> {message}
      </p>
      {onRetry && (
        <button type="button" onClick={onRetry} className={`${btnSecondary} mt-3`}>
          {c.retry}
        </button>
      )}
    </div>
  );
}

const STATUS_STYLE: Record<VerifyStatus, { cls: string; Icon: typeof BadgeCheck }> = {
  supported: { cls: "bg-teal/15 text-teal-deep ring-teal/30", Icon: BadgeCheck },
  partially_supported: { cls: "bg-amber-50 text-amber-800 ring-amber-200", Icon: Info },
  contradicted: { cls: "bg-red-50 text-red-800 ring-red-200", Icon: XCircle },
  not_found: { cls: "bg-surface text-navy-soft ring-line-strong", Icon: CircleHelp },
  unable_to_verify: { cls: "bg-surface text-navy-soft ring-line-strong", Icon: CircleHelp },
};

export function VerificationBadge({ status }: { status: VerifyStatus }) {
  const { c } = useCivic();
  const { cls, Icon } = STATUS_STYLE[status];
  return (
    <span data-testid="verify-status" className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-base font-bold ring-1 ${cls}`}>
      <Icon className="size-5" aria-hidden /> {c[`status_${status}`]}
    </span>
  );
}

const LEVEL_STYLE: Record<PriorityLevel, string> = {
  critical: "bg-red-600 text-white",
  high: "bg-orange-500 text-white",
  medium: "bg-yellow-300 text-navy-deep",
  lower: "bg-surface text-navy",
  unable_to_assess: "bg-white text-navy-soft ring-1 ring-line-strong",
};
export const LEVEL_COLOR: Record<PriorityLevel, string> = {
  critical: "#dc2626",
  high: "#f97316",
  medium: "#eab308",
  lower: "#64748b",
  unable_to_assess: "#94a3b8",
};

export function LevelBadge({ level, score }: { level: PriorityLevel; score?: number | null }) {
  const { c } = useCivic();
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-bold ${LEVEL_STYLE[level]}`}>
      {c[`level_${level}`]}
      {score !== null && score !== undefined && <span aria-label="score">· {score}/100</span>}
    </span>
  );
}

/** A link we show as an official channel: only https .gov.in / .nic.in URLs get the badge. */
export function OfficialLink({ href, children }: { href: string; children: ReactNode }) {
  const { c } = useCivic();
  let official = false;
  try {
    const u = new URL(href);
    official = u.protocol === "https:" && /\.(gov|nic)\.in$/.test(u.hostname);
  } catch {
    official = false;
  }
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex flex-wrap items-center gap-2 font-semibold text-teal-deep underline break-all">
      {official && (
        <span className="inline-flex items-center gap-1 rounded-full bg-teal/15 px-2 py-0.5 text-xs font-bold text-teal-deep no-underline">
          <BadgeCheck className="size-3.5" aria-hidden /> {c.official}
        </span>
      )}
      {children} <ExternalLink className="size-4 shrink-0" aria-hidden />
    </a>
  );
}

export function ProvenanceBadge({ source }: { source: Provenance }) {
  const { c } = useCivic();
  const demo = source.type === "demo";
  return (
    <span
      title={`${source.name} · ${source.last_updated}`}
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
        demo ? "bg-amber-50 text-amber-800 ring-amber-200" : "bg-teal/15 text-teal-deep ring-teal/30"
      }`}
    >
      {demo ? <ShieldAlert className="size-3.5" aria-hidden /> : <BadgeCheck className="size-3.5" aria-hidden />}
      {demo ? c.demoData : c.officialData}
    </span>
  );
}

/** Text from the API in the requested language, or English with a visible label. */
export function Loc({ t }: { t: LocText }) {
  const { c } = useCivic();
  return (
    <>
      <span lang={t.lang}>{t.text}</span>
      {t.status !== "authored" && (
        <span className="ml-2 rounded bg-surface px-1.5 py-0.5 text-xs text-navy-soft">
          {t.status === "machine_translated" ? c.expl_machine_translated : "EN"}
        </span>
      )}
    </>
  );
}

export function ExplanationBlock({ e }: { e: Explanation }) {
  const { c } = useCivic();
  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-navy-soft">{c[`expl_${e.status}`]}</p>
      <p lang={e.lang} className="leading-relaxed">
        {e.text}
      </p>
    </div>
  );
}

/** Horizontal bars; values are shown as numbers too, so colour is never the only signal. */
export function Bars({ rows, color = "#0d9488" }: { rows: [string, number][]; color?: string }) {
  const max = Math.max(1, ...rows.map(([, v]) => v));
  return (
    <ul className="space-y-2">
      {rows.map(([k, v]) => (
        <li key={k} className="grid grid-cols-[minmax(0,9rem)_1fr_3rem] items-center gap-2 text-sm">
          <span className="truncate" title={k}>
            {k}
          </span>
          <span className="h-3 rounded bg-surface" aria-hidden>
            <span className="block h-3 rounded" style={{ width: `${(v / max) * 100}%`, background: color }} />
          </span>
          <span className="text-right font-semibold tabular-nums">{v}</span>
        </li>
      ))}
    </ul>
  );
}

export function Stat({ label: l, value }: { label: string; value: number | string }) {
  return (
    <div className={card}>
      <p className="text-sm text-ink-muted">{l}</p>
      <p className="mt-1 text-3xl font-bold tabular-nums text-navy">{value}</p>
    </div>
  );
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toISOString().slice(0, 10);
}
