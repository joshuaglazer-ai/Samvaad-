import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { m } from "framer-motion";
import QRCode from "qrcode";
import Button from "../components/ui/Button";
import IconCard from "../components/ui/IconCard";
import Icon from "../components/ui/Icon";
import ReadAloud from "../components/ui/ReadAloud";
import { api, type AlignmentResult } from "../lib/api";
import { useAppState } from "../lib/state";
import { useSpeak } from "../lib/useSpeak";

export const VALUES: [string, string][] = [
  ["earning_soon", "rupee"], ["near_home", "home"], ["respect", "users"], ["study_further", "graduation"], ["safety", "shield"],
];
type Who = "learner" | "parent";

function finePointer(): boolean {
  try {
    return window.matchMedia("(pointer: fine)").matches;
  } catch {
    return false;
  }
}

/** One person's five cards: tap in order (mobile) or drag ranked cards to swap (desktop). Controlled. */
function RankRow({ who, order, setOrder, disabled }: {
  who: Who; order: string[]; setOrder: (o: string[]) => void; disabled?: boolean;
}) {
  const { t } = useTranslation();
  const [dragging, setDragging] = useState<string | null>(null);
  const desktop = finePointer();
  const tap = (v: string) => setOrder(order.includes(v) ? order.filter((x) => x !== v) : [...order, v]);
  const swap = (a: string, b: string) => {
    const ia = order.indexOf(a), ib = order.indexOf(b);
    if (ia < 0 || ib < 0) return;
    const next = [...order];
    [next[ia], next[ib]] = [next[ib], next[ia]];
    setOrder(next);
  };
  return (
    <section aria-labelledby={`rank-${who}`}>
      <h2 id={`rank-${who}`} className="flex items-center gap-2 text-xl font-bold text-ink-900">
        <Icon name={who === "learner" ? "learner" : "parent"} className="text-primary-700" />
        {t(`alignment.${who}`)}
      </h2>
      {/* Locked while saving so quick taps cannot land on cards that are about to be replaced. */}
      <fieldset disabled={disabled} className="contents">
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3" role="group" aria-label={t(`alignment.${who}`)}>
          {VALUES.map(([v, icon]) => {
            const rank = order.indexOf(v);
            return (
              <div key={v} draggable={desktop && rank >= 0} onDragStart={() => setDragging(v)}
                onDragOver={(e) => e.preventDefault()} onDrop={() => dragging && swap(dragging, v)} onDragEnd={() => setDragging(null)}>
                <IconCard role="checkbox" icon={icon} label={t(`alignment.values.${v}`)} selected={rank >= 0}
                  badge={rank >= 0 ? t("alignment.rank", { n: rank + 1 }) : undefined} onClick={() => tap(v)} />
              </div>
            );
          })}
        </div>
      </fieldset>
      <div className="mt-3 flex items-center justify-between gap-2">
        <p className="text-sm text-ink-600">{order.length}/{VALUES.length}</p>
        <Button variant="ghost" icon="refresh" onClick={() => setOrder([])} disabled={disabled || order.length === 0}>{t("alignment.reset")}</Button>
      </div>
    </section>
  );
}

export function AlignmentMessage({ result }: { result: AlignmentResult }) {
  const { t } = useTranslation();
  const label = (v: string) => t(`alignment.values.${v}`);
  return (
    <div className="space-y-2 text-lg text-ink-900">
      <p className="font-semibold">{t("alignment.bothWantBest")}</p>
      {result.shared_top.map((v) => <p key={v}>★ {t("alignment.sharedTop", { value: label(v) })}</p>)}
      {result.biggest_difference
        ? <p>{t("alignment.different", { value: label(result.biggest_difference) })}</p>
        : result.shared_top.length === 0 ? null : <p>{t("alignment.allSame")}</p>}
    </div>
  );
}

function ResultView({ result }: { result: AlignmentResult }) {
  const { t } = useTranslation();
  return (
    <>
      <AlignmentMessage result={result} />
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {(["learner", "parent"] as const).map((p) => (
          <div key={p} className="rounded-2xl bg-white/80 p-3">
            <p className="mb-1 flex items-center gap-2 font-bold text-ink-900">
              <Icon name={p === "learner" ? "learner" : "parent"} className="text-primary-700" /> {t(`alignment.${p}`)}
            </p>
            <ol className="list-decimal pl-6 text-ink-900">
              {(result[p] ?? []).map((v) => (
                <li key={v} className={v === result.biggest_difference ? "font-bold text-primary-700" : ""}>{t(`alignment.values.${v}`)}</li>
              ))}
            </ol>
          </div>
        ))}
      </div>
    </>
  );
}

/** Shown on the learner's phone in two-phone mode: QR + 4-digit code for the parent's phone. */
export function FamilyCodeCard({ sessionId }: { sessionId: string }) {
  const { t } = useTranslation();
  const { profile, setProfile } = useAppState();
  const [qr, setQr] = useState("");
  const [joined, setJoined] = useState(false);
  const code = profile.family_code;

  useEffect(() => {
    if (!code) api.familyCode(sessionId).then((r) => setProfile({ family_code: r.family_code })).catch(() => undefined);
  }, [code, sessionId, setProfile]);
  useEffect(() => {
    if (!code) return;
    QRCode.toDataURL(`${window.location.origin}/join?code=${code}`, { margin: 1, width: 180, color: { dark: "#000000", light: "#FFFFFF" } })
      .then(setQr).catch(() => undefined);
  }, [code]);
  useEffect(() => {
    const id = window.setInterval(() => api.status(sessionId).then((s) => setJoined(s.parent_joined)).catch(() => undefined), 3000);
    return () => window.clearInterval(id);
  }, [sessionId]);

  return (
    <section className="rounded-2xl border-2 border-primary-600 p-4" aria-live="polite">
      <h2 className="flex items-center gap-2 text-xl font-bold text-ink-900"><Icon name="phone" className="text-primary-700" />{t("family.codeTitle")}</h2>
      <p className="mt-1 text-ink-600">{t("family.codeHelp")}</p>
      <div className="mt-3 flex flex-wrap items-center gap-4">
        {qr && <img src={qr} alt={t("family.codeTitle")} width={140} height={140} className="rounded-xl bg-white p-1" />}
        <p className="font-mono text-5xl font-extrabold tracking-[0.3em] text-ink-900" aria-label={code?.split("").join(" ")} data-testid="family-code">{code ?? "····"}</p>
      </div>
      <p className={`mt-3 flex items-center gap-2 font-semibold ${joined ? "text-success-600" : "text-ink-600"}`}>
        <Icon name={joined ? "check" : "hourglass"} size={20} /> {joined ? t("family.joined") : t("family.waiting")}
      </p>
    </section>
  );
}

export default function Alignment() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { sessionId, profile, lite } = useAppState();
  const { speak, stop, speakingId } = useSpeak();
  const mode = profile.participation_mode;
  const isParentPhone = profile.role === "parent";
  const together = mode === "together" && !isParentPhone;
  const me: Who = isParentPhone ? "parent" : "learner";
  const other: Who | null = mode === "two_devices" ? (isParentPhone ? "learner" : "parent") : null;

  const [learner, setLearner] = useState<string[]>([]);
  const [parent, setParent] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [result, setResult] = useState<AlignmentResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const poll = useRef<number | null>(null);

  useEffect(() => {
    if (!sessionId) navigate("/start");
  }, [sessionId, navigate]);

  // In two-phone mode, wait (politely) for the other person's cards.
  useEffect(() => {
    if (!saved || !other || !sessionId || result?.complete) return;
    poll.current = window.setInterval(() => {
      api.getAlignment(sessionId).then((r) => r.complete && setResult(r)).catch(() => undefined);
    }, 3000);
    return () => {
      if (poll.current) window.clearInterval(poll.current);
    };
  }, [saved, other, sessionId, result]);

  const save = async () => {
    if (!sessionId) return;
    setSaving(true);
    setError(null);
    try {
      let r: AlignmentResult;
      if (together) {
        await api.saveAlignment(sessionId, { respondent: "learner", ranking: learner });
        r = await api.saveAlignment(sessionId, { respondent: "parent", ranking: parent });
      } else {
        r = await api.saveAlignment(sessionId, { respondent: me, ranking: me === "learner" ? learner : parent });
      }
      setSaved(true);
      if (r.complete) setResult(r);
    } catch {
      setError(t("app.offline"));
    } finally {
      setSaving(false);
    }
  };

  const ready = together ? learner.length === 5 && parent.length === 5 : (me === "learner" ? learner : parent).length === 5;
  const intro = together ? `${t("alignment.intro")} ${t("family.sitTogether")}` : t("alignment.intro");
  const next = () => navigate("/mood/pre");

  return (
    <section className="mt-2">
      <div className="glass space-y-5 p-5">
        <div className="flex items-start justify-between gap-3">
          <h1 className="text-2xl font-bold text-ink-900">{result ? t("alignment.resultTitle") : t("alignment.title")}</h1>
          <ReadAloud speaking={speakingId === "align"} onStop={stop} onSpeak={() => speak(`${t("alignment.title")} ${intro}`, "align")} compact />
        </div>

        {mode === "two_devices" && !isParentPhone && sessionId && !result && <FamilyCodeCard sessionId={sessionId} />}

        {!saved && (
          <>
            <p className="flex items-start gap-2 text-lg text-ink-600">
              {together && <Icon name="users" className="mt-1 shrink-0 text-primary-700" />}
              {intro}
            </p>
            <p className="text-sm text-ink-600">{finePointer() ? t("alignment.dragHint") : t("alignment.tapHint")}</p>
            <div className={together ? "grid gap-6 lg:grid-cols-2" : ""}>
              {(together || me === "learner") && <RankRow who="learner" order={learner} setOrder={setLearner} disabled={saving} />}
              {(together || me === "parent") && <RankRow who="parent" order={parent} setOrder={setParent} disabled={saving} />}
            </div>
            {error && <p role="alert" className="text-danger-600">{error}</p>}
            <Button size="lg" icon="check" className="w-full" disabled={!ready || saving} onClick={save}>
              {together ? t("family.saveBoth") : t("alignment.save")}
            </Button>
          </>
        )}

        {saved && !result && other && (
          <div className="space-y-3" aria-live="polite">
            <p className="flex items-center gap-2 text-lg text-ink-900"><Icon name="hourglass" className="text-primary-700" />{t("family.waitingCards")}</p>
            <Button variant="secondary" iconRight="arrowRight" onClick={next}>{t("family.continueAlone")}</Button>
          </div>
        )}

        {saved && !result && mode === "learner_only" && (
          <div className="space-y-4">
            <p className="flex items-start gap-2 rounded-xl bg-lavender-100 px-3 py-2 text-lg text-ink-900">
              <Icon name="share" className="mt-1 shrink-0 text-primary-700" />{t("family.learnerOnlyNote")}
            </p>
            <Button size="lg" className="w-full" iconRight="arrowRight" onClick={next}>{t("alignment.continue")}</Button>
          </div>
        )}

        {result && (
          <m.div initial={lite ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <ResultView result={result} />
            <Button className="mt-6 w-full" size="lg" iconRight="arrowRight" onClick={next}>{t("alignment.continue")}</Button>
          </m.div>
        )}
      </div>
    </section>
  );
}
