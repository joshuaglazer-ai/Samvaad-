import Icon from "../ui/Icon";

const ICONS: [RegExp, string][] = [
  [/earn|ಸಂಪಾದ|salary|ಸಂಬಳ/i, "rupee"],
  [/step|ಹಂತ|ladder|ಏಣಿ/i, "ladder"],
  [/cost|ಖರ್ಚು|fee|ಶುಲ್ಕ/i, "wallet"],
  [/centre|ಕೇಂದ್ರ/i, "pin"],
  [/counsel|ಸಲಹೆಗಾರ/i, "chat"],
  [/option|ಆಯ್ಕೆ/i, "sparkle"],
  [/safe|ಸುರಕ್ಷ/i, "shield"],
  [/degree|ಪದವಿ/i, "graduation"],
  [/job|ಕೆಲಸ/i, "briefcase"],
];

export default function QuickReplies({ items, onPick, disabled }: { items: string[]; onPick: (s: string) => void; disabled?: boolean }) {
  if (!items.length) return null;
  return (
    <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 sm:flex-wrap sm:overflow-visible">
      {items.map((q) => (
        <button
          key={q}
          type="button"
          disabled={disabled}
          onClick={() => onPick(q)}
          className="flex min-h-12 shrink-0 items-center gap-2 whitespace-nowrap rounded-full border-2 border-lavender-200 bg-white/90 px-4 text-base font-semibold text-ink-900 hover:border-primary-600 disabled:opacity-50"
        >
          <Icon name={ICONS.find(([re]) => re.test(q))?.[1] ?? "question"} size={20} className="text-primary-700" />
          {q}
        </button>
      ))}
    </div>
  );
}
