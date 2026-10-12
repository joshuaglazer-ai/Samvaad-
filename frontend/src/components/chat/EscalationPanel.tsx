import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Button from "../ui/Button";
import Icon from "../ui/Icon";
import { api, wsUrl, type EscalationInfo, type TranscriptMessage } from "../../lib/api";
import type { Speaker } from "../../lib/state";

interface Props {
  escalation: EscalationInfo;
  speaker: Speaker;
  onBack: () => void;
}

type Mode = "choose" | "live" | "callback" | "requested";

/** Family side of human escalation: wait for live chat (WebSocket, 3 s polling fallback) or request a call back. */
export default function EscalationPanel({ escalation, speaker, onBack }: Props) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<Mode>("choose");
  const [info, setInfo] = useState(escalation);
  const [msgs, setMsgs] = useState<TranscriptMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [phone, setPhone] = useState("");
  const [time, setTime] = useState<"morning" | "afternoon" | "evening">("morning");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const lastId = useRef(0);
  const pollRef = useRef<number | null>(null);

  const addMsgs = useCallback((items: TranscriptMessage[]) => {
    if (!items.length) return;
    setMsgs((cur) => {
      const seen = new Set(cur.map((m) => m.id));
      const next = [...cur, ...items.filter((m) => !seen.has(m.id))];
      lastId.current = Math.max(lastId.current, ...next.map((m) => m.id));
      return next;
    });
  }, []);

  // Refresh online status once on open.
  useEffect(() => {
    api.escalationStatus(escalation.id).then(setInfo).catch(() => undefined);
  }, [escalation.id]);

  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = window.setInterval(async () => {
      try {
        addMsgs(await api.escalationMessages(escalation.id, lastId.current));
        setInfo(await api.escalationStatus(escalation.id));
      } catch {
        /* keep polling */
      }
    }, 3000);
  }, [addMsgs, escalation.id]);

  useEffect(() => {
    if (mode !== "live") return;
    let closedByUs = false;
    try {
      const ws = new WebSocket(wsUrl(`/ws/escalation/${escalation.id}?role=family`));
      wsRef.current = ws;
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === "message") addMsgs([data.message]);
        if (data.type === "status") setInfo((i) => ({ ...i, status: data.status }));
      };
      ws.onerror = () => startPolling();
      ws.onclose = () => {
        if (!closedByUs) startPolling();
      };
    } catch {
      startPolling();
    }
    api.escalationMessages(escalation.id, 0).then(addMsgs).catch(() => startPolling());
    return () => {
      closedByUs = true;
      wsRef.current?.close();
      if (pollRef.current) window.clearInterval(pollRef.current);
      pollRef.current = null;
    };
  }, [mode, escalation.id, addMsgs, startPolling]);

  const send = async () => {
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "message", text, speaker }));
    else addMsgs([await api.sendEscalationMessage(escalation.id, { text, speaker })]);
  };

  const requestCallback = async () => {
    setError(null);
    try {
      await api.callback(escalation.id, { phone, preferred_time: time, consent });
      setMode("requested");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("app.error"));
    }
  };

  const joined = ["assigned", "in_progress"].includes(info.status);

  return (
    <section className="glass mt-4 border-2 border-primary-600 p-4" aria-live="polite">
      <div className="flex items-start justify-between gap-2">
        <h2 className="flex items-center gap-2 text-xl font-bold text-ink-900">
          <Icon name="chat" className="text-primary-700" /> {t("chat.talkToCounsellor")}
        </h2>
        <Button variant="ghost" icon="arrowLeft" onClick={onBack}>{t("escalation.back")}</Button>
      </div>
      <p className="mt-2 text-lg text-ink-900">
        {joined ? t("escalation.connected") : info.counsellor_online ? t("escalation.joining") : t("escalation.offline")}
      </p>

      {mode === "choose" && (
        <div className={`mt-4 flex gap-3 ${info.counsellor_online ? "flex-col sm:flex-row" : "flex-col-reverse sm:flex-row-reverse"}`}>
          <Button size="lg" icon="hourglass" variant={info.counsellor_online ? "primary" : "secondary"} className="flex-1" onClick={() => setMode("live")}>
            {t("escalation.wait")}
          </Button>
          <Button size="lg" icon="phone" variant={info.counsellor_online ? "secondary" : "primary"} className="flex-1" onClick={() => setMode("callback")}>
            {t("escalation.callback")}
          </Button>
        </div>
      )}

      {mode === "live" && (
        <div className="mt-4">
          <ul className="max-h-72 space-y-2 overflow-y-auto">
            {msgs.map((m) => (
              <li key={m.id} className={`rounded-2xl px-3 py-2 text-lg ${m.role === "counsellor" ? "bg-success-600/10 text-ink-900" : "ml-8 bg-primary-600 text-white"}`}>
                <span className="block text-sm font-semibold opacity-90">
                  {m.role === "counsellor" ? t("escalation.counsellorLabel") : t(`chat.${m.speaker}`, m.speaker)}
                </span>
                {m.text}
              </li>
            ))}
          </ul>
          <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); send(); }}>
            <label className="sr-only" htmlFor="esc-draft">{t("chat.placeholder")}</label>
            <input id="esc-draft" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={t("chat.placeholder")}
              className="min-h-12 flex-1 rounded-2xl border border-lavender-200 bg-white px-4 text-lg text-ink-900" />
            <Button type="submit" icon="send">{t("chat.send")}</Button>
          </form>
          <Button variant="ghost" icon="phone" className="mt-2" onClick={() => setMode("callback")}>{t("escalation.callback")}</Button>
        </div>
      )}

      {mode === "callback" && (
        <form className="mt-4 space-y-4" onSubmit={(e) => { e.preventDefault(); requestCallback(); }}>
          <div>
            <label htmlFor="cb-phone" className="mb-1 block font-semibold text-ink-900">{t("escalation.phone")}</label>
            <input id="cb-phone" type="tel" inputMode="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
              className="min-h-12 w-full rounded-2xl border border-lavender-200 bg-white px-4 text-xl tracking-wide text-ink-900" />
          </div>
          <fieldset>
            <legend className="mb-1 font-semibold text-ink-900">{t("escalation.time")}</legend>
            <div className="grid grid-cols-3 gap-2">
              {(["morning", "afternoon", "evening"] as const).map((v) => (
                <button key={v} type="button" aria-pressed={time === v} onClick={() => setTime(v)}
                  className={`flex min-h-12 items-center justify-center gap-1 rounded-2xl border-2 text-base font-semibold ${time === v ? "border-primary-600 bg-white" : "border-lavender-200 bg-white/70"} text-ink-900`}>
                  <Icon name={v === "evening" ? "star" : "sun"} size={18} /> {t(`escalation.${v}`)}
                </button>
              ))}
            </div>
          </fieldset>
          <label className="flex items-start gap-3 text-base text-ink-900">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-1 h-6 w-6 shrink-0 accent-primary-600" />
            <span>{t("escalation.consent")}</span>
          </label>
          {error && <p role="alert" className="text-danger-600">{error}</p>}
          <Button type="submit" size="lg" icon="phone" className="w-full" disabled={!consent || phone.replace(/\D/g, "").length < 10}>
            {t("escalation.submit")}
          </Button>
        </form>
      )}

      {mode === "requested" && (
        <p className="mt-4 flex items-center gap-2 rounded-2xl bg-success-600/10 p-3 text-lg font-semibold text-ink-900">
          <Icon name="check" className="text-success-600" /> {t("escalation.requested")}
        </p>
      )}
    </section>
  );
}
