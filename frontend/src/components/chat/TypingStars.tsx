import { useTranslation } from "react-i18next";
import { m } from "framer-motion";

/** Typing indicator: three twinkling stars. */
export default function TypingStars() {
  const { t } = useTranslation();
  return (
    <div role="status" className="flex items-center gap-2 rounded-[22px] border border-lavender-200 bg-white/90 px-4 py-3 text-ink-600">
      {[0, 1, 2].map((i) => (
        <m.svg key={i} width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"
          animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.15, 0.8] }}
          transition={{ repeat: Infinity, duration: 1.2, delay: i * 0.2 }}>
          <path d="M12 2.5l2.9 5.9 6.5.9-4.7 4.6 1.1 6.5L12 17.3l-5.8 3.1 1.1-6.5L2.6 9.3l6.5-.9z" className="fill-star-400 stroke-primary-700" strokeWidth="1.2" />
        </m.svg>
      ))}
      <span className="text-sm">{t("chat.thinking")}</span>
    </div>
  );
}
