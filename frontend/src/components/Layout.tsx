import { Info, Phone, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { useLanguage } from "../i18n/LanguageContext";
import { LanguageToggle } from "./LanguageToggle";

export function Layout({ children }: { children: ReactNode }) {
  const { t } = useLanguage();
  const navClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-2 text-sm font-semibold transition ${
      isActive ? "bg-surface-high text-navy" : "text-ink-muted hover:text-navy"
    }`;

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2">
        Skip to content
      </a>
      {/* Sticky only from sm up: on phones the stacked header would cover a third of the screen. */}
      <header className="z-40 border-b border-line bg-white/95 backdrop-blur sm:sticky sm:top-0">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3 sm:px-8">
          <Link to="/" className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-lg bg-navy text-white">
              <ShieldCheck className="size-6" aria-hidden />
            </span>
            <span className="leading-tight">
              <span className="block text-lg font-bold text-navy">{t.appName}</span>
              <span className="block text-xs font-semibold text-teal-deep">{t.appSubtitle}</span>
            </span>
          </Link>
          <nav aria-label="Primary" className="order-3 flex w-full gap-1 sm:order-none sm:ml-6 sm:w-auto">
            <NavLink to="/analyze" className={navClass}>
              {t.navCheck}
            </NavLink>
            <NavLink to="/" end className={navClass}>
              {t.navHow}
            </NavLink>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <span className="hidden rounded-full bg-surface px-3 py-1 text-xs font-semibold text-navy-soft md:inline">{t.mvpBadge}</span>
            <LanguageToggle />
            <a
              href="tel:1930"
              className="hidden items-center gap-2 rounded-md bg-vermilion px-4 py-2 text-sm font-semibold text-white hover:bg-vermilion/90 sm:inline-flex"
            >
              <Phone className="size-4" aria-hidden /> {t.helpline}
            </a>
          </div>
        </div>
        <p className="flex items-center justify-center gap-2 border-t border-line bg-surface-low px-4 py-1.5 text-center text-xs font-medium text-navy-soft">
          <Info className="size-3.5 shrink-0" aria-hidden /> {t.infoStrip}
        </p>
      </header>

      <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-8 sm:py-10">
        {children}
      </main>

      <footer className="border-t border-line bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <p className="max-w-3xl text-sm text-ink-muted">{t.footerText}</p>
          <a
            href="tel:1930"
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-md bg-vermilion px-4 py-2.5 text-sm font-semibold text-white hover:bg-vermilion/90"
          >
            <Phone className="size-4" aria-hidden /> {t.emergencyHelpline}
          </a>
        </div>
        <p className="mx-auto max-w-7xl px-4 pb-6 text-xs text-ink-muted sm:px-8">
          National Cyber Crime Reporting Portal: cybercrime.gov.in · Helpline 1930
        </p>
      </footer>
    </div>
  );
}
