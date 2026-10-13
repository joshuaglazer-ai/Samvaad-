import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Icon from "./Icon";
import { useAppState } from "../../lib/state";
import { api } from "../../lib/api";

export default function Header() {
  const { t, i18n } = useTranslation();
  const { lite, setLite, theme, setTheme, sessionId, profile, setProfile } = useAppState();

  const switchLang = () => {
    const next = i18n.language === "kn" ? "en" : "kn";
    i18n.changeLanguage(next);
    setProfile({ language: next });
    // Switching language keeps the same session. A parent's own phone keeps its own language (each phone's
    // messages carry their language), so only the learner's phone updates the session language.
    if (sessionId && profile.role !== "parent") api.updateSession(sessionId, { language: next }).catch(() => undefined);
  };

  return (
    <header className="relative z-20 mx-auto flex w-full max-w-7xl items-center justify-between gap-1 px-3 py-3 sm:px-4">
      <Link to="/" aria-label="SAMVAAD" className="flex min-h-12 min-w-12 items-center gap-2 rounded-xl font-extrabold tracking-wide text-ink-900">
        <span className="text-star-400"><Icon name="star" size={26} strokeWidth={2.2} /></span>
        {/* Wordmark text hides on very narrow phones so the three header controls always fit. */}
        <span className="hidden text-base min-[420px]:inline sm:text-lg">SAMVAAD</span>
      </Link>
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => setLite(!lite)}
          aria-pressed={lite}
          className={`flex min-h-12 items-center gap-1.5 whitespace-nowrap rounded-2xl border px-2 text-sm font-semibold ${lite ? "border-primary-600 bg-primary-600 text-white" : "border-lavender-200 bg-white/80 text-ink-900"}`}
          title={lite ? t("app.liteOn") : t("app.liteOff")}
        >
          <Icon name="feather" size={20} />
          <span>{t("app.liteMode")}</span>
        </button>
        <button
          type="button"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-pressed={theme === "dark"}
          className="flex min-h-12 items-center gap-1.5 whitespace-nowrap rounded-2xl border border-lavender-200 bg-white/80 px-2 text-sm font-semibold text-ink-900"
          title={theme === "dark" ? t("app.toLight") : t("app.toDark")}
        >
          <Icon name={theme === "dark" ? "sun" : "moon"} size={20} />
          <span>{theme === "dark" ? t("app.light") : t("app.dark")}</span>
        </button>
        <button
          type="button"
          onClick={switchLang}
          className="flex min-h-12 items-center gap-1.5 whitespace-nowrap rounded-2xl border border-lavender-200 bg-white/80 px-2 text-sm font-semibold text-ink-900"
          aria-label={`${t("app.language")}: ${t("app.switchTo")}`}
        >
          <Icon name="globe" size={20} />
          <span lang={i18n.language === "kn" ? "en" : "kn"}>{t("app.switchTo")}</span>
        </button>
      </div>
    </header>
  );
}
