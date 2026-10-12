import { useTranslation } from "react-i18next";
import { m } from "framer-motion";
import Icon from "../ui/Icon";
import EvidenceBadge from "./EvidenceBadge";
import { UnavailableCard } from "./OutcomeCard";
import type { Card, LadderStep } from "../../lib/api";
import { useAppState } from "../../lib/state";

const KIND_ICON: Record<string, string> = {
  job: "briefcase", upskill: "sparkle", apprenticeship: "users", diploma: "graduation", degree: "graduation",
};
const STAR = "M12 2.5l2.9 5.9 6.5.9-4.7 4.6 1.1 6.5L12 17.3l-5.8 3.1 1.1-6.5L2.6 9.3l6.5-.9z";
// Zig-zag x position (in %) of each star inside the 56px constellation column.
const xOf = (i: number) => (i % 2 === 0 ? 30 : 70);

/** Career ladder drawn as a rising constellation: step 1 at the bottom, each step a star joined to the next.
 * Steps the learner can already start are highlighted in gold. Layout is row-based so long text never overlaps. */
export default function LadderCard({ card }: { card: Card }) {
  const { t } = useTranslation();
  const { lite } = useAppState();
  const d = card.data as { trade_name: string; steps: LadderStep[]; unavailable?: boolean };
  if (d.unavailable) return <UnavailableCard card={card} title={t("cards.ladderTitle")} />;
  const steps = d.steps;
  const firstEligible = steps.findIndex((s) => s.eligible);
  const n = steps.length;

  return (
    <article className="glass p-4">
      <h3 className="flex items-center gap-2 text-lg font-bold text-ink-900">
        <Icon name="ladder" className="text-primary-700" />
        {t("cards.ladderTitle")} — {d.trade_name}
      </h3>
      <p className="mt-1 text-sm text-ink-600">{t("cards.ladderNsqfExplain")}</p>

      <ol className="mt-3 flex flex-col-reverse" aria-label={t("cards.ladderTitle")}>
        {steps.map((s, i) => {
          const delay = lite ? 0 : 0.22 * i;
          return (
            <li key={s.step_order} className="relative flex items-stretch gap-2">
              <div className="relative w-14 shrink-0" aria-hidden="true">
                <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                  {i > 0 && (
                    <m.line x1={xOf(i - 1)} y1="100" x2={xOf(i)} y2="50" className="stroke-lavender-500" strokeWidth="2"
                      strokeDasharray="5 5" vectorEffect="non-scaling-stroke"
                      initial={lite ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay, duration: 0.3 }} />
                  )}
                  {i < n - 1 && (
                    <m.line x1={xOf(i)} y1="50" x2={xOf(i + 1)} y2="0" className="stroke-lavender-500" strokeWidth="2"
                      strokeDasharray="5 5" vectorEffect="non-scaling-stroke"
                      initial={lite ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: delay + 0.15, duration: 0.3 }} />
                  )}
                </svg>
                <m.svg
                  width="30" height="30" viewBox="0 0 24 24"
                  className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2"
                  style={{ left: `${xOf(i)}%` }}
                  initial={lite ? false : { scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay, type: "spring", stiffness: 260, damping: 16 }}
                >
                  {s.eligible && <circle cx="12" cy="12" r="11.5" className="fill-star-400" opacity="0.35" />}
                  <path d={STAR} className={`${s.eligible ? "fill-star-400" : "fill-white"} stroke-primary-700`} strokeWidth="1.4" strokeLinejoin="round" />
                </m.svg>
              </div>
              <m.div
                className={`my-1.5 flex-1 rounded-2xl px-3 py-2 ${s.eligible ? "eligible-step ring-2 ring-star-400" : "bg-white/80"}`}
                initial={lite ? false : { opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay }}
              >
                <p className="flex items-center gap-1.5 text-base font-semibold leading-snug text-ink-900">
                  <Icon name={KIND_ICON[s.kind] ?? "star"} size={18} className="shrink-0 text-primary-700" />
                  {s.title}
                </p>
                <p className="text-sm text-ink-600">
                  {s.nsqf_level ? t("cards.ladderNsqf", { n: s.nsqf_level }) : ""}
                  {s.duration_months ? ` · ${t("cards.months", { n: s.duration_months })}` : ""}
                </p>
                <p className="text-sm text-ink-600">{s.entry_requirement}</p>
                {i === firstEligible && <p className="mt-0.5 text-sm font-bold text-ink-900">★ {t("cards.eligible")}</p>}
              </m.div>
            </li>
          );
        })}
      </ol>
      <EvidenceBadge evidence={card.evidence} />
    </article>
  );
}
