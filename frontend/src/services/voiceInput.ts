// Browser speech-to-text (Web Speech API). Opt-in only: in Chrome/Edge the audio is processed by the
// browser vendor's online speech service, so the UI asks first and always keeps typing available.

export type VoiceErrorKind = "unsupported" | "denied" | "no_speech" | "network" | "failed";

export class VoiceError extends Error {
  constructor(public readonly kind: VoiceErrorKind) {
    super(kind);
    this.name = "VoiceError";
  }
}

interface RecognitionLike {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}
type RecognitionCtor = new () => RecognitionLike;

function ctor(): RecognitionCtor | null {
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function voiceSupported(): boolean {
  return ctor() !== null;
}

/** BCP-47 tag for an Indian-language code, e.g. "ta" -> "ta-IN". */
export function speechLang(code: string): string {
  return `${code}-IN`;
}

/** Listen once; resolves with the transcript. Call the returned `stop` to end early. */
export function listen(code: string): { result: Promise<string>; stop: () => void } {
  const Ctor = ctor();
  if (!Ctor) return { result: Promise.reject(new VoiceError("unsupported")), stop: () => {} };
  const rec = new Ctor();
  rec.lang = speechLang(code);
  rec.interimResults = false;
  rec.continuous = false;
  const result = new Promise<string>((resolve, reject) => {
    let text = "";
    rec.onresult = (e) => {
      text = Array.from(e.results).map((r) => r[0]?.transcript ?? "").join(" ").trim();
    };
    rec.onerror = (e) => {
      const kind: VoiceErrorKind =
        e.error === "not-allowed" || e.error === "service-not-allowed" ? "denied"
        : e.error === "no-speech" ? "no_speech"
        : e.error === "network" ? "network"
        : "failed";
      reject(new VoiceError(kind));
    };
    rec.onend = () => (text ? resolve(text) : reject(new VoiceError("no_speech")));
  });
  rec.start();
  return { result, stop: () => rec.stop() };
}
