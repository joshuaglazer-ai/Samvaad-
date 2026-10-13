import { useTranslation } from "react-i18next";

export default function Footer() {
  const { t } = useTranslation();
  return (
    <footer className="relative z-10 px-4 py-5 text-center text-sm text-ink-600">
      <p>{t("app.disclaimer")}</p>
      <p className="mt-1 text-xs">SIH 2026 · SIH26241 · MSDE</p>
      <p className="mt-1 text-xs">{t("app.starCredit")}</p>
    </footer>
  );
}
