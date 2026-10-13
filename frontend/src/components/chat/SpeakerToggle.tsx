import { useTranslation } from "react-i18next";
import Icon from "../ui/Icon";
import type { Speaker } from "../../lib/state";

interface Props {
  value: Speaker;
  onChange: (s: Speaker) => void;
  options: Speaker[];
}

const AVATAR: Record<Speaker, { icon: string; bg: string }> = {
  learner: { icon: "learner", bg: "bg-sky-200" },
  parent: { icon: "parent", bg: "bg-lavender-200" },
  helper: { icon: "helper", bg: "bg-star-400/50" },
};

/** Large avatars so learner and parent can take turns on one phone. */
export default function SpeakerToggle({ value, onChange, options }: Props) {
  const { t } = useTranslation();
  return (
    <div role="radiogroup" aria-label={t("chat.whoIsSpeaking")} className="flex flex-wrap items-center gap-2">
      <span className="mr-1 text-sm font-semibold text-ink-600">{t("chat.whoIsSpeaking")}</span>
      {options.map((s) => (
        <button
          key={s}
          type="button"
          role="radio"
          aria-checked={value === s}
          onClick={() => onChange(s)}
          className={`flex min-h-12 items-center gap-2 rounded-full border-2 py-1 pl-1 pr-4 text-base font-semibold ${
            value === s ? "border-primary-600 bg-white text-ink-900 shadow-[var(--shadow-soft)]" : "border-transparent bg-white/60 text-ink-900"
          }`}
        >
          <span className={`grid h-10 w-10 place-items-center rounded-full ${AVATAR[s].bg} text-ink-900`}>
            <Icon name={AVATAR[s].icon} size={22} />
          </span>
          {t(`chat.${s}`)}
        </button>
      ))}
    </div>
  );
}

export { AVATAR };
