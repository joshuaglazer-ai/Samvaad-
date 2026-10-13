import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Button from "../components/ui/Button";
import Icon from "../components/ui/Icon";
import Toggle from "../components/ui/Toggle";
import { VoiceMissingNotice } from "../components/ui/ReadAloud";
import SpeakerToggle from "../components/chat/SpeakerToggle";
import MessageBubble, { type ChatItem } from "../components/chat/MessageBubble";
import MicButton from "../components/chat/MicButton";
import QuickReplies from "../components/chat/QuickReplies";
import TypingStars from "../components/chat/TypingStars";
import EscalationPanel from "../components/chat/EscalationPanel";
import Modal from "../components/ui/Modal";
import GoalPicker from "../components/goal/GoalPicker";
import { api, type EscalationInfo, type GoalComparison, type GoalDraft } from "../lib/api";
import { useAppState, type Speaker } from "../lib/state";
import { getDeviceId } from "../lib/deviceId";
import { asLang, languageName, type Lang } from "../lib/languages";
import { useSpeak } from "../lib/useSpeak";

export default function Chat() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { sessionId, profile, setProfile, readAloud, setReadAloud, disclaimerSeen, markDisclaimerSeen } = useAppState();
  const { speak, stop, speakingId, missingVoice, lang } = useSpeak();
  const [items, setItems] = useState<ChatItem[]>([]);
  // Who can speak on this phone depends on how the family is taking part.
  const speakers: Speaker[] = profile.role === "parent"
    ? ["parent"]
    : profile.participation_mode === "together"
      ? (profile.helper_mode ? ["learner", "parent", "helper"] : ["learner", "parent"])
      : (profile.helper_mode ? ["learner", "helper"] : ["learner"]);
  const [speaker, setSpeaker] = useState<Speaker>(speakers.includes("parent") ? "parent" : "learner");
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState("");
  const [quick, setQuick] = useState<string[]>([]);
  const [suggestLang, setSuggestLang] = useState<Lang | null>(null);
  const [escalation, setEscalation] = useState<EscalationInfo | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [goals, setGoals] = useState<GoalComparison | null>(null);
  const [goalOpen, setGoalOpen] = useState(false);
  const [goalSaved, setGoalSaved] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  // The goal this phone can change: the parent's hope on a parent's own phone, otherwise the learner's goal.
  const goalWho = profile.role === "parent" ? "parent" : "learner";
  const myGoal = goals?.[goalWho] ?? null;

  useEffect(() => {
    if (sessionId) api.aspirations(sessionId, i18n.language).then(setGoals).catch(() => undefined);
  }, [sessionId, i18n.language]);

  const changeGoal = async (g: GoalDraft) => {
    if (!sessionId) return;
    try {
      setGoals(await api.saveAspiration(sessionId, goalWho, g));
      setGoalOpen(false);
      setGoalSaved(true);
      api.event({ session_id: sessionId, event_type: "goal_changed", payload: { who: goalWho, source: g.source } }).catch(() => undefined);
    } catch {
      setError(t("app.offline"));
    }
  };

  const starters = [1, 2, 3, 4, 5, 6].map((n) => t(`chat.starter${n}`));

  useEffect(() => {
    if (!sessionId) {
      navigate("/start");
      return;
    }
    // Resume an existing conversation (e.g. after a language switch or reload).
    api.transcript(sessionId).then((rows) => {
      setItems(rows.map((r) => ({ id: String(r.id), role: r.role, speaker: r.speaker, text: r.text, cards: r.cards ?? [] })));
    }).catch(() => undefined);
  }, [sessionId, navigate]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [items, busy]);

  // Two phones share one conversation: pick up the other phone's messages every few seconds.
  useEffect(() => {
    if (!sessionId || profile.participation_mode !== "two_devices") return;
    const me = getDeviceId();
    const id = window.setInterval(() => {
      if (busy) return;
      api.transcript(sessionId).then((rows) => {
        setItems((cur) => {
          const known = new Set(cur.map((x) => x.id));
          const fresh = rows.filter((r) => r.device_id !== me && !r.device_id?.startsWith("live") && !known.has(String(r.id)));
          return fresh.length ? [...cur, ...fresh.map((r) => ({ id: String(r.id), role: r.role, speaker: r.speaker, text: r.text, cards: r.cards ?? [] }))] : cur;
        });
      }).catch(() => undefined);
    }, 4000);
    return () => window.clearInterval(id);
  }, [sessionId, profile.participation_mode, busy]);

  const greeting = `${t("landing.greeting")} ${disclaimerSeen ? "" : t("app.disclaimer")}`.trim();
  useEffect(() => {
    if (readAloud && items.length === 0) speak(greeting, "greeting");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const send = async (text: string) => {
    const clean = text.trim();
    if (!clean || !sessionId || busy) return;
    setError(null);
    stop();
    markDisclaimerSeen();
    setItems((cur) => [...cur, { id: `u-${Date.now()}`, role: "user", speaker, text: clean, cards: [] }]);
    setDraft("");
    setBusy(true);
    try {
      const res = await api.chat({ session_id: sessionId, speaker, text: clean, language: asLang(i18n.language) });
      const id = String(res.message_id);
      setItems((cur) => [...cur, { id, role: "assistant", speaker: "bot", text: res.reply_text, cards: res.cards }]);
      setQuick(res.quick_replies);
      setSuggestLang(res.suggest_language ?? null);
      if (res.escalation) {
        setEscalation(res.escalation);
        setPanelOpen(true);
      }
      if (readAloud) speak(res.reply_text, id);
    } catch {
      setError(t("app.offline"));
    } finally {
      setBusy(false);
    }
  };

  const talkToCounsellor = async () => {
    if (!sessionId) return;
    api.event({ session_id: sessionId, event_type: "counsellor_button" }).catch(() => undefined);
    try {
      const esc = escalation ?? (await api.escalate({ session_id: sessionId, trigger: "user_request" }));
      setEscalation(esc);
      setPanelOpen(true);
    } catch {
      setError(t("app.offline"));
    }
  };

  const pick = (q: string) => {
    api.event({ session_id: sessionId, event_type: "quick_reply_used" }).catch(() => undefined);
    if (/counsel|ಸಲಹೆಗಾರ/i.test(q)) {
      talkToCounsellor();
      return;
    }
    send(q);
  };

  return (
    <section className="mt-1 flex flex-col gap-3">
      <div className="glass flex flex-wrap items-center justify-between gap-2 p-3">
        <SpeakerToggle value={speaker} onChange={setSpeaker} options={speakers} />
        <div className="flex flex-wrap items-center gap-1">
          <Toggle checked={readAloud} onChange={setReadAloud} label={t("chat.autoRead")} icon="speaker" />
          <Button variant="ghost" iconRight="arrowRight" onClick={() => navigate("/mood/post")}>{t("chat.finish")}</Button>
        </div>
      </div>
      {profile.participation_mode !== "learner_only" || goalWho === "learner" ? (
        <div className="glass flex flex-wrap items-center justify-between gap-2 px-3 py-2" data-testid="chat-goal">
          <p className="flex min-w-0 items-center gap-2 text-base text-ink-900" aria-live="polite">
            <Icon name="star" size={20} className="shrink-0 text-primary-700" />
            <span>{goalWho === "parent" ? t("goal.parentHope") : t("goal.yourGoal")}:</span>
            <strong className="truncate" data-testid="chat-goal-label">{myGoal?.label || t("goal.notChosen")}</strong>
            {goalSaved && <span className="sr-only">{t("goal.updated")}</span>}
          </p>
          <Button variant="ghost" icon="refresh" onClick={() => { setGoalSaved(false); setGoalOpen(true); }}>{t("goal.change")}</Button>
        </div>
      ) : null}
      <Modal open={goalOpen} onClose={() => setGoalOpen(false)} title={goalWho === "parent" ? t("goal.parentQuestion") : t("goal.question")}>
        <GoalPicker who={goalWho} district={profile.district} onDone={changeGoal} />
      </Modal>
      {profile.helper_mode && (
        <p className="flex items-start gap-2 rounded-2xl bg-lavender-100 px-3 py-2 text-base text-ink-900">
          <Icon name="helper" className="mt-0.5 shrink-0 text-primary-700" /> {t("chat.helperTip")}
        </p>
      )}
      {missingVoice && <VoiceMissingNotice />}
      {speaker === "parent" && (
        <p className="flex items-center gap-2 rounded-2xl bg-star-400/25 px-3 py-2 text-base font-semibold text-ink-900">
          <Icon name="mic" className="shrink-0 text-primary-700" /> {t("family.parentPrompt")}
        </p>
      )}

      <ul className="flex flex-col gap-4 py-2" aria-live="polite">
        <MessageBubble
          item={{ id: "greeting", role: "assistant", speaker: "bot", text: greeting, cards: [] }}
          speaking={speakingId === "greeting"} onSpeak={() => speak(greeting, "greeting")} onStop={stop}
        />
        {items.map((it) => (
          <MessageBubble key={it.id} item={it} speaking={speakingId === it.id} onSpeak={() => speak(it.text, it.id)} onStop={stop} />
        ))}
        {busy && <li><TypingStars /></li>}
      </ul>
      <div ref={endRef} />

      {error && <p role="alert" className="rounded-xl bg-danger-600/10 px-3 py-2 text-danger-600">{error}</p>}
      {suggestLang && (
        <Button variant="secondary" icon="globe" className="self-start" lang={suggestLang}
          onClick={() => { i18n.changeLanguage(suggestLang); setProfile({ language: suggestLang }); setSuggestLang(null); }}>
          {t("chat.switchTo", { lang: languageName(suggestLang) })}
        </Button>
      )}

      {escalation && panelOpen ? (
        <EscalationPanel escalation={escalation} speaker={speaker} onBack={() => setPanelOpen(false)} />
      ) : (
        <div className="glass sticky bottom-2 z-10 space-y-3 !bg-white p-3">
          <QuickReplies items={quick.length ? quick : starters} onPick={pick} disabled={busy} />
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); send(draft); }}>
            <label className="sr-only" htmlFor="chat-draft">{t("chat.placeholder")}</label>
            <input
              id="chat-draft" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={t("chat.placeholder")}
              className="min-h-12 w-full min-w-0 flex-1 rounded-2xl border border-lavender-200 bg-white px-4 text-lg text-ink-900 placeholder:text-ink-600"
            />
            <Button type="submit" icon="send" disabled={busy || !draft.trim()}>{t("chat.send")}</Button>
          </form>
          <div className="flex flex-wrap items-start gap-2">
            <MicButton lang={lang} onResult={send} disabled={busy} highlight={speaker === "parent"} />
            <Button variant="secondary" icon="chat" onClick={talkToCounsellor}>{t("chat.talkToCounsellor")}</Button>
          </div>
        </div>
      )}
    </section>
  );
}
