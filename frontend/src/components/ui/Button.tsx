import type { ButtonHTMLAttributes, ReactNode } from "react";
import Icon from "./Icon";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const styles: Record<Variant, string> = {
  primary: "bg-primary-600 text-white hover:bg-primary-700 shadow-[var(--shadow-soft)]",
  secondary: "bg-white/85 text-ink-900 border border-lavender-200 hover:border-primary-600 hover:bg-white",
  ghost: "bg-transparent text-primary-700 hover:bg-lavender-100",
  danger: "bg-danger-600 text-white hover:brightness-95",
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  icon?: string;
  iconRight?: string;
  size?: "md" | "lg";
  children: ReactNode;
}

/** Every button has an icon AND a visible text label; minimum 48×48 tap target. */
export default function Button({ variant = "primary", icon, iconRight, size = "md", className = "", children, ...rest }: Props) {
  const sz = size === "lg" ? "min-h-14 px-6 text-lg" : "min-h-12 px-4 text-base";
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 rounded-2xl font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${sz} ${styles[variant]} ${className}`}
      {...rest}
    >
      {icon && <Icon name={icon} />}
      <span>{children}</span>
      {iconRight && <Icon name={iconRight} />}
    </button>
  );
}
