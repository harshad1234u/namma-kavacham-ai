import { useLanguage } from "../../i18n/LanguageContext";

export function SafeNextSteps({ en, ta }: { en: string[]; ta: string[] }) {
  const { lang, t } = useLanguage();
  const steps = lang === "ta" && ta.length ? ta : en;
  return (
    <section aria-labelledby="steps" className="rounded-lg bg-navy p-4 text-white sm:p-6">
      <h3 id="steps" className="text-lg font-semibold">
        {t.nextStepsTitle}
      </h3>
      <ol className="mt-4 flex flex-col gap-3">
        {steps.map((step, i) => (
          <li key={i} className="flex gap-3 rounded-md bg-white/10 p-3 text-sm">
            <span className="font-mono text-lg font-bold text-teal-300">{String(i + 1).padStart(2, "0")}</span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
