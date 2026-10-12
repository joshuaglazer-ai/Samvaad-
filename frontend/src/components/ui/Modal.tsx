import { useEffect, useRef, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import Icon from "./Icon";

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

export default function Modal({ open, onClose, title, children }: Props) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      prev?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink-900/40 p-4 sm:items-center" onClick={onClose}>
      <div
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="glass max-h-[90vh] w-full max-w-lg overflow-y-auto bg-white p-5 outline-none"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <h2 className="text-xl font-bold text-ink-900">{title}</h2>
          <button type="button" onClick={onClose} className="flex min-h-12 items-center gap-1 rounded-xl px-2 text-ink-600">
            <Icon name="close" size={20} />
            <span className="text-sm">{t("app.close")}</span>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
