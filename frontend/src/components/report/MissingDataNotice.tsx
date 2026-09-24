import { CircleHelp, Eye } from "lucide-react";
import { useLanguage } from "../../i18n/LanguageContext";
import { MISSING_LABELS } from "../../i18n/strings";
import { Section } from "./Section";

export function MissingDataNotice({ codes }: { codes: string[] }) {
  const { lang, t } = useLanguage();
  if (codes.length === 0) return null;
  return (
    <Section id="missing" icon={<Eye className="size-5" aria-hidden />} title={t.missingTitle}>
      <ul className="flex flex-col gap-2" data-testid="missing-data">
        {codes.map((code) => (
          <li key={code} className="flex gap-2 text-sm text-ink">
            <CircleHelp className="mt-0.5 size-4 shrink-0 text-amber-700" aria-hidden />
            {MISSING_LABELS[lang][code] ?? code}
          </li>
        ))}
      </ul>
    </Section>
  );
}
