import { BarChart3, CheckCircle2, MapPin, Search, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { card } from "../components/civic/ui";
import { fill, useCivic } from "../i18n/civic";
import { useLanguage } from "../i18n/LanguageContext";
import { getJson, query } from "../services/civicApi";
import type { SchemeSummary } from "../types/civic";

export function Home() {
  const { c } = useCivic();
  const { code } = useLanguage();
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    getJson<SchemeSummary[]>(`/v1/schemes${query({ lang: code })}`)
      .then((s) => setCount(s.length))
      .catch(() => setCount(null));
  }, [code]);

  const cards = [
    { to: "/schemes", title: c.cardAskTitle, body: c.cardAskBody, Icon: Search },
    { to: "/schemes/discover", title: c.cardDiscoverTitle, body: c.cardDiscoverBody, Icon: Sparkles },
    { to: "/dev/report", title: c.cardReportTitle, body: c.cardReportBody, Icon: MapPin },
    { to: "/dev", title: c.cardDashTitle, body: c.cardDashBody, Icon: BarChart3 },
  ];

  return (
    <div className="space-y-10">
      <section className="rounded-2xl bg-navy px-6 py-10 text-white sm:px-10">
        <h1 className="max-w-3xl text-3xl font-bold leading-tight sm:text-4xl">{c.heroTitle}</h1>
        <p className="mt-4 max-w-2xl text-white/85">{c.heroBody}</p>
        {count !== null && (
          <p className="mt-6 inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-sm font-semibold">
            <CheckCircle2 className="size-4" aria-hidden /> {fill(c.schemesCount, { n: count })}
          </p>
        )}
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        {cards.map(({ to, title, body, Icon }) => (
          <Link key={to} to={to} className={`${card} group transition hover:shadow-raised`}>
            <Icon className="size-7 text-teal-deep" aria-hidden />
            <h2 className="mt-3 text-lg font-bold text-navy group-hover:underline">{title}</h2>
            <p className="mt-1 text-ink-muted">{body}</p>
          </Link>
        ))}
      </section>

      <section className={card}>
        <h2 className="text-lg font-bold text-navy">{c.principleTitle}</h2>
        <ul className="mt-3 space-y-2">
          {[c.principle1, c.principle2, c.principle3].map((p) => (
            <li key={p} className="flex gap-2">
              <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-teal-deep" aria-hidden /> {p}
            </li>
          ))}
        </ul>
      </section>

      <Link to="/safety" className={`${card} flex items-start gap-3 hover:shadow-raised`}>
        <ShieldCheck className="size-7 shrink-0 text-vermilion" aria-hidden />
        <span>
          <span className="block font-bold text-navy">{c.cardSafetyTitle}</span>
          <span className="text-ink-muted">{c.cardSafetyBody}</span>
        </span>
      </Link>
    </div>
  );
}
