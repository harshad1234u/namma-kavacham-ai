import { Languages } from "lucide-react";
import { useId } from "react";
import { useCivic } from "../../i18n/civic";
import { useLanguage } from "../../i18n/LanguageContext";
import { LANGS } from "../../i18n/languages";

export function LanguagePicker() {
  const { code, setCode } = useLanguage();
  const { c } = useCivic();
  const id = useId();
  return (
    <div className="flex items-center gap-2">
      <Languages className="size-5 text-navy-soft" aria-hidden />
      <label htmlFor={id} className="sr-only">
        {c.languageLabel} / Language
      </label>
      <select
        id={id}
        value={code}
        onChange={(e) => setCode(e.target.value)}
        className="min-h-10 max-w-[11rem] rounded-md border border-line-strong bg-white px-2 text-sm font-semibold text-navy"
      >
        {LANGS.map((l) => (
          <option key={l.code} value={l.code} lang={l.code}>
            {l.native}
            {l.code !== "en" ? ` · ${l.name}` : ""}
          </option>
        ))}
      </select>
    </div>
  );
}
