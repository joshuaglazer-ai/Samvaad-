import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import Button from "./Button";
import Icon from "./Icon";

interface Props {
  storageKey: string;
  title: string;
  label: string;
  submit: string;
  verify: (pin: string) => Promise<void>;
  children: (pin: string, logout: () => void) => ReactNode;
}

function load(key: string): string {
  try {
    return sessionStorage.getItem(key) ?? "";
  } catch {
    return "";
  }
}

/** Demo-grade PIN gate for counsellor/admin screens (documented as such). */
export default function PinGate({ storageKey, title, label, submit, verify, children }: Props) {
  const { t } = useTranslation();
  const [pin, setPin] = useState(() => load(storageKey));
  const [ok, setOk] = useState(() => !!load(storageKey));
  const [draft, setDraft] = useState("");
  const [error, setError] = useState(false);

  const logout = () => {
    try {
      sessionStorage.removeItem(storageKey);
    } catch {
      /* ignore */
    }
    setOk(false);
    setPin("");
  };

  if (ok && pin) return <>{children(pin, logout)}</>;

  return (
    <form
      className="glass mx-auto mt-8 max-w-sm space-y-4 p-6"
      onSubmit={async (e) => {
        e.preventDefault();
        try {
          await verify(draft);
          try {
            sessionStorage.setItem(storageKey, draft);
          } catch {
            /* ignore */
          }
          setPin(draft);
          setOk(true);
          setError(false);
        } catch {
          setError(true);
        }
      }}
    >
      <h1 className="flex items-center gap-2 text-2xl font-bold text-ink-900"><Icon name="lock" className="text-primary-700" />{title}</h1>
      <label className="block">
        <span className="mb-1 block font-semibold text-ink-900">{label}</span>
        <input type="password" value={draft} onChange={(e) => setDraft(e.target.value)} autoComplete="current-password"
          className="min-h-12 w-full rounded-2xl border border-lavender-200 bg-white px-4 text-lg text-ink-900" />
      </label>
      {error && <p role="alert" className="text-danger-600">{t("app.error")}</p>}
      <Button type="submit" icon="arrowRight" className="w-full">{submit}</Button>
      <p className="text-sm text-ink-600">{t("counsellor.demoAuth")}</p>
    </form>
  );
}
