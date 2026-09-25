import { MessageSquareText, Sparkles } from "lucide-react";
import { useLanguage } from "../../i18n/LanguageContext";
import type { AnalyzeResponse } from "../../types/analysis";
import { Section } from "./Section";

export function AIExplanation({ explanation }: { explanation: AnalyzeResponse["explanation"] }) {
  const { lang, t } = useLanguage();
  const status = explanation.ai_status ?? (explanation.generated_by !== "template" ? "generated" : "disabled");
  const generated = status === "generated";
  const text = lang === "ta" ? explanation.ta : explanation.en;
  const note = lang === "ta" && explanation.note_ta ? explanation.note_ta : explanation.note;

  return (
    <Section id="explanation" icon={<MessageSquareText className="size-5" aria-hidden />} title={t.explanationTitle}>
      <p
        data-testid="ai-status"
        data-status={status}
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
          generated ? "bg-surface-high text-navy" : status === "disabled" ? "bg-surface text-ink-muted" : "bg-amber-50 text-amber-900 ring-1 ring-amber-200"
        }`}
      >
        <Sparkles className="size-3.5" aria-hidden />
        {generated ? t.aiGenerated : `${t.aiStates[status]} — ${t.aiFallback}`}
      </p>
      <p lang={lang} className="mt-3 text-ink">
        {text}
      </p>
      <p className="mt-2 text-xs text-ink-muted">{generated ? t.aiNotOfficial : note}</p>
    </Section>
  );
}
