import { useTranslation } from "react-i18next";
import Icon from "../ui/Icon";
import EvidenceBadge from "./EvidenceBadge";
import { UnavailableCard } from "./OutcomeCard";
import type { Card } from "../../lib/api";
import { rupees } from "../../lib/format";

interface Support { support_type: string; description: string; depends_on_income: boolean }

const SUPPORT_ICON: Record<string, string> = { scheme: "shield", stipend: "wallet", scholarship: "graduation" };

export default function CostsCard({ card }: { card: Card }) {
  const { t } = useTranslation();
  const d = card.data as {
    trade_name: string; fee_min: number | null; fee_max: number | null; fee_description: string | null;
    supports: Support[]; unavailable?: boolean;
  };
  if (d.unavailable) return <UnavailableCard card={card} title={t("cards.costsTitle")} />;
  return (
    <article className="glass p-4">
      <h3 className="flex items-center gap-2 text-lg font-bold text-ink-900">
        <Icon name="rupee" className="text-primary-700" />
        {t("cards.costsTitle")} — {d.trade_name}
      </h3>
      <p className="mt-3 text-sm font-semibold text-ink-600">{t("cards.fee")}</p>
      <p className="text-2xl font-extrabold text-ink-900">
        {d.fee_min === 0 ? t("cards.free") : rupees(d.fee_min)} – {rupees(d.fee_max)}
      </p>
      {d.fee_description && <p className="mt-1 text-sm text-ink-600">{d.fee_description}</p>}
      {d.supports?.length > 0 && (
        <>
          <p className="mt-3 text-sm font-semibold text-ink-600">{t("cards.support")}</p>
          <ul className="mt-1 space-y-2">
            {d.supports.map((s, i) => (
              <li key={i} className="flex items-start gap-2 rounded-2xl bg-white/80 p-3 text-base text-ink-900">
                <Icon name={SUPPORT_ICON[s.support_type] ?? "info"} className="mt-0.5 shrink-0 text-primary-700" />
                <span>{s.description}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <EvidenceBadge evidence={card.evidence} />
    </article>
  );
}
