import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import Icon from "../ui/Icon";

interface Props {
  title: string;
  subtitle?: string;
  chart: ReactNode;
  table: ReactNode;
  legend?: { label: string; color: string }[];
  footnote?: string;
}

/** Card wrapper for every dashboard chart: title, legend, chart/table toggle (table view is the
 * accessible alternative), and a footnote with counts/denominators or suppression notes. */
export default function ChartFrame({ title, subtitle, chart, table, legend, footnote }: Props) {
  const { t } = useTranslation();
  const [asTable, setAsTable] = useState(false);
  return (
    <section className="glass p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold text-ink-900">{title}</h2>
          {subtitle && <p className="text-sm text-ink-600">{subtitle}</p>}
        </div>
        <button type="button" onClick={() => setAsTable(!asTable)} aria-pressed={asTable}
          className="flex min-h-12 items-center gap-1.5 rounded-xl px-3 text-sm font-semibold text-primary-700 hover:bg-lavender-100">
          <Icon name={asTable ? "chart" : "ladder"} size={18} />
          {asTable ? t("admin.showChart") : t("admin.showTable")}
        </button>
      </div>
      {legend && legend.length > 1 && !asTable && (
        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-900" aria-label="Legend">
          {legend.map((l) => (
            <li key={l.label} className="flex items-center gap-1.5">
              <span className="inline-block h-3 w-3 rounded-sm" style={{ background: l.color }} aria-hidden="true" />
              {l.label}
            </li>
          ))}
        </ul>
      )}
      <div className="mt-3">{asTable ? <div className="overflow-x-auto">{table}</div> : chart}</div>
      {footnote && <p className="mt-2 text-xs text-ink-600">{footnote}</p>}
    </section>
  );
}

export function DataTable({ head, rows }: { head: string[]; rows: (string | number | null)[][] }) {
  return (
    <table className="w-full min-w-[480px] border-collapse text-left text-sm text-ink-900">
      <thead>
        <tr className="border-b border-lavender-200">
          {head.map((h) => <th key={h} scope="col" className="px-2 py-1.5 font-semibold">{h}</th>)}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className="border-b border-lavender-100">
            {r.map((c, j) => <td key={j} className="px-2 py-1.5 tabular-nums">{c ?? "—"}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
