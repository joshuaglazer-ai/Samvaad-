import { useTranslation } from "react-i18next";
import Icon from "../ui/Icon";
import type { DataStatus, Evidence } from "../../lib/api";

const STYLE: Record<DataStatus, { cls: string; icon: string }> = {
  verified: { cls: "badge-verified", icon: "shield" },
  historical: { cls: "badge-historical", icon: "clock" },
  demo: { cls: "badge-demo", icon: "info" },
  unavailable: { cls: "badge-unavailable", icon: "alert" },
};

/** Data-status badge: colour + icon + text (never colour alone). */
export function StatusBadge({ status }: { status: DataStatus }) {
  const { t } = useTranslation();
  const s = STYLE[status] ?? STYLE.unavailable;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-bold ${s.cls}`}>
      <Icon name={s.icon} size={16} strokeWidth={2.2} />
      <span>{t(`evidence.${status}`)}</span>
    </span>
  );
}

/** Evidence footer shown under every figure: source, period, sample size, geographic level, status. */
export default function EvidenceBadge({ evidence }: { evidence: Evidence }) {
  const { t } = useTranslation();
  const rows: [string, string | null][] = [
    [t("cards.source"), evidence.source],
    [t("cards.period"), evidence.reporting_period],
    [t("cards.level"), evidence.geo_level ? t(`cards.level_${evidence.geo_level}`) : null],
  ];
  return (
    <div className="mt-3 border-t border-lavender-200 pt-3 text-sm text-ink-600">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <StatusBadge status={evidence.data_status} />
        {evidence.data_status === "demo" && <span className="font-semibold text-info-600">{t("app.demoLabel")}</span>}
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
        {rows.filter(([, v]) => v).map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="font-semibold text-ink-900">{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
        {evidence.sample_size ? (
          <div className="contents">
            <dt className="font-semibold text-ink-900">#</dt>
            <dd>{t("cards.sample", { n: evidence.sample_size })}</dd>
          </div>
        ) : null}
      </dl>
    </div>
  );
}
