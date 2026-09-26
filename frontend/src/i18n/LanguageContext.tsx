import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Language } from "../types/analysis";
import { LANG_CODES, langInfo } from "./languages";
import { STRINGS, type Strings } from "./strings";

const STORAGE_KEY = "nk-language";

interface LanguageState {
  /** Any of the 22 Scheduled Languages or English. */
  code: string;
  setCode: (code: string) => void;
  dir: "ltr" | "rtl";
  /** Legacy two-language view used by the Stay Safe checker ("ta" only when Tamil is chosen). */
  lang: Language;
  setLang: (lang: Language) => void;
  t: Strings;
}

const LanguageContext = createContext<LanguageState | null>(null);

function initialCode(): string {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored && LANG_CODES.has(stored) ? stored : "en";
  } catch {
    return "en";
  }
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [code, setCode] = useState<string>(initialCode);
  const dir = langInfo(code).dir;

  useEffect(() => {
    document.documentElement.lang = code;
    document.documentElement.dir = dir;
    try {
      localStorage.setItem(STORAGE_KEY, code);
    } catch {
      /* storage unavailable (private mode) — language still works for this session */
    }
  }, [code, dir]);

  const value = useMemo(() => {
    const lang: Language = code === "ta" ? "ta" : "en";
    return { code, setCode, dir, lang, setLang: (l: Language) => setCode(l), t: STRINGS[lang] };
  }, [code, dir]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageState {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used inside LanguageProvider");
  return ctx;
}
