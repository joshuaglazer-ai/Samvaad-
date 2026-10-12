import { useTranslation } from "react-i18next";
import Icon from "../ui/Icon";
import EvidenceBadge from "./EvidenceBadge";
import type { Card } from "../../lib/api";
import { pct, rangePosition, rupees } from "../../lib/format";

interface OutcomeData {
  trade_name: string;
  placement_rate: number | null;
  placement_numerator: number | null;
  placement_denominator: number | null;
  earnings_min: number | null;
  earnings_max: number | null;
  earnings_median: number | null;
  earnings_basis: "monthly" | "annual";
  fallback_note?: string | null;
  unavailable?: boolean;
  district?: string | null;
}

export function UnavailableCard({ card, title }: { card: Card; title: string }) {
  const { t } = useTranslation();
  const d = card.data as { trade_name?: string; other_districts?: string[] };
  return (
    <article className="glass p-4">
      <h3 className="flex items-center gap-2 text-lg font-bold text-ink-900">
        <Icon name="alert" className="text-ink-600" />
        {title}{d.trade_name ? ` — ${d.trade_name}` : ""}
      </h3>
      <p className="mt-2 text-base text-ink-900">{t("cards.noData")}</p>
      {d.other_districts && d.other_districts.length > 0 && (
        <p className="mt-1 text-sm text-ink-600">{d.other_districts.map((x) => t(`districts.${x}`, x)).join(", ")}</p>
      )}
      <EvidenceBadge evidence={card.evidence} />
    </article>
  );
}

export default function OutcomeCard({ card }: { card: Card }) {
  const { t } = useTranslation();
  const d = card.data as unknown as OutcomeData;
  if (d.unavailable) return <UnavailableCard card={card} title={t("cards.placement")} />;
  const rate = d.placement_rate ?? 0;
  const pos = rangePosition(d.earnings_median, d.earnings_min, d.earnings_max);

  return (
    <article className="glass p-4" aria-label={d.trade_name}>
      <h3 className="flex items-center gap-2 text-lg font-bold text-ink-900">
        <Icon name="briefcase" className="text-primary-700" />
        {d.trade_name}
      </h3>
      {d.fallback_note && (
        <p className="mt-2 flex items-start gap-2 rounded-xl bg-star-400/25 px-3 py-2 text-sm text-ink-900">
          <Icon name="info" size={18} className="mt-0.5 shrink-0" />
          <span>{t("cards.stateFallback")}</span>
        </p>
      )}

      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="text-sm font-semibold text-ink-600">{t("cards.placement")}</p>
          <div className="mt-1 flex items-center gap-3">
            <svg width="64" height="64" viewBox="0 0 36 36" role="img" aria-label={pct(d.placement_rate)}>
              <circle cx="18" cy="18" r="15.5" fill="none" stroke="#EFE9FD" strokeWidth="5" />
              <circle cx="18" cy="18" r="15.5" fill="none" stroke="#6B4FC4" strokeWidth="5" strokeLinecap="round"
                strokeDasharray={`${(rate / 100) * 97.4} 97.4`} transform="rotate(-90 18 18)" />
            </svg>
            <p className="text-3xl font-extrabold text-ink-900">{pct(d.placement_rate)}</p>
          </div>
          {d.placement_numerator != null && d.placement_denominator != null && (
            <p className="mt-1 text-sm text-ink-600">{d.placement_numerator} / {d.placement_denominator}</p>
          )}
        </div>

        <div>
          <p className="text-sm font-semibold text-ink-600">
            {d.earnings_basis === "annual" ? t("cards.earningsAnnual") : t("cards.earnings")}
          </p>
          <p className="mt-1 text-3xl font-extrabold text-ink-900">
            {rupees(d.earnings_median)} <span className="text-base font-semibold text-ink-600">{t("cards.median")}</span>
          </p>
          <div className="relative mt-3 h-3 rounded-full bg-gradient-to-r from-lavender-200 via-lavender-300 to-sky-200" aria-hidden="true">
            <span className="absolute -top-1 h-5 w-5 -translate-x-1/2 rounded-full border-2 border-white bg-star-400 shadow" style={{ left: `${pos}%` }} />
          </div>
          <div className="mt-1 flex justify-between text-sm text-ink-600">
            <span>{rupees(d.earnings_min)}</span>
            <span className="sr-only">{t("cards.range")}</span>
            <span>{rupees(d.earnings_max)}</span>
          </div>
        </div>
      </div>
      <EvidenceBadge evidence={card.evidence} />
    </article>
  );
}
