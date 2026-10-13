import { useTranslation } from "react-i18next";
import Icon from "../ui/Icon";
import type { GoalComparison } from "../../lib/api";

/**
 * The learner's goal and the parent's hope, side by side and kindly worded. Neither is presented as better;
 * when they differ the family is invited to look at both.
 */
export default function GoalCompare({ goals }: { goals: GoalComparison }) {
  const { t } = useTranslation();
  const { learner, parent, differ } = goals;
  if (!learner && !parent) return null;
  const label = (g: GoalComparison["learner"]) => g?.label || t("goal.notChosen");

  if (learner && parent && !differ) {
    return (
      <p className="flex items-start gap-2 rounded-2xl bg-lavender-100 px-4 py-3 text-lg text-ink-900" data-testid="goal-compare">
        <Icon name="users" className="mt-1 shrink-0 text-primary-700" />
        {t("goal.bothHope", { goal: label(learner) })}
      </p>
    );
  }
  return (
    <section aria-labelledby="goal-compare-title" className="space-y-3" data-testid="goal-compare">
      <h2 id="goal-compare-title" className="text-xl font-bold text-ink-900">{t("goal.compareTitle")}</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {([["learner", learner, "goal.learnerHopes"], ["parent", parent, "goal.parentHopes"]] as const).map(([who, g, key]) => (
          <div key={who} className="rounded-2xl border-2 border-lavender-200 bg-white/80 p-3">
            <p className="flex items-center gap-2 font-semibold text-ink-600">
              <Icon name={who} size={20} className="text-primary-700" />{t(key)}
            </p>
            <p className="mt-1 text-xl font-bold text-ink-900" data-testid={`goal-${who}-label`}>{label(g)}</p>
          </div>
        ))}
      </div>
      {differ && <p className="text-lg text-ink-900">{t("goal.lookAtBoth")}</p>}
    </section>
  );
}
