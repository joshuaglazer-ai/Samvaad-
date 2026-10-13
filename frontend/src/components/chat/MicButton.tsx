import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { m } from "framer-motion";
import Icon from "../ui/Icon";
import { getSpeech, type VoiceLang } from "../../lib/voice";
import { api } from "../../lib/api";
import { useAppState } from "../../lib/state";

interface Props {
  lang: VoiceLang;
  onResult: (text: string) => void;
  disabled?: boolean;
  /** Draws attention to the mic (e.g. on the parent's turn). */
  highlight?: boolean;
}

/** Big mic button. Shows interim text while listening; stops on silence. Hidden where unsupported. */
export default function MicButton({ lang, onResult, disabled, highlight }: Props) {
  const { t } = useTranslation();
  const { sessionId, lite } = useAppState();
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const stopRef = useRef<() => void>(() => undefined);
  const supported = getSpeech().canListen();

  useEffect(() => () => stopRef.current(), []);

  if (!supported) {
    return <p className="text-sm text-ink-600">{t("chat.voiceUnsupported")}</p>;
  }

  const start = () => {
    getSpeech().cancel();
    setInterim("");
    setListening(true);
    stopRef.current = getSpeech().listen(lang, {
      onInterim: setInterim,
      onFinal: (text) => {
        onResult(text);
        api.event({ session_id: sessionId, event_type: "voice_used", payload: { lang } }).catch(() => undefined);
      },
      onEnd: () => {
        setListening(false);
        setInterim("");
      },
      onError: () => setListening(false),
    });
  };
  const stop = () => {
    stopRef.current();
    setListening(false);
  };

  return (
    <div className="flex flex-col items-start gap-1">
      <m.button
        type="button"
        onClick={listening ? stop : start}
        disabled={disabled}
        aria-pressed={listening}
        animate={listening && !lite ? { scale: [1, 1.08, 1], boxShadow: ["0 0 0 0 rgba(107,79,196,.5)", "0 0 0 16px rgba(107,79,196,0)", "0 0 0 0 rgba(107,79,196,0)"] } : { scale: 1 }}
        transition={listening ? { repeat: Infinity, duration: 1.4 } : undefined}
        className={`flex min-h-12 items-center justify-center gap-2 rounded-full px-5 text-white disabled:opacity-50 ${
          listening ? "bg-primary-700" : "bg-primary-600 hover:bg-primary-700"
        } ${highlight && !listening ? "ring-4 ring-star-400 ring-offset-2 ring-offset-white" : ""}`}
      >
        <Icon name={listening ? "stop" : "mic"} size={24} />
        <span className="text-base font-semibold">{listening ? t("chat.stop") : t("chat.mic")}</span>
      </m.button>
      {listening && (
        <p role="status" className="max-w-xs text-center text-sm text-ink-600">{interim || t("chat.listening")}</p>
      )}
    </div>
  );
}
