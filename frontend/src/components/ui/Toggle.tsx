import Icon from "./Icon";

interface Props {
  checked: boolean;
  onChange: (on: boolean) => void;
  label: string;
  icon?: string;
}

export default function Toggle({ checked, onChange, label, icon }: Props) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="flex min-h-12 items-center gap-3 rounded-2xl px-2 text-left text-base font-medium text-ink-900"
    >
      {icon && <Icon name={icon} size={22} className="text-primary-700" />}
      <span>{label}</span>
      <span
        aria-hidden="true"
        className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors ${checked ? "bg-primary-600" : "bg-lavender-200"}`}
      >
        <span className={`h-5 w-5 rounded-full bg-white shadow transition-transform ${checked ? "translate-x-6" : "translate-x-1"}`} />
      </span>
    </button>
  );
}
