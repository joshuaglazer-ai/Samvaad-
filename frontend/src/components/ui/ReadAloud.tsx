import { useTranslation } from "react-i18next";
import Icon from "./Icon";

interface Props {
  speaking: boolean;
  onSpeak: () => void;
  onStop: () => void;
  compact?: boolean;
}

export default function ReadAloud({ speaking, onSpeak, onStop, compact }: Props) {
  const { t } = useTranslation();
  return (
    <button
      type="button"
      onClick={speaking ? onStop : onSpeak}
      aria-pressed={speaking}
      className={`inline-flex min-h-12 items-center gap-1.5 rounded-2xl px-3 font-semibold ${
        speaking ? "bg-star-400/40 text-ink-900" : "bg-lavender-100 text-primary-700 hover:bg-lavender-200"
      } ${compact ? "text-sm" : "text-base"}`}
    >
      <Icon name={speaking ? "stop" : "speaker"} size={20} />
      <span>{speaking ? t("chat.stopReading") : t("chat.readAloud")}</span>
    </button>
  );
}

export function VoiceMissingNotice() {
  const { t } = useTranslation();
  return (
    <p role="status" className="mt-2 flex items-center gap-2 rounded-xl bg-star-400/25 px-3 py-2 text-sm text-ink-900">
      <Icon name="info" size={18} />
      <span>{t("chat.voiceMissing")}</span>
    </p>
  );
}
