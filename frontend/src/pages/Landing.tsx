import { lazy, Suspense } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { m } from "framer-motion";
import Icon from "../components/ui/Icon";
import { useAppState } from "../lib/state";
import LanguagePicker from "../components/ui/LanguagePicker";
import { asLang, type Lang } from "../lib/languages";

const SkyScene = lazy(() => import("../components/three/SkyScene"));

export default function Landing() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { lite, reset, setProfile } = useAppState();

  const chooseLang = (lng: Lang) => {
    i18n.changeLanguage(lng);
    setProfile({ language: lng });
  };
  const start = () => {
    reset();
    setProfile({ language: asLang(i18n.language) });
    navigate("/start");
  };

  return (
    <>
      {!lite && (
        <Suspense fallback={null}>
          <SkyScene variant="landing" />
        </Suspense>
      )}
      <section className="relative z-10 flex min-h-[78vh] flex-col items-center justify-center pt-6 text-center">
        <m.h1
          initial={lite ? false : { opacity: 0, y: 12, letterSpacing: "0.4em" }}
          animate={{ opacity: 1, y: 0, letterSpacing: "0.16em" }}
          transition={{ duration: 0.9 }}
          className="bg-gradient-to-br from-primary-700 via-primary-600 to-ink-900 bg-clip-text text-5xl font-extrabold text-transparent sm:text-7xl"
        >
          SAMVAAD
        </m.h1>
        <p lang="kn" className="mt-1 text-xl font-semibold text-primary-700">ಸಂವಾದ</p>
        <p className="mt-3 text-xl font-semibold text-ink-900 sm:text-2xl">{t("app.tagline")}</p>
        <p className="mt-3 max-w-xl text-lg text-ink-600">{t("landing.greeting")}</p>

        <m.button
          type="button"
          onClick={start}
          whileHover={lite ? undefined : { scale: 1.03 }}
          whileTap={{ scale: 0.98 }}
          className="mt-8 flex min-h-16 flex-col items-center justify-center rounded-3xl bg-primary-600 px-10 py-3 text-white shadow-[var(--shadow-soft)] hover:bg-primary-700"
        >
          <span className="flex items-center gap-2 text-xl font-bold">
            <Icon name="users" size={26} />
            {t("landing.start")}
          </span>
          <span className="text-base opacity-95" lang={i18n.language === "en" ? "kn" : "en"}>{t("landing.startAlt")}</span>
        </m.button>

        <div className="mt-6" role="group" aria-label={t("landing.chooseLanguage")}>
          <p className="mb-2 text-sm font-semibold text-ink-600">{t("landing.chooseLanguage")}</p>
          <div className="mx-auto w-full max-w-md">
            <LanguagePicker variant="compact" value={asLang(i18n.language)} onChange={chooseLang} label={t("landing.chooseLanguage")} />
          </div>
        </div>

        <ul className="mt-10 grid w-full max-w-2xl gap-3 sm:grid-cols-3">
          {[
            ["users", t("landing.point1")],
            ["shield", t("landing.point2")],
            ["mic", t("landing.point3")],
          ].map(([icon, label], i) => (
            <m.li
              key={icon}
              initial={lite ? false : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + i * 0.12 }}
              className="glass flex items-center gap-3 p-4 text-left text-base font-medium text-ink-900"
            >
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-lavender-100 text-primary-700">
                <Icon name={icon} />
              </span>
              {label}
            </m.li>
          ))}
        </ul>

        <Link to="/join" className="mt-5 flex min-h-12 items-center gap-2 rounded-2xl px-4 font-semibold text-primary-700 hover:bg-lavender-100">
          <Icon name="phone" size={20} /> {t("family.joinLink")}
        </Link>

        <nav className="mt-6 flex gap-3 text-sm" aria-label="Staff">
          <Link to="/counsellor" className="flex min-h-12 items-center gap-1.5 rounded-xl px-3 font-semibold text-primary-700 hover:bg-lavender-100">
            <Icon name="chat" size={18} /> {t("landing.counsellor")}
          </Link>
          <Link to="/admin" className="flex min-h-12 items-center gap-1.5 rounded-xl px-3 font-semibold text-primary-700 hover:bg-lavender-100">
            <Icon name="chart" size={18} /> {t("landing.admin")}
          </Link>
        </nav>
      </section>
    </>
  );
}
