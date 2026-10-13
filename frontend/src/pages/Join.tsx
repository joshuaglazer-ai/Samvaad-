import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Button from "../components/ui/Button";
import Icon from "../components/ui/Icon";
import { api } from "../lib/api";
import { useAppState } from "../lib/state";
import LanguagePicker from "../components/ui/LanguagePicker";
import { asLang, type Lang } from "../lib/languages";


/** A parent joins the learner's session on their own phone: 4-digit code (big keypad, no typing) + own language. */
export default function Join() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { setSessionId, setProfile, reset } = useAppState();
  const [code, setCode] = useState((params.get("code") ?? "").replace(/\D/g, "").slice(0, 4));
  const [lang, setLang] = useState<Lang>(asLang(i18n.language));
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  const press = (d: string) => setCode((c) => (c.length < 4 ? c + d : c));
  const join = async () => {
    setBusy(true);
    setError(false);
    try {
      const r = await api.join(code, lang);
      reset();
      i18n.changeLanguage(lang);
      setProfile({ language: lang, role: "parent", participation_mode: "two_devices", district: r.district,
        learner_education: r.learner_education });
      setSessionId(r.session_id);
      navigate("/alignment");
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="glass mt-2 space-y-5 p-5">
      <h1 className="flex items-center gap-2 text-2xl font-bold text-ink-900"><Icon name="parent" className="text-primary-700" />{t("family.joinTitle")}</h1>

      <div>
        <p className="mb-2 text-lg font-semibold text-ink-900">{t("family.chooseLang")}</p>
        <LanguagePicker value={lang} label={t("family.chooseLang")} onChange={(l) => { setLang(l); i18n.changeLanguage(l); }} />
      </div>

      <div>
        <p className="mb-2 text-lg font-semibold text-ink-900" id="code-label">{t("family.enterCode")}</p>
        <p className="mb-3 text-center font-mono text-5xl font-extrabold tracking-[0.4em] text-ink-900" aria-labelledby="code-label" aria-live="polite">
          {code.padEnd(4, "·")}
        </p>
        <div className="mx-auto grid max-w-xs grid-cols-3 gap-2">
          {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((d) => (
            <button key={d} type="button" onClick={() => press(d)} className="min-h-14 rounded-2xl border border-lavender-200 bg-white text-2xl font-bold text-ink-900">{d}</button>
          ))}
          <button type="button" onClick={() => setCode((c) => c.slice(0, -1))} className="flex min-h-14 items-center justify-center gap-1 rounded-2xl text-base font-semibold text-primary-700">
            <Icon name="arrowLeft" size={20} />{t("family.delete")}
          </button>
          <button type="button" onClick={() => press("0")} className="min-h-14 rounded-2xl border border-lavender-200 bg-white text-2xl font-bold text-ink-900">0</button>
        </div>
      </div>

      {error && <p role="alert" className="text-center text-danger-600">{t("family.badCode")}</p>}
      <Button size="lg" icon="check" className="w-full" disabled={code.length !== 4 || busy} onClick={join}>{t("family.join")}</Button>
    </section>
  );
}
