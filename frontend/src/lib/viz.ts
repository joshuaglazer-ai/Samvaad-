/**
 * Chart colours per theme. Categorical hues are assigned in a FIXED order per entity (never by rank).
 *
 * Light: validated on the card surface #fbfaff (worst adjacent CVD ΔE 9.1, normal-vision ΔE 19.6); three hues are
 *   below 3:1 contrast, so every chart ships a legend, tooltips and a table view.
 * Dark (pure black, no lavender): neutral greys for single-series charts and magnitudes; categorical identity uses the
 *   dark steps of the same hues with slot 7 changed from violet to cyan (#2ba3c4) — validated on #141414: all gates
 *   pass (worst adjacent CVD ΔE 8.4, normal-vision ΔE 19.3, all ≥ 3:1 contrast). Text never uses series colours.
 */
import { useAppState } from "./state";

export const CONCERN_ORDER = ["income", "job_security", "social_status", "safety", "cost", "distance_migration", "degree_first", "other"];
export const ALIGN_ORDER = ["earning_soon", "near_home", "respect", "study_further", "safety"];

const LIGHT = {
  categorical: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
  sequential: ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
  series1: "#2a78d6", series2: "#eb6834", muted: "#8f8aa6", suppressed: "#c9c6d6", zeroLine: "#9a96aa",
  grid: "#e4ddf7", axis: "#4E4577", gap: "#ffffff",
  tooltip: { borderRadius: 12, border: "1px solid #DED3F8", fontSize: 13, color: "#241B4B", background: "#ffffff" },
};

const DARK: typeof LIGHT = {
  categorical: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#2ba3c4", "#e66767"],
  // Grey ramp: darker = less resistance, lighter = more (reads as "brighter = more" on black).
  sequential: ["#262626", "#404040", "#525252", "#737373", "#a3a3a3", "#d4d4d4", "#f5f5f5"],
  series1: "#E5E5E5", series2: "#737373", muted: "#525252", suppressed: "#262626", zeroLine: "#525252",
  grid: "#262626", axis: "#A3A3A3", gap: "#141414",
  tooltip: { borderRadius: 12, border: "1px solid #262626", fontSize: 13, color: "#F5F5F5", background: "#141414" },
};

export type VizTheme = typeof LIGHT & {
  concernColor: Record<string, string>;
  alignColor: Record<string, string>;
  sequentialColor: (value: number, max: number) => string;
};

export function vizFor(theme: "light" | "dark"): VizTheme {
  const base = theme === "dark" ? DARK : LIGHT;
  return {
    ...base,
    concernColor: Object.fromEntries(CONCERN_ORDER.map((c, i) => [c, base.categorical[i]])),
    alignColor: Object.fromEntries(ALIGN_ORDER.map((c, i) => [c, base.categorical[i]])),
    sequentialColor: (value: number, max: number) => {
      const s = base.sequential;
      if (max <= 0) return s[1];
      const i = Math.min(s.length - 1, Math.floor((value / max) * (s.length - 1) + 0.5));
      return s[Math.max(1, i)];
    },
  };
}

export function useViz(): VizTheme {
  const { theme } = useAppState();
  return vizFor(theme);
}
