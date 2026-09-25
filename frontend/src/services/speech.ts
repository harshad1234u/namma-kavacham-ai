import { LEVEL_ACTIONS, LEVEL_LABELS, STRINGS } from "../i18n/strings";
import type { AnalyzeResponse, Language } from "../types/analysis";

// Browser-native text-to-speech only. The spoken text is built from the validated report, never from
// the submitted message, and passes through redactForSpeech before any utterance is created.
export const SPEECH_LANG: Record<Language, string> = { en: "en-IN", ta: "ta-IN" };
const MAX_CHUNK_CHARS = 160; // Chrome silently stops long utterances; speak one short sentence at a time

export function speechSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window && typeof window.SpeechSynthesisUtterance === "function";
}

const voiceLang = (v: SpeechSynthesisVoice) => v.lang.replace("_", "-").toLowerCase();

// On-device voices only: "remote" voices (localService false, e.g. Chrome's Google voices) send the text
// to an online service. Prefer the Indian variant, then any voice of the language; never another language.
export function pickVoice(voices: SpeechSynthesisVoice[], lang: Language): SpeechSynthesisVoice | null {
  const local = voices.filter((v) => v.localService !== false);
  const exact = SPEECH_LANG[lang].toLowerCase();
  return local.find((v) => voiceLang(v) === exact) ?? local.find((v) => voiceLang(v).split("-")[0] === lang) ?? null;
}

const HIDDEN: Record<Language, string> = { en: "(hidden)", ta: "(மறைக்கப்பட்டது)" };
const URL_RE = /\b(?:https?:\/\/|www\.)[^\s<>"')\]]+|\b(?:[a-z0-9-]+\.)+[a-z]{2,}[/?#][^\s<>"')\]]*/gi;
const EMAIL_RE = /[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g;
const SECRET_RE = /\b(?:gsk_|sk-|AIza)[\w-]{10,}|\b[\w-]{32,}\b/g;
const PAN_RE = /\b[A-Z]{5}\d{4}[A-Z]\b/gi;
const MASKED_RE = /(?:[*•]{2,}|X{4,})\d*/g;
const LONG_NUMBER_RE = /\+?\d(?:[\s-]?\d){4,}/g; // 5+ digits: phones, Aadhaar, account and card numbers
const CODE_RE = /(OTP|PIN|CVV|code|passcode|password|கடவுச்சொல்|குறியீடு)([^\d\n]{0,20}?)\d{4,8}(?!\d)/giu;

function hostOnly(url: string): string {
  const host = url.replace(/^(?:https?:\/\/)?(?:www\.)?/i, "").split(/[/?#]/)[0];
  return host.replace(/[.,;:]+$/, "");
}

export function redactForSpeech(text: string, lang: Language): string {
  const hidden = ` ${HIDDEN[lang]} `;
  return text
    .replace(URL_RE, (url) => ` ${hostOnly(url)} `) // a site name is useful; paths and query strings are not
    .replace(EMAIL_RE, hidden)
    .replace(SECRET_RE, hidden)
    .replace(PAN_RE, hidden)
    .replace(MASKED_RE, hidden)
    .replace(LONG_NUMBER_RE, hidden)
    .replace(CODE_RE, (_m, keyword: string, gap: string) => `${keyword}${gap}${hidden}`)
    .replace(/\s+([.,;:!?])/g, "$1")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function splitSentences(text: string): string[] {
  const out: string[] = [];
  // Not after a digit, so "1. Do not click" stays one chunk.
  for (const sentence of text.split(/(?<=\D[.!?।])\s+/)) {
    let rest = sentence.trim();
    while (rest.length > MAX_CHUNK_CHARS) {
      // The cut keeps the character at `cut`, so search from MAX - 1 to stay within the limit.
      const cut = Math.max(rest.lastIndexOf(", ", MAX_CHUNK_CHARS - 1), rest.lastIndexOf(" ", MAX_CHUNK_CHARS - 1));
      const at = cut > 0 ? cut + 1 : MAX_CHUNK_CHARS;
      out.push(rest.slice(0, at).trim());
      rest = rest.slice(at).trim();
    }
    if (rest) out.push(rest);
  }
  return out;
}

export function buildSpokenReport(result: AnalyzeResponse, lang: Language): string[] {
  const t = STRINGS[lang];
  const ta = lang === "ta";
  const parts = [t.audioIntro];
  if (result.risk.assessment_status === "insufficient_content") {
    parts.push(`${t.insufficientTitle}.`, t.insufficientBody);
  } else {
    const { level, score } = result.risk;
    parts.push(`${t.riskLevel}: ${LEVEL_LABELS[lang][level]}.`, LEVEL_ACTIONS[lang][level]);
    parts.push(t.audioScore.replace("{score}", String(score)), t.notProbability);
    parts.push(ta ? result.explanation.ta : result.explanation.en);
  }
  const steps = ta && result.safe_next_steps_ta.length ? result.safe_next_steps_ta : result.safe_next_steps;
  if (steps.length) parts.push(`${t.nextStepsTitle}.`, ...steps.map((s, i) => `${i + 1}. ${s}`));
  parts.push(t.audioHelpline);
  return parts.flatMap((p) => splitSentences(redactForSpeech(p, lang)));
}
