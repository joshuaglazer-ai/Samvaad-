import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getSpeech, type VoiceLang } from "./voice";
import { api } from "./api";
import { useAppState } from "./state";
import { asLang } from "./languages";

/** Read text aloud in the current language. If no voice is installed, `missingVoice` turns on so the UI can
 * show "Kannada voice not available on this device" and keep the text highlighted instead. */
export function useSpeak() {
  const { i18n } = useTranslation();
  const { sessionId } = useAppState();
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const [missingVoice, setMissingVoice] = useState(false);
  const lang = asLang(i18n.language) as VoiceLang;

  const stop = useCallback(() => {
    getSpeech().cancel();
    setSpeakingId(null);
  }, []);

  const speak = useCallback(
    (text: string, id = "default") => {
      const res = getSpeech().speak(text, lang, () => setSpeakingId((cur) => (cur === id ? null : cur)));
      if (res.ok) {
        setMissingVoice(false);
        setSpeakingId(id);
        api.event({ session_id: sessionId, event_type: "read_aloud_used", payload: { lang } }).catch(() => undefined);
      } else {
        setMissingVoice(res.reason === "no_voice");
        setSpeakingId(id); // keep the text highlighted as the fallback
        window.setTimeout(() => setSpeakingId((cur) => (cur === id ? null : cur)), 6000);
      }
      return res;
    },
    [lang, sessionId],
  );

  useEffect(() => () => getSpeech().cancel(), []);

  return { speak, stop, speakingId, missingVoice, lang, canSpeak: getSpeech().canSpeak() };
}
