import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Icon from "./Icon";
import { useAppState } from "../../lib/state";
import { api } from "../../lib/api";

export default function Header() {
  const { t, i18n } = useTranslation();
  const { lite, setLite, sessionId, setProfile } = useAppState();

  const switchLang = () => {
    const next = i18n.language === "kn" ? "en" : "kn";
    i18n.changeLanguage(next);
    setProfile({ language: next });
    // Switching language keeps the same session.
    if (sessionId) api.updateSession(sessionId, { language: next }).catch(() => undefined);
  };

  return (
    <header className="relative z-20 mx-auto flex w-full max-w-7xl items-center justify-between gap-2 px-4 py-3">
      <Link to="/" className="flex min-h-12 items-center gap-2 rounded-xl font-extrabold tracking-wide text-ink-900">
        <span className="text-star-400"><Icon name="star" size={26} strokeWidth={2.2} /></span>
        <span className="text-lg">SAMVAAD</span>
      </Link>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setLite(!lite)}
          aria-pressed={lite}
          className={`flex min-h-12 items-center gap-1.5 rounded-2xl border px-3 text-sm font-semibold ${lite ? "border-primary-600 bg-primary-600 text-white" : "border-lavender-200 bg-white/80 text-ink-900"}`}
          title={lite ? t("app.liteOn") : t("app.liteOff")}
        >
          <Icon name="feather" size={20} />
          <span>{t("app.liteMode")}</span>
        </button>
        <button
          type="button"
          onClick={switchLang}
          className="flex min-h-12 items-center gap-1.5 rounded-2xl border border-lavender-200 bg-white/80 px-3 text-sm font-semibold text-ink-900"
          aria-label={`${t("app.language")}: ${t("app.switchTo")}`}
        >
          <Icon name="globe" size={20} />
          <span lang={i18n.language === "kn" ? "en" : "kn"}>{t("app.switchTo")}</span>
        </button>
      </div>
    </header>
  );
}
