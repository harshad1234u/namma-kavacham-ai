import { Pause, Play, RotateCcw, Square, Volume2 } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useLanguage } from "../../i18n/LanguageContext";
import { buildSpokenReport, pickVoice, speechSupported } from "../../services/speech";
import type { AnalyzeResponse, Language } from "../../types/analysis";
import { Section } from "./Section";

type Status = "idle" | "speaking" | "paused" | "finished" | "stopped" | "error";

const VOICE_WAIT_MS = 2000; // Chrome loads voices asynchronously; some browsers never fire voiceschanged
const RATES = [0.75, 1, 1.25, 1.5];
const btn = "inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-4 font-semibold disabled:cursor-not-allowed disabled:opacity-40";

function useVoices(supported: boolean) {
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>(() => (supported ? window.speechSynthesis.getVoices() : []));
  const [settled, setSettled] = useState(!supported || voices.length > 0);
  useEffect(() => {
    if (!supported) return;
    const synth = window.speechSynthesis;
    const update = () => {
      setVoices(synth.getVoices());
      setSettled(true);
    };
    synth.addEventListener?.("voiceschanged", update);
    const timer = window.setTimeout(update, VOICE_WAIT_MS);
    return () => {
      synth.removeEventListener?.("voiceschanged", update);
      window.clearTimeout(timer);
    };
  }, [supported]);
  return { voices, settled };
}

// Rendered with key={analysis_id}, so a new report remounts it and the unmount cleanup cancels speech.
export function AudioReport({ result }: { result: AnalyzeResponse }) {
  const { lang, t } = useLanguage();
  const ids = { lang: useId(), rate: useId() };
  const supported = speechSupported();
  const { voices, settled } = useVoices(supported);
  const [audioLang, setAudioLang] = useState<Language>(lang);
  const [rate, setRate] = useState(1);
  const [status, setStatus] = useState<Status>("idle");
  const voice = supported ? pickVoice(voices, audioLang) : null;
  const run = useRef(0); // bumped on every cancel; callbacks from an older run are ignored
  // Chrome never fires "end" for an utterance that was garbage-collected mid-speech, which stalls the
  // queue; holding the current one here keeps it alive until it finishes.
  const current = useRef<SpeechSynthesisUtterance | null>(null);
  const rateRef = useRef(rate);
  rateRef.current = rate;

  const cancel = useCallback(() => {
    run.current += 1;
    current.current = null;
    const synth = supported ? window.speechSynthesis : undefined;
    if (!synth) return;
    const wasPaused = synth.paused;
    synth.cancel();
    if (wasPaused) synth.resume(); // Chrome otherwise stays paused and ignores the next speak()
  }, [supported]);

  useEffect(() => setAudioLang(lang), [lang]); // follow the page language

  useEffect(() => {
    cancel();
    setStatus("idle");
  }, [audioLang, cancel]);

  useEffect(() => {
    window.addEventListener("pagehide", cancel);
    return () => {
      window.removeEventListener("pagehide", cancel);
      cancel();
    };
  }, [cancel]);

  function start() {
    if (!voice) return;
    cancel(); // never overlap with anything already queued
    const id = run.current;
    const chunks = buildSpokenReport(result, audioLang);
    const speakAt = (i: number, retried = false) => {
      if (run.current !== id) return;
      if (i >= chunks.length) {
        current.current = null;
        return setStatus("finished");
      }
      const utterance = new SpeechSynthesisUtterance(chunks[i]);
      utterance.voice = voice;
      utterance.lang = voice.lang;
      utterance.rate = rateRef.current; // a speed change applies from the next sentence
      utterance.onend = () => speakAt(i + 1);
      utterance.onerror = (event) => {
        if (run.current !== id) return; // from our own cancel(): that run is over
        // Within the current run, "interrupted" is spurious (seen on Chrome/Windows): retry the sentence
        // once, then move on, so the reader never stalls silently.
        if (event.error === "interrupted" || event.error === "canceled") return speakAt(retried ? i + 1 : i, !retried);
        cancel();
        setStatus("error");
      };
      current.current = utterance;
      window.speechSynthesis.speak(utterance);
    };
    setStatus("speaking");
    speakAt(0);
  }

  const active = status === "speaking" || status === "paused";
  const unavailable = supported && settled && !voice;

  return (
    <Section id="audio" icon={<Volume2 className="size-5" aria-hidden />} title={t.audioTitle}>
      <p className="text-sm text-ink-muted">{t.audioHelp}</p>
      {!supported ? (
        <p className="mt-3 rounded-md border-l-4 border-amber bg-amber-50 p-3 text-sm text-amber-900">{t.audioUnsupported}</p>
      ) : (
        <>
          <div className="mt-3 flex flex-wrap items-end gap-3">
            <label htmlFor={ids.lang} className="text-sm font-semibold text-navy">
              {t.audioLanguage}
              <select
                id={ids.lang}
                value={audioLang}
                onChange={(e) => setAudioLang(e.target.value as Language)}
                className="mt-1 block rounded-md border-[1.5px] border-line-strong p-2 font-normal"
              >
                {(Object.keys(t.audioLanguages) as Language[]).map((k) => (
                  <option key={k} value={k}>
                    {t.audioLanguages[k]}
                  </option>
                ))}
              </select>
            </label>
            <label htmlFor={ids.rate} className="text-sm font-semibold text-navy">
              {t.audioSpeed}
              <select
                id={ids.rate}
                value={rate}
                onChange={(e) => setRate(Number(e.target.value))}
                className="mt-1 block rounded-md border-[1.5px] border-line-strong p-2 font-normal"
              >
                {RATES.map((r) => (
                  <option key={r} value={r}>
                    {r}×
                  </option>
                ))}
              </select>
            </label>
          </div>

          {!settled && !voice && <p className="mt-3 text-sm text-ink-muted">{t.audioChecking}</p>}
          {unavailable && (
            <p role="alert" className="mt-3 rounded-md border-l-4 border-amber bg-amber-50 p-3 text-sm text-amber-900">
              {t.audioNoVoice[audioLang]}
            </p>
          )}
          {voice && <p className="mt-3 text-xs text-ink-muted">{t.audioVoice.replace("{voice}", voice.name)}</p>}

          <div className="mt-3 flex flex-wrap gap-2">
            {!active && (
              <button type="button" onClick={start} disabled={!voice} className={`${btn} bg-navy text-white hover:bg-navy-deep`}>
                <Play className="size-4" aria-hidden /> {t.audioListen}
              </button>
            )}
            {status === "speaking" && (
              <button
                type="button"
                onClick={() => {
                  window.speechSynthesis.pause();
                  setStatus("paused");
                }}
                className={`${btn} bg-navy text-white hover:bg-navy-deep`}
              >
                <Pause className="size-4" aria-hidden /> {t.audioPause}
              </button>
            )}
            {status === "paused" && (
              <button
                type="button"
                onClick={() => {
                  window.speechSynthesis.resume();
                  setStatus("speaking");
                }}
                className={`${btn} bg-navy text-white hover:bg-navy-deep`}
              >
                <Play className="size-4" aria-hidden /> {t.audioResume}
              </button>
            )}
            {active && (
              <button
                type="button"
                onClick={() => {
                  cancel();
                  setStatus("stopped");
                }}
                className={`${btn} bg-surface-high text-navy hover:bg-surface`}
              >
                <Square className="size-4" aria-hidden /> {t.audioStop}
              </button>
            )}
            {status !== "idle" && (
              <button type="button" onClick={start} disabled={!voice} className={`${btn} bg-surface-high text-navy hover:bg-surface`}>
                <RotateCcw className="size-4" aria-hidden /> {t.audioRestart}
              </button>
            )}
          </div>
          <p role="status" aria-live="polite" className={`mt-2 text-sm ${status === "error" ? "font-semibold text-red-800" : "text-navy"}`}>
            {t.audioStatus[status]}
          </p>
        </>
      )}
    </Section>
  );
}
