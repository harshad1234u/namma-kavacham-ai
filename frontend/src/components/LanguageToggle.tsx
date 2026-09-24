import { useLanguage } from "../i18n/LanguageContext";
import type { Language } from "../types/analysis";

const OPTIONS: { value: Language; label: string }[] = [
  { value: "en", label: "English" },
  { value: "ta", label: "தமிழ்" },
];

export function LanguageToggle() {
  const { lang, setLang } = useLanguage();
  return (
    <div role="group" aria-label="Language / மொழி" className="inline-flex rounded-full border border-line bg-canvas p-1">
      {OPTIONS.map((opt) => {
        const active = lang === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            lang={opt.value}
            aria-pressed={active}
            onClick={() => setLang(opt.value)}
            className={`min-h-9 rounded-full px-4 text-sm transition ${
              active ? "bg-white font-semibold text-navy shadow-card" : "text-ink-muted hover:text-navy"
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
