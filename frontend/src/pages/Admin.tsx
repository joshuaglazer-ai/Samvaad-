import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { CircleMarker, MapContainer, TileLayer, Tooltip as MapTooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import Button from "../components/ui/Button";
import Icon from "../components/ui/Icon";
import PinGate from "../components/ui/PinGate";
import { useAppState } from "../lib/state";
import { StatusBadge } from "../components/cards/EvidenceBadge";
import ChartFrame, { DataTable } from "../components/admin/ChartFrame";
import GoalPanels, { type GoalVsHope, type TopAspirations, type UnmatchedAspirations } from "../components/admin/GoalPanels";
import TradesAdmin from "../components/admin/TradesAdmin";
import { API_BASE, api, type DataStatus } from "../lib/api";
import { ALIGN_ORDER, CONCERN_ORDER, useViz } from "../lib/viz";

// ------------------------------------------------------------------ response types
interface Flags { includes_demo_data: boolean; includes_simulated_sessions: boolean; simulated_sessions: number; min_cell_size: number }
interface Ratio { numerator: number; denominator: number }
interface Overview extends Flags {
  sessions: number; open_cases: number; cases: number; escalation_rate: Ratio;
  mood_shift_parent: { mean: number | null; n: number }; mood_shift_learner: { mean: number | null; n: number };
  evidence_coverage: Ratio; guardrail: Record<string, number>;
  participation_modes: Record<"together" | "two_devices" | "learner_only", number>;
}
interface Suppressible { sessions: number; suppressed: boolean }
interface ResistanceRow extends Suppressible {
  district: string; lat: number; lng: number; negative_parent_messages: number | null; parent_messages: number | null;
  share: number | null; top_negative_concerns: string[] | null;
}
interface ConcernGroup extends Suppressible { group: string; total_messages: number | null; counts: Record<string, number> | null }
interface Concerns extends Flags { by_district: ConcernGroup[]; by_income_bracket: ConcernGroup[] }
interface Sentiment extends Flags {
  model_sentiment_by_parent_turn: ({ turn: number; mean_sentiment: number | null; messages: number | null } & Suppressible)[];
  self_reported_mood: Record<"parent" | "learner", { pre_mean: number | null; post_mean: number | null; improved: number | null; same: number | null; worse: number | null } & Suppressible>;
}
interface Funnel extends Flags { steps: { step: string; sessions: number; denominator: number; share: number }[] }
interface AlignRow extends Suppressible { district: string; completed: number | null; no_big_difference: number | null; counts: Record<string, number> | null }
interface EvidenceGaps extends Flags {
  gaps: { trade_slug: string; district: string; concern: string; requests: number; sessions: number; tools: Record<string, number> }[];
  other: { requests: number; groups: number }; total_requests: number;
}
interface DataQuality {
  outcomes_by_status: Record<string, number>; providers_by_status: Record<string, number>; costs_by_status: Record<string, number>;
  outcomes_total: number; stale_outcomes: { count: number; rule: string }; verification_overdue: { count: number; rule: string };
  trades_missing_qualification_code: number; trades_total: number; includes_demo_data: boolean;
}

const DISTRICTS = ["Bengaluru Urban", "Mysuru", "Kalaburagi", "Dharwad"];
const INCOME = ["<1.5L", "1.5-3L", "3-6L", ">6L", "prefer_not_to_say"];
const pctOf = (r: Ratio) => (r.denominator ? `${Math.round((100 * r.numerator) / r.denominator)}%` : "—");

function Kpi({ icon, label, value, detail }: { icon: string; label: string; value: string; detail: string }) {
  return (
    <div className="glass p-4">
      <p className="flex items-center gap-2 text-sm font-semibold text-ink-600"><Icon name={icon} size={18} className="text-primary-700" />{label}</p>
      <p className="mt-1 text-3xl font-extrabold tabular-nums text-ink-900">{value}</p>
      <p className="text-sm text-ink-600">{detail}</p>
    </div>
  );
}

function Dashboard({ pin, logout }: { pin: string; logout: () => void }) {
  const { t } = useTranslation();
  const viz = useViz();
  const { lite } = useAppState();
  const animate = !lite; // Lite mode: no chart animation either
  const { concernColor: CONCERN_COLOR, alignColor: ALIGN_COLOR, sequential: SEQUENTIAL,
    sequentialColor, grid: GRID, axis: AXIS_TEXT, tooltip: tooltipStyle } = viz;
  const [district, setDistrict] = useState("");
  const [income, setIncome] = useState("");
  const [period, setPeriod] = useState("all");
  const [mode, setMode] = useState("");
  const [concernView, setConcernView] = useState<"district" | "income">("district");
  const [data, setData] = useState<{
    overview: Overview; resistance: { districts: ResistanceRow[] }; concerns: Concerns; sentiment: Sentiment;
    funnel: Funnel; align: { districts: AlignRow[] }; gaps: EvidenceGaps; quality: DataQuality;
    top: TopAspirations; unmatched: UnmatchedAspirations; goalVsHope: GoalVsHope;
  } | null>(null);
  const [tradeNames, setTradeNames] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const qs = useMemo(() => {
    const p = new URLSearchParams();
    if (district) p.set("district", district);
    if (income) p.set("income_bracket", income);
    if (period !== "all") p.set("period", period);
    if (mode) p.set("participation_mode", mode);
    const s = p.toString();
    return s ? `?${s}` : "";
  }, [district, income, period, mode]);

  const load = useCallback(async () => {
    try {
      const g = <T,>(path: string) => api.admin.get<T>(pin, path);
      const [overview, resistance, concerns, sentiment, funnel, align, gaps, quality, top, unmatched, goalVsHope] = await Promise.all([
        g<Overview>(`overview${qs}`), g<{ districts: ResistanceRow[] }>(`resistance-by-district${qs}`),
        g<Concerns>(`concerns${qs}`), g<Sentiment>(`sentiment-shift${qs}`), g<Funnel>(`funnel${qs}`),
        g<{ districts: AlignRow[] }>(`alignment-gaps${qs}`), g<EvidenceGaps>(`evidence-gaps${qs}`), g<DataQuality>("data-quality"),
        g<TopAspirations>(`top-aspirations${qs}`), g<UnmatchedAspirations>(`unmatched-aspirations${qs}`),
        g<GoalVsHope>(`goal-vs-hope${qs}`),
      ]);
      setData({ overview, resistance, concerns, sentiment, funnel, align, gaps, quality, top, unmatched, goalVsHope });
      setError(null);
    } catch (e) {
      if (e instanceof Error && /401/.test(String((e as { status?: number }).status))) logout();
      setError(t("app.error"));
    }
  }, [pin, qs, logout, t]);

  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    api.trades("en").then((ts) => setTradeNames(Object.fromEntries(ts.map((x) => [x.slug, x.name_en])))).catch(() => undefined);
  }, []);

  if (error && !data) return <p role="alert" className="glass mt-4 p-5 text-danger-600">{error}</p>;
  if (!data) return <p className="p-8 text-center text-ink-600" role="status">{t("app.loading")}</p>;

  const { overview: o, resistance, concerns, sentiment, funnel, align, gaps, quality } = data;
  const tooFew = t("admin.tooFew");
  const concernLabel = (c: string) => t(`concerns.${c}`);
  const groups = concernView === "district" ? concerns.by_district : concerns.by_income_bracket;
  const groupLabel = (g: string) => (concernView === "district" ? t(`districts.${g}`, g) : t(`income.${g}`, g === "not_given" ? "—" : g));
  const concernRows = groups.filter((g) => !g.suppressed && g.counts).map((g) => ({
    name: groupLabel(g.group), total: g.total_messages, sessions: g.sessions,
    ...Object.fromEntries(CONCERN_ORDER.map((c) => [c, g.total_messages ? Math.round((1000 * (g.counts![c] ?? 0)) / g.total_messages) / 10 : 0])),
    ...Object.fromEntries(CONCERN_ORDER.map((c) => [`${c}_n`, g.counts![c] ?? 0])),
  }));
  const suppressedGroups = groups.filter((g) => g.suppressed);
  const maxShare = Math.max(0.01, ...resistance.districts.map((d) => d.share ?? 0));
  const maxSessions = Math.max(1, ...resistance.districts.map((d) => d.sessions));
  const moodRows = (["parent", "learner"] as const).map((w) => ({ who: t(`mood.${w}`), ...sentiment.self_reported_mood[w] }));
  const alignRows = align.districts.filter((d) => !d.suppressed && d.counts && d.completed).map((d) => ({
    name: t(`districts.${d.district}`), completed: d.completed,
    ...Object.fromEntries(ALIGN_ORDER.map((v) => [v, Math.round((1000 * (d.counts![v] ?? 0)) / d.completed!) / 10])),
    ...Object.fromEntries(ALIGN_ORDER.map((v) => [`${v}_n`, d.counts![v] ?? 0])),
  }));
  const tradeName = (slug: string) => slug.startsWith("goal: ") ? `“${slug.slice(6)}” (goal)` : tradeNames[slug] ?? slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const exportHref = `${API_BASE}/api/admin/export.csv${qs ? `${qs}&` : "?"}pin=${encodeURIComponent(pin)}`;

  return (
    <section className="mt-2 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-ink-900"><Icon name="chart" className="text-primary-700" />{t("admin.title")}</h1>
        <div className="flex gap-2">
          <a href={exportHref} className="inline-flex min-h-12 items-center gap-2 rounded-2xl bg-primary-600 px-4 font-semibold text-white hover:bg-primary-700">
            <Icon name="download" /> {t("admin.export")}
          </a>
          <Button variant="ghost" icon="lock" onClick={logout}>{t("app.close")}</Button>
        </div>
      </div>

      {(o.includes_simulated_sessions || o.includes_demo_data) && (
        <p role="status" className="flex items-start gap-2 rounded-2xl bg-info-600 px-4 py-3 font-semibold text-white">
          <Icon name="info" className="mt-0.5 shrink-0" />
          <span>
            {t("admin.demoBanner")}
            {o.includes_simulated_sessions && ` (${o.simulated_sessions} simulated sessions)`}
            {o.includes_demo_data && ` · ${t("app.demoLabel")}`}
          </span>
        </p>
      )}

      {/* Filters: one row, above all charts */}
      <div className="glass flex flex-wrap items-end gap-3 p-3" role="group" aria-label="Filters">
        <label className="text-sm font-semibold text-ink-900">
          {t("admin.filterDistrict")}
          <select value={district} onChange={(e) => setDistrict(e.target.value)} className="mt-1 block min-h-12 rounded-xl border border-lavender-200 bg-white px-3 text-base">
            <option value="">{t("admin.all")}</option>
            {DISTRICTS.map((d) => <option key={d} value={d}>{t(`districts.${d}`)}</option>)}
          </select>
        </label>
        <label className="text-sm font-semibold text-ink-900">
          {t("admin.filterIncome")}
          <select value={income} onChange={(e) => setIncome(e.target.value)} className="mt-1 block min-h-12 rounded-xl border border-lavender-200 bg-white px-3 text-base">
            <option value="">{t("admin.all")}</option>
            {INCOME.map((b) => <option key={b} value={b}>{t(`income.${b}`)}</option>)}
          </select>
        </label>
        <label className="text-sm font-semibold text-ink-900">
          {t("adminModes.filter")}
          <select value={mode} onChange={(e) => setMode(e.target.value)} className="mt-1 block min-h-12 rounded-xl border border-lavender-200 bg-white px-3 text-base">
            <option value="">{t("admin.all")}</option>
            {(["together", "two_devices", "learner_only"] as const).map((md) => (
              <option key={md} value={md}>{t(`adminModes.${md}`)} ({o.participation_modes?.[md] ?? 0})</option>
            ))}
          </select>
        </label>
        <div className="text-sm font-semibold text-ink-900">
          {t("admin.period")}
          <div className="mt-1 flex rounded-xl border border-lavender-200 bg-white p-0.5" role="radiogroup" aria-label={t("admin.period")}>
            {["7d", "30d", "90d", "all"].map((p) => (
              <button key={p} type="button" role="radio" aria-checked={period === p} onClick={() => setPeriod(p)}
                className={`min-h-11 rounded-lg px-3 text-sm font-semibold ${period === p ? "bg-primary-600 text-white" : "text-ink-900"}`}>
                {p === "all" ? t("admin.all") : p}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi icon="users" label={t("admin.sessions")} value={String(o.sessions)} detail={`${o.escalation_rate.numerator} escalated (${pctOf(o.escalation_rate)})`} />
        <Kpi icon="chat" label={t("admin.openCases")} value={String(o.open_cases)} detail={`of ${o.cases} cases`} />
        <Kpi icon="heart" label={t("admin.moodShift")}
          value={o.mood_shift_parent.mean == null ? "—" : `${o.mood_shift_parent.mean > 0 ? "+" : ""}${o.mood_shift_parent.mean}`}
          detail={o.mood_shift_parent.mean == null ? tooFew : `${t("mood.parent")}, self-reported 1–5 · n=${o.mood_shift_parent.n}`} />
        <Kpi icon="shield" label={t("admin.coverage")} value={pctOf(o.evidence_coverage)}
          detail={`${o.evidence_coverage.numerator} / ${o.evidence_coverage.denominator} data requests answered`} />
      </div>

      {/* Map + resistance */}
      <ChartFrame
        title={t("admin.map")}
        subtitle={`${t("admin.resistanceShare")} — model-estimated sentiment ≤ −1. Circle size = sessions; colour = share.`}
        chart={
          <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
            <div className="h-80 overflow-hidden rounded-2xl">
              <MapContainer center={[14.9, 76.4]} zoom={6} scrollWheelZoom={false} style={{ height: "100%", width: "100%" }}>
                <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                {resistance.districts.map((d) => (
                  <CircleMarker key={d.district} center={[d.lat, d.lng]} radius={10 + 22 * Math.sqrt(d.sessions / maxSessions)}
                    pathOptions={{ color: viz.gap, weight: 2, fillOpacity: 0.85,
                      fillColor: d.suppressed || d.share == null ? viz.suppressed : sequentialColor(d.share, maxShare) }}>
                    <MapTooltip>
                      <strong>{t(`districts.${d.district}`)}</strong><br />
                      {d.suppressed ? tooFew : <>
                        {Math.round((d.share ?? 0) * 100)}% ({d.negative_parent_messages}/{d.parent_messages} parent messages)<br />
                        {d.sessions} sessions<br />
                        {(d.top_negative_concerns ?? []).map(concernLabel).join(", ")}
                      </>}
                    </MapTooltip>
                  </CircleMarker>
                ))}
              </MapContainer>
            </div>
            <div>
              <ul className="space-y-3">
                {[...resistance.districts].sort((a, b) => (b.share ?? -1) - (a.share ?? -1)).map((d) => (
                  <li key={d.district}>
                    <div className="flex justify-between text-sm font-semibold text-ink-900">
                      <span>{t(`districts.${d.district}`)}</span>
                      <span className="tabular-nums">{d.suppressed ? tooFew : `${Math.round((d.share ?? 0) * 100)}%`}</span>
                    </div>
                    {!d.suppressed && (
                      <>
                        <div className="mt-1 h-2.5 rounded-full bg-lavender-100">
                          <div className="h-2.5 rounded-full" style={{ width: `${((d.share ?? 0) / maxShare) * 100}%`, background: sequentialColor(d.share ?? 0, maxShare) }} />
                        </div>
                        <p className="mt-0.5 text-xs text-ink-600">
                          {d.negative_parent_messages}/{d.parent_messages} · {d.sessions} sessions · {(d.top_negative_concerns ?? []).slice(0, 2).map(concernLabel).join(", ")}
                        </p>
                      </>
                    )}
                  </li>
                ))}
              </ul>
              <div className="mt-4 text-xs text-ink-600">
                <div className="flex h-2.5 overflow-hidden rounded-full" aria-hidden="true">{SEQUENTIAL.slice(1).map((c) => <span key={c} className="flex-1" style={{ background: c }} />)}</div>
                <div className="mt-0.5 flex justify-between"><span>0%</span><span>{Math.round(maxShare * 100)}%</span></div>
              </div>
            </div>
          </div>
        }
        table={<DataTable head={["District", "Negative parent msgs", "Parent msgs", "Share", "Sessions", "Top worries"]}
          rows={resistance.districts.map((d) => [t(`districts.${d.district}`), d.negative_parent_messages, d.parent_messages,
            d.suppressed ? tooFew : `${Math.round((d.share ?? 0) * 100)}%`, d.sessions, (d.top_negative_concerns ?? []).map(concernLabel).join(", ")])} />}
        footnote={`${t("adminModes.selfIdentified")} Cells with fewer than ${o.min_cell_size} sessions are shown as "${tooFew}".`}
      />

      <div className="grid gap-4 xl:grid-cols-2">
        {/* Concerns */}
        <ChartFrame
          title={concernView === "district" ? t("admin.concerns") : t("admin.concernsByIncome")}
          subtitle="Share of family messages by worry (%). Tagged per message."
          legend={CONCERN_ORDER.map((c) => ({ label: concernLabel(c), color: CONCERN_COLOR[c] }))}
          chart={
            <>
              <div className="mb-2 flex gap-1" role="radiogroup" aria-label="Group by">
                {(["district", "income"] as const).map((v) => (
                  <button key={v} type="button" role="radio" aria-checked={concernView === v} onClick={() => setConcernView(v)}
                    className={`min-h-11 rounded-lg px-3 text-sm font-semibold ${concernView === v ? "bg-primary-600 text-white" : "bg-white/80 text-ink-900"}`}>
                    {v === "district" ? t("admin.filterDistrict") : t("admin.filterIncome")}
                  </button>
                ))}
              </div>
              <ResponsiveContainer width="100%" height={Math.max(180, concernRows.length * 52 + 40)}>
                <BarChart data={concernRows} layout="vertical" margin={{ left: 8, right: 16 }} barCategoryGap={10}>
                  <CartesianGrid horizontal={false} stroke={GRID} />
                  <XAxis type="number" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} allowDataOverflow tickFormatter={(v: number) => `${Math.round(v)}%`} tick={{ fill: AXIS_TEXT, fontSize: 12 }} />
                  <YAxis type="category" dataKey="name" width={110} tick={{ fill: AXIS_TEXT, fontSize: 12 }} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: GRID, opacity: 0.4 }}
                    formatter={(v: number, name: string, item) => [`${v}% (${(item.payload as Record<string, number>)[`${name}_n`]})`, concernLabel(name)]} />
                  {CONCERN_ORDER.map((c, i) => (
                    <Bar isAnimationActive={animate} key={c} dataKey={c} stackId="a" fill={CONCERN_COLOR[c]} stroke={viz.gap} strokeWidth={2}
                      radius={i === CONCERN_ORDER.length - 1 ? [0, 4, 4, 0] : 0} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
              {suppressedGroups.length > 0 && (
                <p className="text-xs text-ink-600">{suppressedGroups.map((g) => groupLabel(g.group)).join(", ")}: {tooFew}</p>
              )}
            </>
          }
          table={<DataTable head={["Group", "Messages", ...CONCERN_ORDER.map(concernLabel)]}
            rows={groups.map((g) => [groupLabel(g.group), g.suppressed ? tooFew : g.total_messages,
              ...CONCERN_ORDER.map((c) => (g.counts ? g.counts[c] : null))])} />}
        />

        {/* Alignment gaps */}
        <ChartFrame
          title={t("admin.alignmentGaps")}
          subtitle="Value that learner and parent ranked most differently (share of completed card sorts)."
          legend={ALIGN_ORDER.map((v) => ({ label: t(`alignment.values.${v}`), color: ALIGN_COLOR[v] }))}
          chart={
            <ResponsiveContainer width="100%" height={Math.max(180, alignRows.length * 52 + 40)}>
              <BarChart data={alignRows} layout="vertical" margin={{ left: 8, right: 16 }} barCategoryGap={10}>
                <CartesianGrid horizontal={false} stroke={GRID} />
                <XAxis type="number" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} allowDataOverflow tickFormatter={(v: number) => `${Math.round(v)}%`} tick={{ fill: AXIS_TEXT, fontSize: 12 }} />
                <YAxis type="category" dataKey="name" width={110} tick={{ fill: AXIS_TEXT, fontSize: 12 }} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: GRID, opacity: 0.4 }}
                  formatter={(v: number, name: string, item) => [`${v}% (${(item.payload as Record<string, number>)[`${name}_n`]})`, t(`alignment.values.${name}`)]} />
                {ALIGN_ORDER.map((v, i) => (
                  <Bar isAnimationActive={animate} key={v} dataKey={v} stackId="a" fill={ALIGN_COLOR[v]} stroke={viz.gap} strokeWidth={2}
                    radius={i === ALIGN_ORDER.length - 1 ? [0, 4, 4, 0] : 0} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          }
          table={<DataTable head={["District", "Completed", ...ALIGN_ORDER.map((v) => t(`alignment.values.${v}`))]}
            rows={align.districts.map((d) => [t(`districts.${d.district}`), d.suppressed ? tooFew : d.completed,
              ...ALIGN_ORDER.map((v) => (d.counts ? d.counts[v] : null))])} />}
        />

        {/* Model sentiment — its own chart, its own axis */}
        <ChartFrame
          title={t("admin.modelSentiment")}
          subtitle="Mean estimated sentiment by the parent's message number in a session (−2 very negative … +2 very positive)."
          chart={
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={sentiment.model_sentiment_by_parent_turn.filter((x) => !x.suppressed)} margin={{ left: 0, right: 16, top: 8 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey="turn" tickFormatter={(v) => (v === 5 ? "5+" : String(v))} tick={{ fill: AXIS_TEXT, fontSize: 12 }}
                  label={{ value: "Parent message #", position: "insideBottom", offset: -2, fill: AXIS_TEXT, fontSize: 12 }} height={36} />
                <YAxis domain={[-2, 2]} ticks={[-2, -1, 0, 1, 2]} tick={{ fill: AXIS_TEXT, fontSize: 12 }} width={32} />
                <ReferenceLine y={0} stroke={viz.zeroLine} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: GRID, opacity: 0.4 }} formatter={(v: number, _n, item) => [`${v} (n=${(item.payload as { messages: number }).messages})`, "Mean sentiment"]}
                  labelFormatter={(l) => `Parent message #${l === 5 ? "5+" : l}`} />
                <Line isAnimationActive={animate} type="monotone" dataKey="mean_sentiment" stroke={viz.series1} strokeWidth={2}
                  dot={{ r: 4, fill: viz.series1, stroke: viz.gap, strokeWidth: 2 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          }
          table={<DataTable head={["Parent message #", "Mean sentiment", "Messages", "Sessions"]}
            rows={sentiment.model_sentiment_by_parent_turn.map((x) => [x.turn === 5 ? "5+" : x.turn, x.suppressed ? tooFew : x.mean_sentiment, x.messages, x.sessions])} />}
          footnote={`Model estimate from message text — not the family's own rating. ${t("adminModes.selfIdentified")}`}
        />

        {/* Self-reported mood — separate chart */}
        <ChartFrame
          title={t("admin.selfMood")}
          subtitle="Families' own 1–5 rating before and after the conversation."
          legend={[{ label: "Before", color: viz.series2 }, { label: "After", color: viz.series1 }]}
          chart={
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={moodRows.filter((r) => !r.suppressed)} margin={{ left: 0, right: 16, top: 8 }} barGap={2}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey="who" tick={{ fill: AXIS_TEXT, fontSize: 12 }} />
                <YAxis domain={[0, 5]} ticks={[1, 2, 3, 4, 5]} tick={{ fill: AXIS_TEXT, fontSize: 12 }} width={28} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: GRID, opacity: 0.4 }} formatter={(v: number, name: string) => [v, name === "pre_mean" ? "Before" : "After"]} />
                <Bar isAnimationActive={animate} dataKey="pre_mean" fill={viz.series2} radius={[4, 4, 0, 0]} maxBarSize={48} />
                <Bar isAnimationActive={animate} dataKey="post_mean" fill={viz.series1} radius={[4, 4, 0, 0]} maxBarSize={48} />
              </BarChart>
            </ResponsiveContainer>
          }
          table={<DataTable head={["Who", "Before (mean)", "After (mean)", "Improved", "Same", "Worse", "Sessions"]}
            rows={moodRows.map((r) => [r.who, r.suppressed ? tooFew : r.pre_mean, r.post_mean, r.improved, r.same, r.worse, r.sessions])} />}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1.4fr]">
        {/* Funnel */}
        <ChartFrame
          title={t("admin.funnel")}
          subtitle="Sessions reaching each step."
          chart={
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={funnel.steps.map((s) => ({ ...s, label: t(`admin.steps.${s.step}`), pct: Math.round(s.share * 100) }))}
                layout="vertical" margin={{ left: 8, right: 40 }} barCategoryGap={8}>
                <XAxis type="number" hide domain={[0, funnel.steps[0]?.denominator || 1]} />
                <YAxis type="category" dataKey="label" width={150} tick={{ fill: AXIS_TEXT, fontSize: 12 }} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: GRID, opacity: 0.4 }} formatter={(v: number, _n, item) => [`${v} / ${(item.payload as { denominator: number }).denominator} (${(item.payload as { pct: number }).pct}%)`, "Sessions"]} />
                <Bar isAnimationActive={animate} dataKey="sessions" radius={[0, 4, 4, 0]} label={{ position: "right", fill: AXIS_TEXT, fontSize: 12, formatter: (v: number) => v }}>
                  {funnel.steps.map((s) => <Cell key={s.step} fill={s.step === "escalated" ? viz.muted : viz.series1} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          }
          table={<DataTable head={["Step", "Sessions", "Of", "Share"]}
            rows={funnel.steps.map((s) => [t(`admin.steps.${s.step}`), s.sessions, s.denominator, `${Math.round(s.share * 100)}%`])} />}
        />

        {/* Evidence Gap Radar */}
        <section className="glass min-w-0 p-4">
          <h2 className="flex items-center gap-2 text-lg font-bold text-ink-900"><Icon name="alert" className="text-primary-700" />{t("admin.evidenceGaps")}</h2>
          <p className="text-sm text-ink-600">Questions families asked that our data could not answer — where to collect data next.</p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm text-ink-900">
              <thead>
                <tr className="border-b border-lavender-200">
                  {["#", "Trade", "District", "Worry", "Requests", "Sessions", "Missing"].map((h) => <th key={h} scope="col" className="px-2 py-1.5 font-semibold">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {gaps.gaps.map((g, i) => (
                  <tr key={`${g.trade_slug}-${g.district}-${g.concern}`} className="border-b border-lavender-100">
                    <td className="px-2 py-1.5 tabular-nums">{i + 1}</td>
                    <td className="px-2 py-1.5 font-semibold">{tradeName(g.trade_slug)}</td>
                    <td className="px-2 py-1.5">{t(`districts.${g.district}`, g.district)}</td>
                    <td className="px-2 py-1.5">{concernLabel(g.concern)}</td>
                    <td className="px-2 py-1.5 tabular-nums">
                      <span className="inline-block h-2 rounded-full bg-primary-600 align-middle" style={{ width: `${(g.requests / (gaps.gaps[0]?.requests || 1)) * 60}px` }} aria-hidden="true" />{" "}
                      {g.requests}
                    </td>
                    <td className="px-2 py-1.5 tabular-nums">{g.sessions}</td>
                    <td className="px-2 py-1.5">{Object.keys(g.tools).map((x) => x.replace(/^get_|_/g, " ").trim()).join(", ")}</td>
                  </tr>
                ))}
                {gaps.other.requests > 0 && (
                  <tr className="text-ink-600">
                    <td className="px-2 py-1.5" />
                    <td className="px-2 py-1.5" colSpan={3}>Other ({gaps.other.groups} smaller groups, {tooFew} each)</td>
                    <td className="px-2 py-1.5 tabular-nums">{gaps.other.requests}</td>
                    <td colSpan={2} />
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-ink-600">{gaps.total_requests} unanswered requests in total.</p>
        </section>
      </div>

      {/* Update 3: goals in families' own words */}
      <div className="grid gap-4 lg:grid-cols-2">
        <GoalPanels top={data.top} unmatched={data.unmatched} goalVsHope={data.goalVsHope} animate={animate} />
      </div>

      {/* Data quality */}
      <section className="glass p-4">
        <h2 className="flex items-center gap-2 text-lg font-bold text-ink-900"><Icon name="shield" className="text-primary-700" />{t("admin.dataQuality")}</h2>
        <div className="mt-3 grid gap-4 md:grid-cols-3">
          {([["Outcome records", quality.outcomes_by_status], ["Training centres", quality.providers_by_status], ["Fees & support", quality.costs_by_status]] as const).map(([label, counts]) => (
            <div key={label} className="rounded-2xl bg-white/80 p-3">
              <p className="font-semibold text-ink-900">{label}</p>
              <ul className="mt-2 space-y-1.5">
                {Object.entries(counts).map(([status, n]) => (
                  <li key={status} className="flex items-center justify-between gap-2"><StatusBadge status={status as DataStatus} /><span className="tabular-nums font-semibold">{n}</span></li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <ul className="mt-3 space-y-1 text-sm text-ink-900">
          <li>Older records ({quality.stale_outcomes.rule}): <strong>{quality.stale_outcomes.count}</strong> of {quality.outcomes_total}</li>
          <li>Verification overdue ({quality.verification_overdue.rule}): <strong>{quality.verification_overdue.count}</strong></li>
          <li>Trades without an official qualification code (to verify on nqr.gov.in): <strong>{quality.trades_missing_qualification_code}</strong> of {quality.trades_total}</li>
        </ul>
      </section>
    </section>
  );
}

function AdminTabs({ pin, logout }: { pin: string; logout: () => void }) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<"dashboard" | "trades">("dashboard");
  return (
    <>
      <div className="mt-2 flex gap-1 rounded-2xl border border-lavender-200 bg-white p-1" role="tablist" aria-label={t("admin.title")}>
        {(["dashboard", "trades"] as const).map((k) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl px-3 font-semibold ${tab === k ? "bg-primary-600 text-white" : "text-ink-900"}`}>
            <Icon name={k === "dashboard" ? "chart" : "gear"} size={20} />{k === "dashboard" ? t("admin.tabDashboard") : t("admin.tabTrades")}
          </button>
        ))}
      </div>
      <div role="tabpanel">{tab === "dashboard" ? <Dashboard pin={pin} logout={logout} /> : <TradesAdmin pin={pin} />}</div>
    </>
  );
}

export default function Admin() {
  const { t } = useTranslation();
  return (
    <PinGate storageKey="samvaad.adminPin" title={t("admin.title")} label={t("admin.pin")} submit={t("admin.login")}
      verify={async (pin) => { await api.admin.get(pin, "data-quality"); }}>
      {(pin, logout) => <AdminTabs pin={pin} logout={logout} />}
    </PinGate>
  );
}
