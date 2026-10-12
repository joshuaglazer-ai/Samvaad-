import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./en.json";
import kn from "./kn.json";

export type Lang = "en" | "kn";

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem("samvaad.lang");
    if (saved === "en" || saved === "kn") return saved;
  } catch {
    /* storage may be blocked */
  }
  return "en";
}

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, kn: { translation: kn } },
  lng: initialLang(),
  fallbackLng: "en",
  interpolation: { escapeValue: false },
  returnNull: false,
});

function applyLang(lng: string) {
  document.documentElement.lang = lng;
  try {
    localStorage.setItem("samvaad.lang", lng);
  } catch {
    /* ignore */
  }
}
applyLang(i18n.language);
i18n.on("languageChanged", applyLang);

export default i18n;
