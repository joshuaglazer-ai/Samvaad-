import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { initialLite, saveLite } from "./device";
import type { Lang } from "./languages";

export type Speaker = "learner" | "parent" | "helper";
export type Theme = "light" | "dark";

const THEME_KEY = "samvaad.theme";

function systemTheme(): Theme {
  try {
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  } catch {
    return "light";
  }
}

/** A saved manual choice wins; otherwise follow the system setting. */
export function savedTheme(): Theme | null {
  try {
    const v = localStorage.getItem(THEME_KEY);
    return v === "dark" || v === "light" ? v : null;
  } catch {
    return null;
  }
}

export type ParticipationMode = "together" | "two_devices" | "learner_only";
/** Which family member this phone belongs to in a two-phone session. */
export type DeviceRole = "learner" | "parent";

export interface Profile {
  language: Lang;
  participation_mode: ParticipationMode;
  role: DeviceRole;
  family_code?: string | null;
  district?: string;
  learner_education?: string;
  learner_interests: string[];
  top_concerns: string[];
  income_bracket?: string | null;
  helper_mode: boolean;
}

interface AppState {
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
  profile: Profile;
  setProfile: (p: Partial<Profile>) => void;
  lite: boolean;
  setLite: (on: boolean) => void;
  theme: Theme;
  setTheme: (t: Theme) => void;
  readAloud: boolean;
  setReadAloud: (on: boolean) => void;
  disclaimerSeen: boolean;
  markDisclaimerSeen: () => void;
  reset: () => void;
}

const emptyProfile: Profile = {
  language: "en",
  participation_mode: "together",
  role: "learner",
  family_code: null,
  learner_interests: [],
  top_concerns: [],
  income_bracket: null,
  helper_mode: false,
};

const Ctx = createContext<AppState | null>(null);

function load<T>(key: string, fallback: T): T {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}
function store(key: string, value: unknown) {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage may be unavailable */
  }
}

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionIdState] = useState<string | null>(() => load("samvaad.session", null));
  const [profile, setProfileState] = useState<Profile>(() => ({ ...emptyProfile, ...load("samvaad.profile", emptyProfile) }));
  const [lite, setLiteState] = useState<boolean>(() => initialLite());
  const [theme, setThemeState] = useState<Theme>(() => savedTheme() ?? systemTheme());

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#000000" : "#6B4FC4");
  }, [theme]);

  // Follow the system setting until the user picks a theme in the header.
  useEffect(() => {
    let mq: MediaQueryList | undefined;
    try {
      mq = window.matchMedia("(prefers-color-scheme: dark)");
    } catch {
      return;
    }
    const onChange = () => {
      if (!savedTheme()) setThemeState(mq!.matches ? "dark" : "light");
    };
    mq.addEventListener?.("change", onChange);
    return () => mq?.removeEventListener?.("change", onChange);
  }, []);
  const [readAloud, setReadAloud] = useState<boolean>(() => load("samvaad.readAloud", true));
  const [disclaimerSeen, setDisclaimerSeen] = useState<boolean>(() => load("samvaad.disclaimer", false));

  useEffect(() => {
    document.documentElement.classList.toggle("lite", lite);
  }, [lite]);

  const setSessionId = useCallback((id: string | null) => {
    setSessionIdState(id);
    store("samvaad.session", id);
  }, []);
  const setProfile = useCallback((p: Partial<Profile>) => {
    setProfileState((prev) => {
      const next = { ...prev, ...p };
      store("samvaad.profile", next);
      return next;
    });
  }, []);
  const setLite = useCallback((on: boolean) => {
    setLiteState(on);
    saveLite(on);
  }, []);
  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    try {
      localStorage.setItem(THEME_KEY, t);
    } catch {
      /* storage may be blocked; the choice lasts for this visit */
    }
  }, []);
  const setRead = useCallback((on: boolean) => {
    setReadAloud(on);
    store("samvaad.readAloud", on);
  }, []);
  const markDisclaimerSeen = useCallback(() => {
    setDisclaimerSeen(true);
    store("samvaad.disclaimer", true);
  }, []);
  const reset = useCallback(() => {
    setSessionId(null);
    setProfileState(emptyProfile);
    store("samvaad.profile", emptyProfile);
    setDisclaimerSeen(false);
    store("samvaad.disclaimer", false);
  }, [setSessionId]);

  const value = useMemo(
    () => ({
      sessionId, setSessionId, profile, setProfile, lite, setLite, theme, setTheme,
      readAloud, setReadAloud: setRead, disclaimerSeen, markDisclaimerSeen, reset,
    }),
    [sessionId, setSessionId, profile, setProfile, lite, setLite, theme, setTheme, readAloud, setRead, disclaimerSeen, markDisclaimerSeen, reset],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppState(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAppState outside provider");
  return v;
}
