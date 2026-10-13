import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Button from "../ui/Button";
import IconCard from "../ui/IconCard";
import Icon from "../ui/Icon";
import ReadAloud from "../ui/ReadAloud";
import MicButton from "../chat/MicButton";
import { api, type GoalDraft, type MatchCandidate, type MatchResult, type Sector, type Suggestion, type Trade } from "../../lib/api";
import { asLang } from "../../lib/languages";
import { useAppState } from "../../lib/state";
import { useSpeak } from "../../lib/useSpeak";

type Who = "learner" | "parent";
type View = "choose" | "say" | "browse" | "quiz" | "results" | "confirm";

const TRAITS: [string, string][] = [["hands", "hand"], ["people", "users"], ["machines", "gear"], ["outdoors", "sun"], ["computers", "cpu"]];

/** Search all four languages' names and everyday words, so "bijli", "ಸೋಲಾರ್" or "mechanic" all find a trade. */
export function searchTrades(trades: Trade[], query: string): Trade[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return trades.filter((t) => [
    ...Object.values(t.names ?? {}), ...Object.values(t.synonyms ?? {}).flat(), t.sector_name,
  ].some((w) => (w ?? "").toLowerCase().includes(q)));
}

interface Pending {
  text: string | null;
  source: GoalDraft["source"];
  candidates: MatchCandidate[];
  match?: MatchResult;
}

interface Props {
  who: Who;
  district?: string;
  onDone: (goal: GoalDraft) => void;
  /** Shown as a secondary action on the first screen (e.g. the parent may skip). */
  onSkip?: () => void;
  skipLabel?: string;
}

/**
 * "What would you like to do or become?" — three equal ways to answer: say/type it, browse ideas, or "Not sure yet".
 * Then show what the app understood and let the family confirm. Trades come only from the API.
 */
export default function GoalPicker({ who, district, onDone, onSkip, skipLabel }: Props) {
  const { t, i18n } = useTranslation();
  const lang = asLang(i18n.language);
  const { sessionId, readAloud } = useAppState();
  const { speak, stop, speakingId } = useSpeak();
  const [view, setView] = useState<View>("choose");
  const [text, setText] = useState("");
  const [voiceUsed, setVoiceUsed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sectors, setSectors] = useState<Sector[]>([]);
  const [allTrades, setAllTrades] = useState<Trade[]>([]);
  const [sector, setSector] = useState<Sector | null>(null);
  const [sectorTrades, setSectorTrades] = useState<Trade[]>([]);
  const [query, setQuery] = useState("");
  const [quizStep, setQuizStep] = useState(0);
  const [likes, setLikes] = useState<string[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [pending, setPending] = useState<Pending | null>(null);
  const [chosen, setChosen] = useState<string | null>(null);

  const track = (option: string) =>
    api.event({ session_id: sessionId, event_type: "goal_option_chosen", payload: { who, option } }).catch(() => undefined);

  // Catalogue for Browse, in the current language.
  useEffect(() => {
    if (view !== "browse") return;
    api.sectors(lang).then(setSectors).catch(() => setError(t("app.offline")));
    api.trades(lang).then(setAllTrades).catch(() => undefined);
  }, [view, lang, t]);
  useEffect(() => {
    if (!sector) return setSectorTrades([]);
    api.trades(lang, sector.slug).then(setSectorTrades).catch(() => setError(t("app.offline")));
  }, [sector, lang, t]);

  const quizQuestion = quizStep < TRAITS.length ? t(`goal.q_${TRAITS[quizStep][0]}`) : t("goal.q_place");
  useEffect(() => {
    if (view === "quiz" && readAloud) speak(quizQuestion, `quiz-${quizStep}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, quizStep, readAloud]);

  const confirmWith = (p: Pending) => {
    setPending(p);
    setChosen(p.candidates[0]?.slug ?? null);
    setView("confirm");
  };

  const checkText = async () => {
    const said = text.trim();
    if (!said) return;
    setBusy(true);
    setError(null);
    try {
      const match = await api.matchAspiration(said, lang);
      confirmWith({ text: said, source: voiceUsed ? "voice" : "text", candidates: match.candidates, match });
    } catch {
      setError(t("app.offline"));
    } finally {
      setBusy(false);
    }
  };

  const pickTrade = (tr: { slug: string; name: string; sector: string }, source: "browse" | "quiz") =>
    confirmWith({ text: tr.name, source, candidates: [{ ...tr, score: 1, reason: "" }] });

  const answerQuiz = (yes: boolean) => {
    const trait = TRAITS[quizStep][0];
    setLikes((l) => (yes ? [...l.filter((x) => x !== trait), trait] : l.filter((x) => x !== trait)));
    setQuizStep((s) => s + 1);
  };
  const answerPlace = async (nearHome: boolean) => {
    setBusy(true);
    setError(null);
    try {
      const r = await api.suggestTrades({ likes, near_home: nearHome, district, language: lang });
      setSuggestions(r.suggestions);
      setView("results");
    } catch {
      setError(t("app.offline"));
    } finally {
      setBusy(false);
    }
  };

  const finish = (selected: string[]) => {
    if (!pending) return;
    const pick = pending.candidates.find((c) => c.slug === selected[0]);
    onDone({
      text: pending.text, language: lang, source: pending.source, selected_slugs: selected, confirmed: true,
      label: pick?.name ?? pending.text ?? "",
    });
  };

  const results = useMemo(() => searchTrades(allTrades, query), [allTrades, query]);
  // Always back to the three options (the page's own Back button leaves this question).
  const back = () => (
    <Button variant="ghost" icon="arrowLeft" onClick={() => { setError(null); setView("choose"); }}>{t("goal.otherWays")}</Button>
  );

  return (
    <div className="space-y-4" data-testid={`goal-${who}`}>
      {view === "choose" && (
        <>
          <div className="grid gap-3 sm:grid-cols-3" role="radiogroup" aria-label={who === "parent" ? t("goal.parentQuestion") : t("goal.question")}>
            <IconCard icon="mic" label={t("goal.say")} description={t("goal.sayDesc")} onClick={() => { track("say"); setView("say"); }} />
            <IconCard icon="search" label={t("goal.browse")} description={t("goal.browseDesc")} onClick={() => { track("browse"); setSector(null); setQuery(""); setView("browse"); }} />
            <IconCard icon="question" label={t("goal.notSure")} description={t("goal.notSureDesc")}
              onClick={() => { track("quiz"); setQuizStep(0); setLikes([]); setView("quiz"); }} />
          </div>
          {onSkip && <Button variant="ghost" onClick={onSkip}>{skipLabel ?? t("goal.skipHope")}</Button>}
        </>
      )}

      {view === "say" && (
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); checkText(); }}>
          <label htmlFor={`goal-text-${who}`} className="block text-lg font-semibold text-ink-900">{t("goal.inputLabel")}</label>
          <textarea id={`goal-text-${who}`} rows={2} maxLength={300} value={text} placeholder={t("goal.placeholder")}
            onChange={(e) => { setText(e.target.value); setVoiceUsed(false); }}
            className="w-full rounded-2xl border-2 border-lavender-200 bg-white px-4 py-3 text-lg text-ink-900 focus:border-primary-600" />
          <div className="flex flex-wrap items-start justify-between gap-3">
            <MicButton lang={lang} highlight={who === "parent"} onResult={(said) => { setText(said); setVoiceUsed(true); }} />
            <Button type="submit" iconRight="arrowRight" disabled={!text.trim() || busy}>{busy ? t("goal.thinking") : t("goal.check")}</Button>
          </div>
          {back()}
        </form>
      )}

      {view === "browse" && (
        <div className="space-y-3">
          <label className="flex items-center gap-2 rounded-2xl border-2 border-lavender-200 bg-white px-3">
            <Icon name="search" className="shrink-0 text-primary-700" />
            <span className="sr-only">{t("goal.searchLabel")}</span>
            <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("goal.searchPlaceholder")}
              className="min-h-12 w-full bg-transparent text-lg text-ink-900 outline-none" />
          </label>
          {query.trim() ? (
            results.length ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {results.map((tr) => <IconCard key={tr.slug} icon={tr.icon} label={tr.name} description={tr.sector_name} onClick={() => pickTrade(tr, "browse")} />)}
              </div>
            ) : <p className="text-ink-600">{t("goal.noResults")}</p>
          ) : sector ? (
            <>
              <Button variant="ghost" icon="arrowLeft" onClick={() => setSector(null)}>{t("goal.allSectors")}</Button>
              <h2 className="text-xl font-bold text-ink-900">{sector.name}</h2>
              <div className="grid gap-3 sm:grid-cols-2">
                {sectorTrades.map((tr) => <IconCard key={tr.slug} icon={tr.icon} label={tr.name} onClick={() => pickTrade(tr, "browse")} />)}
              </div>
            </>
          ) : (
            <>
              <h2 className="text-xl font-bold text-ink-900">{t("goal.sectorsTitle")}</h2>
              <div className="grid grid-cols-2 gap-3">
                {sectors.map((s) => <IconCard key={s.slug} icon={s.icon} label={s.name} onClick={() => setSector(s)} />)}
              </div>
            </>
          )}
          {back()}
        </div>
      )}

      {view === "quiz" && (
        <div className="space-y-3">
          <p className="text-sm font-semibold text-ink-600">{t("goal.quizStep", { n: Math.min(quizStep + 1, TRAITS.length + 1), total: TRAITS.length + 1 })}</p>
          <div className="flex items-start justify-between gap-3">
            <h2 className={`text-xl font-bold text-ink-900 ${speakingId === `quiz-${quizStep}` ? "reading-highlight" : ""}`}>{quizQuestion}</h2>
            <ReadAloud speaking={speakingId === `quiz-${quizStep}`} onSpeak={() => speak(quizQuestion, `quiz-${quizStep}`)} onStop={stop} compact />
          </div>
          {quizStep < TRAITS.length ? (
            <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label={quizQuestion}>
              <IconCard icon={TRAITS[quizStep][1]} label={t("goal.yes")} onClick={() => answerQuiz(true)} />
              <IconCard icon="close" label={t("goal.notReally")} onClick={() => answerQuiz(false)} />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label={quizQuestion}>
              <IconCard icon="home" label={t("goal.nearHome")} onClick={() => answerPlace(true)} />
              <IconCard icon="route" label={t("goal.openToMove")} onClick={() => answerPlace(false)} />
            </div>
          )}
          {back()}
        </div>
      )}

      {view === "results" && (
        <div className="space-y-3">
          <h2 className="text-xl font-bold text-ink-900">{t("goal.suggestionsTitle")}</h2>
          <p className="flex items-start gap-2 rounded-xl bg-lavender-100 px-3 py-2 text-ink-900">
            <Icon name="info" className="mt-0.5 shrink-0 text-primary-700" size={20} />{t("goal.suggestionsNote")}
          </p>
          {suggestions.length ? (
            <div className="grid gap-3 sm:grid-cols-3">
              {suggestions.map((s) => <IconCard key={s.slug} icon={s.icon} label={s.name} description={s.reason} onClick={() => pickTrade(s, "quiz")} />)}
            </div>
          ) : <p className="text-ink-600">{t("goal.noSuggestions")}</p>}
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" icon="search" onClick={() => setView("browse")}>{t("goal.browse")}</Button>
            <Button variant="ghost" onClick={() => onDone({ text: null, language: lang, source: "quiz", selected_slugs: [], confirmed: false, label: "" })}>
              {t("goal.decideLater")}
            </Button>
          </div>
        </div>
      )}

      {view === "confirm" && pending && (
        <div className="space-y-4" aria-live="polite">
          <p className="text-lg text-ink-900">
            {who === "parent" ? t("goal.understoodParent") : t("goal.understoodLearner")}{" "}
            <strong data-testid="goal-understood">{pending.text}</strong>
          </p>
          {pending.candidates.length > 0 ? (
            <>
              {(pending.source === "text" || pending.source === "voice") && <p className="font-semibold text-ink-900">{t("goal.closest")}</p>}
              {(pending.source === "text" || pending.source === "voice") && (
                <div className="grid gap-3 sm:grid-cols-3" role="radiogroup" aria-label={t("goal.closest")}>
                  {pending.candidates.map((c) => (
                    <IconCard key={c.slug} icon="sparkle" label={c.name} description={c.reason} selected={chosen === c.slug} onClick={() => setChosen(c.slug)} />
                  ))}
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                <Button icon="check" disabled={!chosen} onClick={() => chosen && finish([chosen])}>{t("goal.yesRight")}</Button>
                <Button variant="secondary" icon="search" onClick={() => { setSector(null); setQuery(""); setView("browse"); }}>{t("goal.chooseDifferent")}</Button>
                {(pending.source === "text" || pending.source === "voice") && <Button variant="ghost" onClick={() => finish([])}>{t("goal.noneOfThese")}</Button>}
              </div>
            </>
          ) : (
            <>
              <p className="flex items-start gap-2 rounded-xl bg-lavender-100 px-3 py-2 text-lg text-ink-900">
                <Icon name="heart" className="mt-1 shrink-0 text-primary-700" />
                {pending.match?.category === "degree_career" ? t("goal.degreeMsg") : t("goal.unknownMsg")}
              </p>
              {pending.match?.category === "degree_career" && (pending.match.related?.length ?? 0) > 0 && (
                <p className="text-ink-600">{t("goal.degreeRelated")}</p>
              )}
              <div className="flex flex-wrap gap-2">
                <Button icon="check" onClick={() => finish([])}>{t("goal.saveGoal")}</Button>
                {pending.match?.category === "degree_career" && (pending.match.related?.length ?? 0) > 0 ? (
                  <Button variant="secondary" icon="sparkle" onClick={() => {
                    const rel = sectors.find((s) => s.slug === pending.match?.related_sector);
                    setQuery("");
                    if (rel) setSector(rel);
                    else api.sectors(lang).then((all) => setSector(all.find((s) => s.slug === pending.match?.related_sector) ?? null)).catch(() => undefined);
                    setView("browse");
                  }}>{t("goal.showRelated")}</Button>
                ) : (
                  <Button variant="secondary" icon="search" onClick={() => { setSector(null); setQuery(""); setView("browse"); }}>{t("goal.otherOptions")}</Button>
                )}
              </div>
            </>
          )}
          {back()}
        </div>
      )}

      {error && <p role="alert" className="rounded-xl bg-danger-600/10 px-3 py-2 text-danger-600">{error}</p>}
    </div>
  );
}
