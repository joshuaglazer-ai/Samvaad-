import { useTranslation } from "react-i18next";
import Icon from "../ui/Icon";
import EvidenceBadge, { StatusBadge } from "./EvidenceBadge";
import { UnavailableCard } from "./OutcomeCard";
import type { Card, DataStatus } from "../../lib/api";

interface Provider { name: string; district: string; provider_type: string; data_status: DataStatus }

const TYPE_ICON: Record<string, string> = { government_iti: "building", skill_centre: "gear", private_training_partner: "heart" };

export default function ProviderCard({ card }: { card: Card }) {
  const { t } = useTranslation();
  const d = card.data as { trade_name: string; district: string; providers: Provider[]; unavailable?: boolean };
  if (d.unavailable) return <UnavailableCard card={card} title={t("cards.providersTitle")} />;
  return (
    <article className="glass p-4">
      <h3 className="flex items-center gap-2 text-lg font-bold text-ink-900">
        <Icon name="pin" className="text-primary-700" />
        {t("cards.providersTitle")} — {t(`districts.${d.district}`, d.district)}
      </h3>
      <ul className="mt-3 space-y-2">
        {d.providers.map((p) => (
          <li key={p.name} className="flex items-center gap-3 rounded-2xl bg-white/80 p-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-lavender-100 text-primary-700">
              <Icon name={TYPE_ICON[p.provider_type] ?? "building"} />
            </span>
            <span className="flex-1 text-base font-semibold text-ink-900">{p.name}</span>
            <StatusBadge status={p.data_status} />
          </li>
        ))}
      </ul>
      <EvidenceBadge evidence={card.evidence} />
    </article>
  );
}
