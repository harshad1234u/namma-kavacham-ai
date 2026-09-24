import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Language } from "../types/analysis";
import { STRINGS, type Strings } from "./strings";

const STORAGE_KEY = "nk-language";

interface LanguageState {
  lang: Language;
  setLang: (lang: Language) => void;
  t: Strings;
}

const LanguageContext = createContext<LanguageState | null>(null);

function initialLanguage(): Language {
  try {
    return localStorage.getItem(STORAGE_KEY) === "ta" ? "ta" : "en";
  } catch {
    return "en";
  }
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Language>(initialLanguage);

  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      /* storage unavailable (private mode) — language still works for this session */
    }
  }, [lang]);

  const value = useMemo(() => ({ lang, setLang, t: STRINGS[lang] }), [lang]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageState {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used inside LanguageProvider");
  return ctx;
}
