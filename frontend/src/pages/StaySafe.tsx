import { ArrowRight, CheckCircle2, Info, Lock, ShieldCheck, Smartphone, XCircle, Zap } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { SAMPLES, type Sample } from "../data/samples";
import { useLanguage } from "../i18n/LanguageContext";

const CHECKS = {
  en: [
    ["Urgency & coercion", "Detects pressure such as “disconnected tonight”, “account blocked”, or “arrest warrant”."],
    ["Deceptive links", "Spots lookalike domains pretending to be .gov.in, disguised app downloads, and hidden destinations."],
    ["OTP, PIN & payment demands", "Flags requests to share codes, pay “processing fees”, or send money to UPI IDs."],
    ["Link reputation", "Looks up existing VirusTotal reports for the link only — never your message."],
  ],
  ta: [
    ["அவசரம் & அச்சுறுத்தல்", "“இன்று இரவு துண்டிக்கப்படும்”, “கணக்கு முடக்கப்பட்டது” போன்ற அழுத்தத்தைக் கண்டறிகிறது."],
    ["ஏமாற்று இணைப்புகள்", ".gov.in போலத் தோன்றும் போலி டொமைன்கள், மறைக்கப்பட்ட செயலி பதிவிறக்கங்களைக் கண்டறிகிறது."],
    ["OTP, PIN & கட்டணக் கோரிக்கைகள்", "குறியீடுகளைப் பகிர, “செயலாக்கக் கட்டணம்” செலுத்த அல்லது UPI-க்குப் பணம் அனுப்பக் கோருவதைக் குறிக்கிறது."],
    ["இணைப்பு நம்பகத்தன்மை", "இணைப்புக்கான VirusTotal அறிக்கைகளைத் தேடுகிறது — உங்கள் செய்தியை அல்ல."],
  ],
} as const;

const BOUNDARIES = {
  en: [
    ["No SMS inbox access", "We never ask for SMS, notification, or accessibility permissions. You choose what to submit."],
    ["No sender certification", "Caller IDs and SMS headers can be spoofed. We assess the message, never who sent it."],
    ["No live government search", "Government claims are compared only with a small curated reference set, not live records."],
    ["No guarantees", "Missing or unavailable checks are shown as “not checked” — never as safe."],
  ],
  ta: [
    ["SMS அணுகல் இல்லை", "SMS, அறிவிப்பு அல்லது அணுகல் அனுமதிகளை நாங்கள் கேட்பதில்லை. எதைச் சமர்ப்பிப்பது என்பது உங்கள் முடிவு."],
    ["அனுப்புநர் சான்றளிப்பு இல்லை", "அழைப்பாளர் ஐடி, SMS தலைப்புகள் போலியாக்கப்படலாம். செய்தியை மதிப்பிடுகிறோம், அனுப்பியவரை அல்ல."],
    ["நேரடி அரசுத் தேடல் இல்லை", "அரசுக் கூற்றுகள் சிறிய தொகுக்கப்பட்ட குறிப்புடன் மட்டுமே ஒப்பிடப்படுகின்றன."],
    ["உத்தரவாதம் இல்லை", "விடுபட்ட அல்லது கிடைக்காத சோதனைகள் “சரிபார்க்கப்படவில்லை” என்றே காட்டப்படும் — பாதுகாப்பானது என அல்ல."],
  ],
} as const;

const TONE: Record<Sample["tone"], string> = {
  critical: "bg-red-50 text-red-800",
  caution: "bg-amber-50 text-amber-800",
  advisory: "bg-teal/15 text-teal-deep",
};

export function StaySafe() {
  const { lang, t } = useLanguage();
  const navigate = useNavigate();

  return (
    <div className="flex flex-col gap-10">
      <section className="relative overflow-hidden rounded-xl border border-line bg-white p-6 shadow-card sm:p-10">
        <div className="flex flex-wrap gap-2">
          {[
            [t.chipDeterministic, <ShieldCheck key="a" className="size-3.5" aria-hidden />],
            [t.chipNoSms, <Smartphone key="b" className="size-3.5" aria-hidden />],
            [t.chipPrivate, <Lock key="c" className="size-3.5" aria-hidden />],
          ].map(([label, icon]) => (
            <span key={String(label)} className="inline-flex items-center gap-1.5 rounded-full bg-surface px-3 py-1 text-xs font-semibold text-navy-soft">
              {icon} {label}
            </span>
          ))}
        </div>
        <h1 className="mt-5 text-3xl font-bold tracking-tight text-navy sm:text-4xl">{t.heroTitle}</h1>
        <p className="mt-2 text-xl font-semibold text-teal-deep sm:text-2xl" lang={lang === "en" ? "ta" : "en"}>
          {t.heroTitleAlt}
        </p>
        <p className="mt-4 max-w-3xl text-lg text-ink-muted">{t.heroBody}</p>
        <p className="mt-5 flex max-w-3xl gap-2 rounded-md bg-surface-low p-3 text-sm text-navy-soft">
          <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>
            <strong className="text-navy">{t.advisoryTitle}</strong> {t.advisoryBody}
          </span>
        </p>
        <Link
          to="/analyze"
          className="mt-6 inline-flex min-h-12 items-center gap-2 rounded-md bg-navy px-6 font-semibold text-white hover:bg-navy-deep"
        >
          {t.startCheck} <ArrowRight className="size-4" aria-hidden />
        </Link>
      </section>

      <section aria-labelledby="samples">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="samples" className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-navy">
            <Zap className="size-4" aria-hidden /> {t.samplesTitle}
          </h2>
          <p className="text-xs text-ink-muted">{t.samplesHint}</p>
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {SAMPLES.map((sample) => (
            <button
              key={sample.id}
              type="button"
              onClick={() => navigate("/analyze", { state: { sampleId: sample.id } })}
              className="rounded-lg border border-line bg-white p-4 text-left shadow-card transition hover:border-line-strong hover:shadow-raised"
            >
              <span className={`rounded px-2 py-0.5 text-xs font-semibold ${TONE[sample.tone]}`}>{sample.tag[lang]}</span>
              <p className="mt-2 font-semibold text-navy">{sample.title[lang]}</p>
              <p className="mt-1 line-clamp-2 text-xs text-ink-muted">“{sample.body}”</p>
            </button>
          ))}
        </div>
      </section>

      <section aria-labelledby="transparency" className="grid gap-5 lg:grid-cols-2">
        <h2 id="transparency" className="sr-only">
          {t.whatWeCheck} / {t.boundaries}
        </h2>
        <div className="rounded-lg border border-line bg-white p-6 shadow-card">
          <h3 className="text-xl font-semibold text-navy">{t.whatWeCheck}</h3>
          <p className="text-sm font-semibold text-teal-deep">{t.whatWeCheckSub}</p>
          <ul className="mt-4 flex flex-col gap-3">
            {CHECKS[lang].map(([title, body]) => (
              <li key={title} className="flex gap-3 rounded-md bg-surface-low p-3 text-sm">
                <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-teal-deep" aria-hidden />
                <span>
                  <strong className="text-navy">{title}:</strong> {body}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-lg border border-line bg-white p-6 shadow-card">
          <h3 className="text-xl font-semibold text-navy">{t.boundaries}</h3>
          <p className="text-sm font-semibold text-ink-muted">{t.boundariesSub}</p>
          <ul className="mt-4 flex flex-col gap-3">
            {BOUNDARIES[lang].map(([title, body]) => (
              <li key={title} className="flex gap-3 rounded-md bg-surface-low p-3 text-sm">
                <XCircle className="mt-0.5 size-5 shrink-0 text-ink-muted" aria-hidden />
                <span>
                  <strong className="text-navy">{title}:</strong> {body}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <p className="flex gap-3 rounded-lg border border-line-strong bg-surface-low p-4 text-sm text-navy-soft">
        <Info className="mt-0.5 size-5 shrink-0 text-navy" aria-hidden /> {t.disclaimer}
      </p>
    </div>
  );
}
