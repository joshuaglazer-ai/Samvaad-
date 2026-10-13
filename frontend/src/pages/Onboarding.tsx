import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Button from "../components/ui/Button";
import IconCard from "../components/ui/IconCard";
import Icon from "../components/ui/Icon";
import ProgressDots from "../components/ui/ProgressDots";
import LanguagePicker from "../components/ui/LanguagePicker";
import Toggle from "../components/ui/Toggle";
import ReadAloud, { VoiceMissingNotice } from "../components/ui/ReadAloud";
import { api } from "../lib/api";
import { useAppState, type ParticipationMode } from "../lib/state";
import { useSpeak } from "../lib/useSpeak";

const SkyScene = lazy(() => import("../components/three/SkyScene"));

const DISTRICTS = ["Bengaluru Urban", "Mysuru", "Kalaburagi", "Dharwad"];
const EDUCATION: [string, string][] = [
  ["class_8", "learner"], ["class_10", "learner"], ["class_12", "learner"], ["iti", "gear"],
  ["diploma", "graduation"], ["graduate", "graduation"], ["other", "help"],
];
const INTERESTS: [string, string][] = [
  ["machines", "gear"], ["helping", "heart"], ["electricity", "bolt"], ["vehicles", "car"],
  ["nature_solar", "sun"], ["computers", "cpu"],
];
export const CONCERN_ICONS: Record<string, string> = {
  income: "rupee", job_security: "briefcase", social_status: "users", safety: "shield", cost: "wallet",
  distance_migration: "route", degree_first: "graduation", other: "help",
};
const DEFAULT_INCOME = ["<1.5L", "1.5-3L", "3-6L", ">6L", "prefer_not_to_say"];

type StepKey = "language" | "consent" | "mode" | "district" | "education" | "interests" | "concerns" | "income" | "helper";
const STEPS: StepKey[] = ["language", "consent", "mode", "district", "education", "interests", "concerns", "income", "helper"];
const MODES: [ParticipationMode, string][] = [["together", "users"], ["two_devices", "phone"], ["learner_only", "learner"]];

export default function Onboarding() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { profile, setProfile, setSessionId, readAloud, setReadAloud, lite } = useAppState();
  const { speak, stop, speakingId, missingVoice } = useSpeak();
  const [step, setStep] = useState(0);
  const [consent, setConsent] = useState(false);
  const [incomeBands, setIncomeBands] = useState<string[]>(DEFAULT_INCOME);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const key = STEPS[step];

  useEffect(() => {
    api.config().then((c) => setIncomeBands(c.income_brackets)).catch(() => undefined);
  }, []);

  const question = useMemo(() => {
    switch (key) {
      case "language": return t("onboarding.language");
      case "consent": return `${t("consent.title")}. ${t("consent.text")}`;
      case "mode": return t("mode.question");
      case "district": return t("onboarding.district");
      case "education": return t("onboarding.education");
      case "interests": return t("onboarding.interests");
      case "concerns": return t("onboarding.concerns");
      case "income": return t("onboarding.income");
      case "helper": return t("onboarding.helper");
    }
  }, [key, t]);

  // Every screen reads its question aloud (toggleable).
  useEffect(() => {
    if (readAloud) speak(question, `q-${key}`);
    return () => stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, i18n.language, readAloud]);

  const canNext = (() => {
    switch (key) {
      case "consent": return consent;
      case "district": return !!profile.district;
      case "education": return !!profile.learner_education;
      case "interests": return profile.learner_interests.length > 0;
      case "concerns": return profile.top_concerns.length > 0;
      default: return true;
    }
  })();

  const toggleIn = (list: string[], v: string) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  const finish = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const { session_id, family_code } = await api.createSession({
        language: profile.language,
        district: profile.district!,
        learner_education: profile.learner_education!,
        learner_interests: profile.learner_interests,
        top_concerns: profile.top_concerns,
        income_bracket: profile.income_bracket ?? null,
        helper_mode: profile.helper_mode,
        consent_given: consent,
        participation_mode: profile.participation_mode,
      });
      setProfile({ role: "learner", family_code });
      setSessionId(session_id);
      navigate("/alignment");
    } catch {
      setError(t("app.offline"));
    } finally {
      setSubmitting(false);
    }
  };

  const next = () => (step === STEPS.length - 1 ? finish() : setStep(step + 1));
  const autoNext = () => window.setTimeout(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), profile.helper_mode ? 700 : 250);

  return (
    <>
      {!lite && (
        <Suspense fallback={null}>
          <SkyScene variant="onboarding" />
        </Suspense>
      )}
      <section className="relative z-10 mt-2">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <ProgressDots step={step} total={STEPS.length} />
          <Toggle checked={readAloud} onChange={setReadAloud} label={t("onboarding.readAloud")} icon="speaker" />
        </div>

        <div className="glass p-5">
          <div className="flex items-start justify-between gap-3">
            <h1 className={`text-2xl font-bold text-ink-900 ${speakingId === `q-${key}` ? "reading-highlight" : ""}`}>
              {key === "consent" ? t("consent.title") : question}
            </h1>
            <ReadAloud speaking={speakingId === `q-${key}`} onSpeak={() => speak(question, `q-${key}`)} onStop={stop} compact />
          </div>
          {missingVoice && <VoiceMissingNotice />}
          {key === "interests" && <p className="mt-1 text-ink-600">{t("onboarding.interestsHint")}</p>}
          {key === "concerns" && <p className="mt-1 text-ink-600">{t("onboarding.concernsHint")}</p>}
          {key === "income" && <p className="mt-1 text-ink-600">{t("onboarding.incomeHint")}</p>}
          {profile.helper_mode && <p className="mt-2 rounded-xl bg-lavender-100 px-3 py-2 text-sm text-ink-900">{t("chat.helperTip")}</p>}

          <div className="mt-5">
            {key === "language" && (
              <LanguagePicker value={profile.language} label={question}
                onChange={(lng) => { i18n.changeLanguage(lng); setProfile({ language: lng }); autoNext(); }} />
            )}

            {key === "consent" && (
              <div>
                <p className="flex items-start gap-3 text-lg text-ink-900">
                  <Icon name="lock" className="mt-1 shrink-0 text-primary-700" />
                  {t("consent.text")}
                </p>
                <p className="mt-3 text-base text-ink-600">{t("app.disclaimer")}</p>
                <Button className="mt-5 w-full" size="lg" icon="check" onClick={() => { setConsent(true); setStep(step + 1); }}>
                  {t("consent.agree")}
                </Button>
              </div>
            )}

            {key === "mode" && (
              <div className="grid gap-3" role="radiogroup" aria-label={question}>
                {MODES.map(([mode, icon]) => (
                  <IconCard key={mode} icon={icon} label={t(`mode.${mode}`)} description={t(`mode.${mode}Desc`)}
                    selected={profile.participation_mode === mode} onClick={() => { setProfile({ participation_mode: mode }); autoNext(); }} />
                ))}
              </div>
            )}

            {key === "district" && (
              <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label={question}>
                {DISTRICTS.map((d) => (
                  <IconCard key={d} icon="pin" label={t(`districts.${d}`)} selected={profile.district === d}
                    onClick={() => { setProfile({ district: d }); autoNext(); }} />
                ))}
              </div>
            )}

            {key === "education" && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3" role="radiogroup" aria-label={question}>
                {EDUCATION.map(([e, icon]) => (
                  <IconCard key={e} icon={icon} label={t(`education.${e}`)} selected={profile.learner_education === e}
                    onClick={() => { setProfile({ learner_education: e }); autoNext(); }} />
                ))}
              </div>
            )}

            {key === "interests" && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3" role="group" aria-label={question}>
                {INTERESTS.map(([v, icon]) => (
                  <IconCard key={v} role="checkbox" icon={icon} label={t(`interests.${v}`)} selected={profile.learner_interests.includes(v)}
                    onClick={() => setProfile({ learner_interests: toggleIn(profile.learner_interests, v) })} />
                ))}
              </div>
            )}

            {key === "concerns" && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4" role="group" aria-label={question}>
                {Object.keys(CONCERN_ICONS).map((c) => (
                  <IconCard key={c} role="checkbox" icon={CONCERN_ICONS[c]} label={t(`concerns.${c}`)} selected={profile.top_concerns.includes(c)}
                    onClick={() => setProfile({ top_concerns: toggleIn(profile.top_concerns, c) })} />
                ))}
              </div>
            )}

            {key === "income" && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3" role="radiogroup" aria-label={question}>
                {incomeBands.map((b) => (
                  <IconCard key={b} icon={b === "prefer_not_to_say" ? "lock" : "wallet"} label={t(`income.${b}`, b)}
                    selected={profile.income_bracket === b} onClick={() => { setProfile({ income_bracket: b }); autoNext(); }} />
                ))}
              </div>
            )}

            {key === "helper" && (
              <div>
                <div className="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label={question}>
                  <IconCard icon="helper" label={t("onboarding.helperYes")} selected={profile.helper_mode}
                    onClick={() => setProfile({ helper_mode: true })} />
                  <IconCard icon="users" label={t("onboarding.helperNo")} selected={!profile.helper_mode}
                    onClick={() => setProfile({ helper_mode: false })} />
                </div>
                <p className="mt-3 text-ink-600">{t("onboarding.helperDesc")}</p>
              </div>
            )}
          </div>

          {error && <p role="alert" className="mt-4 rounded-xl bg-danger-600/10 px-3 py-2 text-danger-600">{error}</p>}

          {key !== "consent" && (
            <div className="mt-6 flex items-center justify-between gap-3">
              <Button variant="secondary" icon="arrowLeft" onClick={() => (step === 0 ? navigate("/") : setStep(step - 1))}>
                {t("app.back")}
              </Button>
              <div className="flex gap-2">
                {key === "income" && !profile.income_bracket && (
                  <Button variant="ghost" onClick={() => { setProfile({ income_bracket: null }); setStep(step + 1); }}>{t("app.skip")}</Button>
                )}
                <Button iconRight={step === STEPS.length - 1 ? "check" : "arrowRight"} disabled={!canNext || submitting} onClick={next}>
                  {step === STEPS.length - 1 ? t("onboarding.finish") : t("app.next")}
                </Button>
              </div>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
