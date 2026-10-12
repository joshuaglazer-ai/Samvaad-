import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Button from "../components/ui/Button";
import MoodCheck from "../components/ui/MoodCheck";
import ReadAloud from "../components/ui/ReadAloud";
import { api } from "../lib/api";
import { useAppState } from "../lib/state";
import { useSpeak } from "../lib/useSpeak";

/** Self-reported mood (1–5) for learner and parent, before and after the conversation. */
export default function Mood() {
  const { phase = "pre" } = useParams();
  const isPost = phase === "post";
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { sessionId, readAloud } = useAppState();
  const { speak, stop, speakingId } = useSpeak();
  const [learner, setLearner] = useState<number | null>(null);
  const [parent, setParent] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const title = isPost ? t("mood.postTitle") : t("mood.preTitle");

  useEffect(() => {
    if (!sessionId) navigate("/start");
  }, [sessionId, navigate]);
  useEffect(() => {
    if (readAloud) speak(title, "mood");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  const next = async () => {
    if (!sessionId) return;
    setBusy(true);
    const p = isPost ? "post" : "pre";
    await Promise.allSettled([
      learner && api.mood(sessionId, { respondent: "learner", phase: p, value: learner }),
      parent && api.mood(sessionId, { respondent: "parent", phase: p, value: parent }),
    ]);
    if (isPost) await api.endSession(sessionId).catch(() => undefined);
    setBusy(false);
    navigate(isPost ? `/summary/${sessionId}` : "/chat");
  };

  return (
    <section className="mt-2 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <h1 className={`text-2xl font-bold text-ink-900 ${speakingId === "mood" ? "reading-highlight" : ""}`}>{title}</h1>
        <ReadAloud speaking={speakingId === "mood"} onSpeak={() => speak(title, "mood")} onStop={stop} compact />
      </div>
      <MoodCheck label={t("mood.learner")} value={learner} onChange={setLearner} />
      <MoodCheck label={t("mood.parent")} value={parent} onChange={setParent} />
      <div className="flex justify-between gap-3">
        <Button variant="ghost" onClick={() => navigate(isPost ? `/summary/${sessionId}` : "/chat")}>{t("app.skip")}</Button>
        <Button size="lg" iconRight="arrowRight" disabled={(!learner && !parent) || busy} onClick={next}>{t("mood.continue")}</Button>
      </div>
    </section>
  );
}
