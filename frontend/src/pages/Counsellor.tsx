import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Button from "../components/ui/Button";
import Icon from "../components/ui/Icon";
import PinGate from "../components/ui/PinGate";
import CardView from "../components/cards/CardView";
import {
  api, wsUrl, type CallbackItem, type CounsellorCase, type CounsellorCaseDetail, type TranscriptMessage,
} from "../lib/api";
import { minutesSince } from "../lib/format";

const TRIGGER_ICON: Record<string, string> = {
  user_request: "hand", no_data: "alert", negative_sentiment: "heart", sensitive_topic: "shield", repeated_failure: "refresh",
};
const STATUS_STYLE: Record<string, string> = {
  pending: "bg-warning-600 text-white", assigned: "bg-info-600 text-white", in_progress: "bg-primary-600 text-white",
  resolved: "bg-success-600 text-white",
};

function Console({ pin, logout }: { pin: string; logout: () => void }) {
  const { t } = useTranslation();
  const [queue, setQueue] = useState<CounsellorCase[]>([]);
  const [callbacks, setCallbacks] = useState<CallbackItem[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<CounsellorCaseDetail | null>(null);
  const [live, setLive] = useState<TranscriptMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [summaryLang, setSummaryLang] = useState<"en" | "kn">("en");
  const [me, setMe] = useState(() => {
    try {
      return sessionStorage.getItem("samvaad.counsellorName") ?? "Counsellor 1";
    } catch {
      return "Counsellor 1";
    }
  });
  const [now, setNow] = useState(new Date());
  const caseWs = useRef<WebSocket | null>(null);
  const lastLive = useRef(0);

  const refresh = useCallback(async () => {
    try {
      setQueue(await api.counsellor.queue(pin));
      setCallbacks(await api.counsellor.callbacks(pin));
    } catch {
      logout();
    }
  }, [pin, logout]);

  // Lobby socket marks this counsellor as online and pushes new cases; queue also polls as a fallback.
  useEffect(() => {
    refresh();
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsUrl(`/ws/counsellor?pin=${encodeURIComponent(pin)}`));
      ws.onmessage = () => refresh();
    } catch {
      /* polling covers it */
    }
    const poll = window.setInterval(refresh, 5000);
    const tick = window.setInterval(() => setNow(new Date()), 30000);
    const ping = window.setInterval(() => ws?.readyState === WebSocket.OPEN && ws.send("ping"), 20000);
    return () => {
      ws?.close();
      window.clearInterval(poll);
      window.clearInterval(tick);
      window.clearInterval(ping);
    };
  }, [pin, refresh]);

  const addLive = useCallback((items: TranscriptMessage[]) => {
    if (!items.length) return;
    setLive((cur) => {
      const seen = new Set(cur.map((x) => x.id));
      const next = [...cur, ...items.filter((x) => !seen.has(x.id))];
      lastLive.current = Math.max(lastLive.current, ...next.map((x) => x.id));
      return next;
    });
  }, []);

  // Open the selected case: details, live room socket (with 3 s polling fallback).
  useEffect(() => {
    if (selected == null) return;
    setLive([]);
    lastLive.current = 0;
    api.counsellor.caseDetail(pin, selected).then((d) => {
      setDetail(d);
      setSummaryLang(d.language === "kn" ? "kn" : "en");
    }).catch(() => undefined);
    api.escalationMessages(selected, 0).then(addLive).catch(() => undefined);
    let poll: number | null = null;
    const startPoll = () => {
      if (poll) return;
      poll = window.setInterval(() => api.escalationMessages(selected, lastLive.current).then(addLive).catch(() => undefined), 3000);
    };
    try {
      const ws = new WebSocket(wsUrl(`/ws/escalation/${selected}?role=counsellor&pin=${encodeURIComponent(pin)}`));
      caseWs.current = ws;
      ws.onopen = () => api.escalationMessages(selected, lastLive.current).then(addLive).catch(() => undefined);
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === "message") addLive([data.message]);
      };
      ws.onerror = startPoll;
      ws.onclose = startPoll;
    } catch {
      startPoll();
    }
    return () => {
      if (caseWs.current) {
        caseWs.current.onclose = null;
        caseWs.current.close();
      }
      if (poll) window.clearInterval(poll);
    };
  }, [selected, pin, addLive]);

  const update = async (body: { status?: string; assigned_to?: string }) => {
    if (selected == null) return;
    await api.counsellor.update(pin, selected, body);
    setDetail(await api.counsellor.caseDetail(pin, selected));
    refresh();
  };

  const send = async () => {
    const text = draft.trim();
    if (!text || selected == null) return;
    setDraft("");
    const ws = caseWs.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "message", text }));
    else addLive([await api.counsellor.reply(pin, selected, text)]);
    if (detail?.status !== "in_progress") update({ status: "in_progress" });
  };

  const saveMe = (v: string) => {
    setMe(v);
    try {
      sessionStorage.setItem("samvaad.counsellorName", v);
    } catch {
      /* ignore */
    }
  };

  return (
    <section className="mt-2 grid gap-4 lg:grid-cols-[360px_1fr]">
      <aside className="space-y-4">
        <div className="glass p-4">
          <div className="flex items-center justify-between gap-2">
            <h1 className="flex items-center gap-2 text-xl font-bold text-ink-900"><Icon name="chat" className="text-primary-700" />{t("counsellor.title")}</h1>
            <Button variant="ghost" icon="lock" onClick={logout}>{t("app.close")}</Button>
          </div>
          <label className="mt-2 block text-sm text-ink-600">
            ID
            <input value={me} onChange={(e) => saveMe(e.target.value)} className="mt-1 min-h-12 w-full rounded-xl border border-lavender-200 bg-white px-3 text-base text-ink-900" />
          </label>
        </div>

        <div className="glass p-4">
          <h2 className="mb-2 text-lg font-bold text-ink-900">{t("counsellor.queue")} ({queue.length})</h2>
          {queue.length === 0 && <p className="text-ink-600">{t("counsellor.empty")}</p>}
          <ul className="space-y-2">
            {queue.map((c) => (
              <li key={c.id}>
                <button type="button" onClick={() => setSelected(c.id)} aria-pressed={selected === c.id}
                  className={`w-full rounded-2xl border-2 p-3 text-left ${selected === c.id ? "border-primary-600 bg-white" : "border-transparent bg-white/70 hover:border-lavender-300"}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-1.5 font-semibold text-ink-900">
                      <Icon name={TRIGGER_ICON[c.trigger] ?? "alert"} size={18} className="text-primary-700" />
                      {c.trigger.replace(/_/g, " ")}
                    </span>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${STATUS_STYLE[c.status]}`}>{c.status.replace("_", " ")}</span>
                  </div>
                  <p className="mt-1 text-sm text-ink-600">
                    #{c.id} · {c.district} · {c.language === "kn" ? "ಕನ್ನಡ" : "English"} · {t("counsellor.waiting", { m: minutesSince(c.created_at, now) })}
                    {c.has_callback && " · ☎"}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="glass p-4">
          <h2 className="mb-2 flex items-center gap-2 text-lg font-bold text-ink-900"><Icon name="phone" className="text-primary-700" />{t("counsellor.callbacks")}</h2>
          {callbacks.length === 0 && <p className="text-ink-600">—</p>}
          <ul className="space-y-2">
            {callbacks.map((cb) => (
              <li key={cb.id} className="rounded-2xl bg-white/80 p-3">
                <p className="text-lg font-bold tracking-wide text-ink-900">{cb.phone ?? "—"}</p>
                <p className="text-sm text-ink-600">#{cb.escalation_id} · {cb.district} · {cb.preferred_time}</p>
                <Button variant="ghost" icon="close" className="mt-1" onClick={async () => { await api.counsellor.deleteCallback(pin, cb.id); refresh(); }}>
                  {t("counsellor.deletePhone")}
                </Button>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      <div className="space-y-4">
        {!detail ? (
          <div className="glass grid min-h-64 place-items-center p-6 text-ink-600">{t("counsellor.empty")}</div>
        ) : (
          <>
            <div className="glass p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-xl font-bold text-ink-900">{t("counsellor.summary")} #{detail.id}</h2>
                <div className="flex gap-1" role="group" aria-label="Summary language">
                  {(["en", "kn"] as const).map((l) => (
                    <button key={l} type="button" aria-pressed={summaryLang === l} onClick={() => setSummaryLang(l)}
                      className={`min-h-12 rounded-xl px-3 font-semibold ${summaryLang === l ? "bg-primary-600 text-white" : "bg-white/80 text-ink-900"}`}>
                      {l === "en" ? "English" : "ಕನ್ನಡ"}
                    </button>
                  ))}
                </div>
              </div>
              <pre lang={summaryLang} className="mt-3 whitespace-pre-wrap rounded-2xl bg-lavender-100 p-3 font-sans text-base text-ink-900">
                {summaryLang === "kn" ? detail.summary_kn : detail.summary_en}
              </pre>
              <p className="mt-2 text-sm text-ink-600">
                {t("counsellor.status")}: <strong className="text-ink-900">{detail.status}</strong>
                {detail.assigned_to && ` · ${detail.assigned_to}`}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button icon="hand" variant="secondary" disabled={detail.status !== "pending"} onClick={() => update({ assigned_to: me })}>{t("counsellor.assign")}</Button>
                <Button icon="chat" variant="secondary" disabled={detail.status === "in_progress" || detail.status === "resolved"} onClick={() => update({ status: "in_progress" })}>{t("counsellor.inProgress")}</Button>
                <Button icon="check" disabled={detail.status === "resolved"} onClick={() => update({ status: "resolved" })}>{t("counsellor.resolve")}</Button>
              </div>
            </div>

            <div className="glass p-4">
              <h2 className="mb-2 text-lg font-bold text-ink-900">{t("counsellor.live")}</h2>
              <ul className="max-h-72 space-y-2 overflow-y-auto" aria-live="polite">
                {live.map((m) => (
                  <li key={m.id} className={`rounded-2xl px-3 py-2 ${m.role === "counsellor" ? "ml-8 bg-primary-600 text-white" : "bg-white text-ink-900"}`}>
                    <span className="block text-xs font-semibold opacity-90">{m.role === "counsellor" ? t("escalation.counsellorLabel") : m.speaker}</span>
                    {m.text}
                  </li>
                ))}
              </ul>
              <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); send(); }}>
                <label htmlFor="c-reply" className="sr-only">{t("counsellor.reply")}</label>
                <input id="c-reply" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={t("counsellor.reply")}
                  className="min-h-12 flex-1 rounded-2xl border border-lavender-200 bg-white px-4 text-base text-ink-900" />
                <Button type="submit" icon="send" disabled={!draft.trim() || detail.status === "resolved"}>{t("counsellor.send")}</Button>
              </form>
            </div>

            <div className="glass p-4">
              <h2 className="mb-2 text-lg font-bold text-ink-900">{t("counsellor.transcript")}</h2>
              <ol className="space-y-3">
                {detail.transcript.map((m) => (
                  <li key={m.id} className="rounded-2xl bg-white/80 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-ink-600">
                      {m.role === "assistant" ? "SAMVAAD" : m.speaker}
                      {m.concern_category && ` · ${m.concern_category}`}
                      {m.sentiment != null && ` · sentiment ${m.sentiment > 0 ? "+" : ""}${m.sentiment}`}
                      {m.guardrail_status && m.guardrail_status !== "na" && ` · guardrail ${m.guardrail_status}`}
                    </p>
                    <p className="mt-1 text-base text-ink-900">{m.text}</p>
                    {m.cards.length > 0 && (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-sm font-semibold text-primary-700">{m.cards.length} card(s)</summary>
                        <div className="mt-2 space-y-2">{m.cards.map((c, i) => <CardView key={i} card={c} />)}</div>
                      </details>
                    )}
                  </li>
                ))}
              </ol>
            </div>
          </>
        )}
      </div>
    </section>
  );
}

export default function Counsellor() {
  const { t } = useTranslation();
  return (
    <PinGate
      storageKey="samvaad.counsellorPin"
      title={t("counsellor.title")}
      label={t("counsellor.pin")}
      submit={t("counsellor.login")}
      verify={async (pin) => { await api.counsellor.queue(pin); }}
    >
      {(pin, logout) => <Console pin={pin} logout={logout} />}
    </PinGate>
  );
}
