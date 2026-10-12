import Icon from "./Icon";

interface Props {
  icon: string;
  label: string;
  selected?: boolean;
  onClick: () => void;
  badge?: string;
  description?: string;
  role?: "checkbox" | "radio";
}

/** Large picture card for low-literacy selection: icon + text, ≥ 48px tap target, clear selected state. */
export default function IconCard({ icon, label, selected = false, onClick, badge, description, role = "radio" }: Props) {
  return (
    <button
      type="button"
      role={role}
      aria-checked={selected}
      onClick={onClick}
      className={`relative flex min-h-24 w-full flex-col items-center justify-center gap-2 rounded-[20px] border-2 p-3 text-center transition-colors ${
        selected
          ? "border-primary-600 bg-white text-ink-900 shadow-[var(--shadow-soft)]"
          : "border-lavender-200 bg-white/75 text-ink-900 hover:border-primary-600"
      }`}
    >
      {badge && (
        <span className="absolute left-2 top-2 rounded-full bg-primary-600 px-2 py-0.5 text-sm font-bold text-white">{badge}</span>
      )}
      {selected && (
        <span className="absolute right-2 top-2 rounded-full bg-primary-600 p-1 text-white" aria-hidden="true">
          <Icon name="check" size={16} strokeWidth={3} />
        </span>
      )}
      <span className={`grid h-12 w-12 place-items-center rounded-2xl ${selected ? "bg-primary-600 text-white" : "bg-lavender-100 text-primary-700"}`}>
        <Icon name={icon} size={28} />
      </span>
      <span className="text-base font-semibold leading-tight">{label}</span>
      {description && <span className="text-sm text-ink-600">{description}</span>}
    </button>
  );
}
