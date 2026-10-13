/** The four supported languages, each shown in its own script. */
export type Lang = "en" | "kn" | "hi" | "te";

export const LANGUAGES: { code: Lang; name: string }[] = [
  { code: "en", name: "English" },
  { code: "kn", name: "ಕನ್ನಡ" },
  { code: "hi", name: "हिन्दी" },
  { code: "te", name: "తెలుగు" },
];

export const LANG_CODES: Lang[] = LANGUAGES.map((l) => l.code);

export function isLang(v: unknown): v is Lang {
  return typeof v === "string" && (LANG_CODES as string[]).includes(v);
}

export function asLang(v: unknown): Lang {
  return isLang(v) ? v : "en";
}

export function languageName(code: string): string {
  return LANGUAGES.find((l) => l.code === code)?.name ?? code;
}
