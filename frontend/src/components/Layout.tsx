import { Info, Landmark, Phone } from "lucide-react";
import type { ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { fill, useCivic } from "../i18n/civic";
import { useLanguage } from "../i18n/LanguageContext";
import { LanguagePicker } from "./civic/LanguagePicker";

const SAFETY_PATHS = ["/safety", "/analyze"];

export function Layout({ children }: { children: ReactNode }) {
  const { t } = useLanguage();
  const { c, fallback, langName } = useCivic();
  const { pathname } = useLocation();
  const safety = SAFETY_PATHS.some((p) => pathname.startsWith(p));
  const navClass = ({ isActive }: { isActive: boolean }) =>
    `whitespace-nowrap rounded-md px-3 py-2 text-sm font-semibold transition ${
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
              <Landmark className="size-6" aria-hidden />
            </span>
            <span className="leading-tight">
              <span className="block text-lg font-bold text-navy">{c.appName}</span>
              <span className="hidden text-xs font-semibold text-teal-deep sm:block">{c.tagline}</span>
            </span>
          </Link>
          <div className="ml-auto flex items-center gap-2">
            <LanguagePicker />
          </div>
          <nav aria-label="Primary" className="order-3 -mx-1 flex w-full flex-wrap gap-1">
            <NavLink to="/schemes" end className={navClass}>
              {c.navAsk}
            </NavLink>
            <NavLink to="/schemes/discover" className={navClass}>
              {c.navDiscover}
            </NavLink>
            <NavLink to="/dev" end className={navClass}>
              {c.navDev}
            </NavLink>
            <NavLink to="/dev/report" className={navClass}>
              {c.navReport}
            </NavLink>
            <NavLink to="/safety" className={({ isActive }) => navClass({ isActive: isActive || safety })}>
              {c.navSafety}
            </NavLink>
            <NavLink to="/languages" className={navClass}>
              {c.navLanguages}
            </NavLink>
          </nav>
        </div>
        <p className="flex items-center justify-center gap-2 border-t border-line bg-surface-low px-4 py-1.5 text-center text-xs font-medium text-navy-soft">
          <Info className="size-3.5 shrink-0" aria-hidden /> {safety ? t.infoStrip : c.infoStrip}
        </p>
        {fallback && (
          <p role="note" className="border-t border-amber-200 bg-amber-50 px-4 py-1.5 text-center text-xs font-medium text-amber-900">
            {fill(c.uiFallbackNotice, { lang: langName })}
          </p>
        )}
      </header>

      <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-8 sm:py-10">
        {children}
      </main>

      <footer className="border-t border-line bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <p className="max-w-3xl text-sm text-ink-muted">{safety ? t.footerText : c.footerText}</p>
          <a
            href="tel:1930"
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-md bg-vermilion px-4 py-2.5 text-sm font-semibold text-white hover:bg-vermilion/90"
          >
            <Phone className="size-4" aria-hidden /> {safety ? t.emergencyHelpline : "1930"}
          </a>
        </div>
        <p className="mx-auto max-w-7xl px-4 pb-6 text-xs text-ink-muted sm:px-8">{c.footerSafety}</p>
      </footer>
    </div>
  );
}
