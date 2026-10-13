import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Icon from "./Icon";
import { LANGUAGES, asLang, languageName, type Lang } from "../../lib/languages";
import { getSpeech } from "../../lib/voice";

/** Header language switch, visible on every screen: shows the current language in its own script and opens a
 * short list of all four languages (each with a "Hear" button). */
export default function LanguageMenu({ onChange }: { onChange: (l: Lang) => void }) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = asLang(i18n.language);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label={`${t("app.language")}: ${languageName(current)}`}
        className="flex min-h-12 items-center gap-1.5 whitespace-nowrap rounded-2xl border border-lavender-200 bg-white/80 px-2 text-sm font-semibold text-ink-900"
      >
        <Icon name="globe" size={20} />
        <span lang={current}>{languageName(current)}</span>
      </button>
      {open && (
        <div role="menu" aria-label={t("landing.chooseLanguage")}
          className="glass absolute right-0 z-30 mt-2 w-60 space-y-1 bg-white p-2">
          {LANGUAGES.map((l) => (
            <div key={l.code} className="flex items-center gap-1">
              <button type="button" role="menuitemradio" aria-checked={current === l.code} lang={l.code}
                onClick={() => { onChange(l.code); setOpen(false); }}
                className={`flex min-h-12 flex-1 items-center gap-2 rounded-xl px-3 text-left text-base font-semibold text-ink-900 ${
                  current === l.code ? "bg-lavender-100" : "hover:bg-lavender-100"
                }`}>
                {current === l.code ? <Icon name="check" size={18} /> : <span className="w-[18px]" />}
                {l.name}
              </button>
              <button type="button" onClick={() => getSpeech().speak(l.name, l.code)} aria-label={`${t("family.hear")}: ${l.name}`}
                className="flex min-h-12 min-w-12 items-center justify-center rounded-xl text-primary-700 hover:bg-lavender-100">
                <Icon name="speaker" size={20} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
