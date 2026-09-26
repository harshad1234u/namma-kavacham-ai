// The 22 Scheduled Languages + English, for the language picker. Mirrors backend
// app/data/civic/languages.json (the full support matrix is served by /v1/meta/languages).
export interface Lang {
  code: string;
  name: string;
  native: string;
  dir: "ltr" | "rtl";
}

export const LANGS: Lang[] = [
  { code: "en", name: "English", native: "English", dir: "ltr" },
  { code: "as", name: "Assamese", native: "অসমীয়া", dir: "ltr" },
  { code: "bn", name: "Bengali", native: "বাংলা", dir: "ltr" },
  { code: "brx", name: "Bodo", native: "बड़ो", dir: "ltr" },
  { code: "doi", name: "Dogri", native: "डोगरी", dir: "ltr" },
  { code: "gu", name: "Gujarati", native: "ગુજરાતી", dir: "ltr" },
  { code: "hi", name: "Hindi", native: "हिन्दी", dir: "ltr" },
  { code: "kn", name: "Kannada", native: "ಕನ್ನಡ", dir: "ltr" },
  { code: "ks", name: "Kashmiri", native: "کٲشُر", dir: "rtl" },
  { code: "kok", name: "Konkani", native: "कोंकणी", dir: "ltr" },
  { code: "mai", name: "Maithili", native: "मैथिली", dir: "ltr" },
  { code: "ml", name: "Malayalam", native: "മലയാളം", dir: "ltr" },
  { code: "mni", name: "Manipuri (Meitei)", native: "ꯃꯤꯇꯩꯂꯣꯟ", dir: "ltr" },
  { code: "mr", name: "Marathi", native: "मराठी", dir: "ltr" },
  { code: "ne", name: "Nepali", native: "नेपाली", dir: "ltr" },
  { code: "or", name: "Odia", native: "ଓଡ଼ିଆ", dir: "ltr" },
  { code: "pa", name: "Punjabi", native: "ਪੰਜਾਬੀ", dir: "ltr" },
  { code: "sa", name: "Sanskrit", native: "संस्कृतम्", dir: "ltr" },
  { code: "sat", name: "Santali", native: "ᱥᱟᱱᱛᱟᱲᱤ", dir: "ltr" },
  { code: "sd", name: "Sindhi", native: "سنڌي", dir: "rtl" },
  { code: "ta", name: "Tamil", native: "தமிழ்", dir: "ltr" },
  { code: "te", name: "Telugu", native: "తెలుగు", dir: "ltr" },
  { code: "ur", name: "Urdu", native: "اردو", dir: "rtl" },
];

export const LANG_CODES = new Set(LANGS.map((l) => l.code));
export const langInfo = (code: string): Lang => LANGS.find((l) => l.code === code) ?? LANGS[0];
