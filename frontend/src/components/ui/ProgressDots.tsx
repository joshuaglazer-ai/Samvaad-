import { useTranslation } from "react-i18next";

export default function ProgressDots({ step, total }: { step: number; total: number }) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-3" aria-label={t("onboarding.progress", { n: step + 1, total })}>
      <div className="flex gap-1.5" aria-hidden="true">
        {Array.from({ length: total }, (_, i) => (
          <span
            key={i}
            className={`h-2.5 rounded-full transition-all ${i === step ? "w-7 bg-primary-600" : i < step ? "w-2.5 bg-star-400" : "w-2.5 bg-lavender-200"}`}
          />
        ))}
      </div>
      <span className="text-sm text-ink-600">{t("onboarding.progress", { n: step + 1, total })}</span>
    </div>
  );
}
