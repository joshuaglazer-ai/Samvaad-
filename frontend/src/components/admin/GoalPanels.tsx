import { useTranslation } from "react-i18next";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Icon from "../ui/Icon";
import ChartFrame, { DataTable } from "./ChartFrame";
import { useViz } from "../../lib/viz";

// Update 3 dashboard panels. Every count comes from logged sessions; groups under the small-cell threshold are folded
// into "other" by the backend, and exact words are quoted only when at least that many families used them.
interface Flags { min_cell_size: number; parent_data_note: string }
interface Suppressible { sessions: number; suppressed: boolean }
export interface TopAspirations extends Flags {
  districts: { district: string; sessions: number; other_sessions: number;
    groups: { trade_slug: string | null; trade_name: string | null; sessions: number; words: { text: string; sessions: number }[]; other_words_sessions: number }[] }[];
}
export interface UnmatchedAspirations extends Flags {
  goals: { text: string; category: string; sessions: number; learner: number | null; parent: number | null; districts: Record<string, number | null> }[];
  other: { phrases: number; sessions: number };
}
type DifferCell = Suppressible & { differ: number | null; differ_rate: number | null };
export interface GoalVsHope extends Flags {
  districts: ({ district: string } & DifferCell)[];
  overall: DifferCell;
  by_mode: Record<string, DifferCell>;
}

const CATEGORY_LABEL: Record<string, string> = {
  degree_career: "Degree career", professional_course: "Professional course", unknown: "Not in our data",
};

export default function GoalPanels({ top, unmatched, goalVsHope, animate }: {
  top: TopAspirations; unmatched: UnmatchedAspirations; goalVsHope: GoalVsHope; animate: boolean;
}) {
  const { t } = useTranslation();
  const viz = useViz();
  const tooFew = t("admin.tooFew");
  const few = (n: number | null) => (n === null ? `<${unmatched.min_cell_size}` : String(n));
  const differRows = goalVsHope.districts.filter((d) => !d.suppressed).map((d) => ({
    name: t(`districts.${d.district}`, d.district), rate: d.differ_rate ?? 0, differ: d.differ, sessions: d.sessions,
  }));
  const suppressed = goalVsHope.districts.filter((d) => d.suppressed);

  return (
    <>
      {/* Top aspirations, by district */}
      <section className="glass min-w-0 p-4" data-testid="panel-top-aspirations">
        <h2 className="flex items-center gap-2 text-lg font-bold text-ink-900"><Icon name="star" className="text-primary-700" />{t("admin.topAspirations")}</h2>
        <p className="text-sm text-ink-600">{t("admin.topAspirationsSub")}</p>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {top.districts.map((d) => (
            <div key={d.district} className="rounded-2xl bg-white/80 p-3">
              <p className="font-semibold text-ink-900">{t(`districts.${d.district}`, d.district)} <span className="font-normal text-ink-600">· {d.sessions} sessions</span></p>
              <ul className="mt-2 space-y-2">
                {d.groups.map((g) => (
                  <li key={g.trade_slug ?? "none"}>
                    <div className="flex items-center justify-between gap-2 text-ink-900">
                      <span className="font-semibold">{g.trade_name ?? t("admin.noMatchGroup")}</span>
                      <span className="tabular-nums">{g.sessions}</span>
                    </div>
                    <span className="block h-1.5 rounded-full" style={{ width: `${Math.max(6, (100 * g.sessions) / (d.groups[0]?.sessions || 1))}%`, background: viz.series1 }} aria-hidden="true" />
                    {g.words.length > 0 && (
                      <p className="mt-1 text-sm text-ink-600">
                        {g.words.map((w) => `“${w.text}” (${w.sessions})`).join(" · ")}
                        {g.other_words_sessions > 0 && ` · ${t("admin.otherWords")} (${g.other_words_sessions})`}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
              {d.other_sessions > 0 && <p className="mt-2 text-xs text-ink-600">+ {d.other_sessions} sessions in {t("admin.smallerGroups")} ({tooFew})</p>}
            </div>
          ))}
        </div>
      </section>

      {/* Unmatched aspirations */}
      <section className="glass min-w-0 p-4" data-testid="panel-unmatched">
        <h2 className="flex items-center gap-2 text-lg font-bold text-ink-900"><Icon name="question" className="text-primary-700" />{t("admin.unmatched")}</h2>
        <p className="text-sm text-ink-600">{t("admin.unmatchedSub")}</p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-sm text-ink-900">
            <thead>
              <tr className="border-b border-lavender-200">
                {["Goal (their words)", "Kind", "Sessions", "Learner", "Parent", "Districts"].map((h) => <th key={h} scope="col" className="px-2 py-1.5 font-semibold">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {unmatched.goals.map((g) => (
                <tr key={g.text} className="border-b border-lavender-100">
                  <td className="px-2 py-1.5 font-semibold">“{g.text}”</td>
                  <td className="px-2 py-1.5">{CATEGORY_LABEL[g.category] ?? g.category}</td>
                  <td className="px-2 py-1.5 tabular-nums">{g.sessions}</td>
                  <td className="px-2 py-1.5 tabular-nums">{few(g.learner)}</td>
                  <td className="px-2 py-1.5 tabular-nums">{few(g.parent)}</td>
                  <td className="px-2 py-1.5">{Object.entries(g.districts).map(([d, n]) => `${t(`districts.${d}`, d)} ${few(n)}`).join(", ")}</td>
                </tr>
              ))}
              {unmatched.other.phrases > 0 && (
                <tr className="text-ink-600">
                  <td className="px-2 py-1.5" colSpan={2}>Other ({unmatched.other.phrases} goals, {tooFew} each)</td>
                  <td className="px-2 py-1.5 tabular-nums">{unmatched.other.sessions}</td>
                  <td colSpan={3} />
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-ink-600">Parent hopes: {goalVsHope.parent_data_note}. Also listed in the Evidence Gap Radar as “goal: …”.</p>
      </section>

      {/* Learner goal vs parent hope */}
      <ChartFrame
        title={t("admin.goalVsHope")}
        subtitle={`${t("admin.goalVsHopeSub")} ${goalVsHope.parent_data_note}.`}
        chart={
          <div className="h-56" data-testid="panel-goal-vs-hope">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={differRows} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke={viz.grid} />
                <XAxis dataKey="name" tick={{ fill: viz.axis, fontSize: 12 }} />
                <YAxis domain={[0, 100]} unit="%" tick={{ fill: viz.axis, fontSize: 12 }} width={44} />
                <Tooltip contentStyle={viz.tooltip} cursor={{ fill: viz.grid, opacity: 0.4 }}
                  formatter={(v: number, _n, item) => [`${v}% (${(item.payload as { differ: number }).differ} of ${(item.payload as { sessions: number }).sessions})`, t("admin.differRate")]} />
                <Bar isAnimationActive={animate} dataKey="rate" fill={viz.series1} radius={[4, 4, 0, 0]} maxBarSize={56} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        }
        table={<DataTable head={["District", "Differ", "Sessions", "Share"]}
          rows={goalVsHope.districts.map((d) => [t(`districts.${d.district}`, d.district), d.suppressed ? tooFew : d.differ ?? "—",
            d.sessions, d.suppressed ? "—" : `${d.differ_rate}%`])} />}
        footnote={[
          goalVsHope.overall.suppressed ? null : `Overall: ${goalVsHope.overall.differ} of ${goalVsHope.overall.sessions} (${goalVsHope.overall.differ_rate}%).`,
          goalVsHope.by_mode.two_devices && !goalVsHope.by_mode.two_devices.suppressed
            ? `Two phones (strongest signal): ${goalVsHope.by_mode.two_devices.differ_rate}% of ${goalVsHope.by_mode.two_devices.sessions}.` : null,
          suppressed.length ? `${suppressed.map((d) => t(`districts.${d.district}`, d.district)).join(", ")}: ${tooFew}.` : null,
        ].filter(Boolean).join(" ")}
      />
    </>
  );
}
