import { useTranslation } from "react-i18next";

/** 5 face icons, 1 = very worried … 5 = confident. Each face has a visible text label. */
const MOUTHS = [
  "M8 17c1.2-2 6.8-2 8 0", // 1 big frown
  "M8.5 16.5c1.2-1 5.8-1 7 0", // 2 slight frown
  "M8.5 16h7", // 3 neutral
  "M8.5 15.5c1.2 1 5.8 1 7 0", // 4 slight smile
  "M8 15c1.2 2.4 6.8 2.4 8 0", // 5 big smile
];
const FILLS = ["#EFE9FD", "#EFE9FD", "#F8F5FF", "#FDF6DF", "#FBEFC5"];

export function Face({ value, size = 44 }: { value: number; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10" fill={FILLS[value - 1]} stroke="#56399F" strokeWidth="1.4" />
      <circle cx="9" cy="10" r="1.1" fill="#241B4B" />
      <circle cx="15" cy="10" r="1.1" fill="#241B4B" />
      <path d={MOUTHS[value - 1]} fill="none" stroke="#241B4B" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

interface Props {
  label: string;
  value: number | null;
  onChange: (v: number) => void;
}

export default function MoodCheck({ label, value, onChange }: Props) {
  const { t } = useTranslation();
  return (
    <fieldset className="glass p-4">
      <legend className="sr-only">{label}</legend>
      <p className="mb-3 text-lg font-bold text-ink-900" aria-hidden="true">{label}</p>
      <div className="grid grid-cols-5 gap-1.5" role="radiogroup" aria-label={label}>
        {[1, 2, 3, 4, 5].map((v) => (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={value === v}
            onClick={() => onChange(v)}
            className={`flex min-h-24 flex-col items-center justify-start gap-1 rounded-2xl border-2 px-1 py-2 text-center text-xs font-semibold leading-tight sm:text-sm ${
              value === v ? "border-primary-600 bg-white" : "border-transparent bg-white/60 hover:border-lavender-300"
            }`}
          >
            <Face value={v} />
            <span className="text-ink-900">{t(`mood.faces.${v}`)}</span>
          </button>
        ))}
      </div>
    </fieldset>
  );
}
