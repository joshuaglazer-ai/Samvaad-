import { useTranslation } from "react-i18next";
import IconCard from "./IconCard";
import Icon from "./Icon";
import { LANGUAGES, type Lang } from "../../lib/languages";
import { getSpeech } from "../../lib/voice";

interface Props {
  value: Lang;
  onChange: (l: Lang) => void;
  label: string;
  /** Larger picture cards (onboarding / join) or compact buttons (landing). */
  variant?: "cards" | "compact";
}

/** English · ಕನ್ನಡ · हिन्दी · తెలుగు — each in its own script, each with a separate "Hear" button that reads the
 * language name aloud (separate so choosing a language never triggers "hear" by mistake). */
export default function LanguagePicker({ value, onChange, label, variant = "cards" }: Props) {
  const { t } = useTranslation();
  return (
    <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label={label}>
      {LANGUAGES.map((l) => (
        <div key={l.code} className="flex flex-col gap-1.5">
          {variant === "cards" ? (
            <IconCard icon="globe" label={l.name} selected={value === l.code} onClick={() => onChange(l.code)} />
          ) : (
            <button type="button" role="radio" aria-checked={value === l.code} lang={l.code} onClick={() => onChange(l.code)}
              className={`flex min-h-12 items-center justify-center gap-2 rounded-2xl border-2 px-4 text-lg font-semibold text-ink-900 ${
                value === l.code ? "border-primary-600 bg-white" : "border-lavender-200 bg-white/70"
              }`}>
              <Icon name="globe" size={20} /> {l.name}
            </button>
          )}
          <button type="button" onClick={() => getSpeech().speak(l.name, l.code)} aria-label={`${t("family.hear")}: ${l.name}`}
            className="flex min-h-12 items-center justify-center gap-1.5 rounded-xl bg-lavender-100 px-2 text-sm font-semibold text-primary-700">
            <Icon name="speaker" size={18} /><span>{t("family.hear")}</span>
          </button>
        </div>
      ))}
    </div>
  );
}
