/**
 * Chart colours. Categorical hues are assigned in a FIXED order per entity (never by rank) and were validated
 * with the dataviz validator on the card surface #fbfaff: all hard gates pass (worst adjacent CVD ΔE 9.1,
 * normal-vision ΔE 19.6). Three hues are below 3:1 contrast, so every chart ships a legend, tooltips and a
 * table view. Text never uses series colours.
 */
export const CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];

export const CONCERN_ORDER = ["income", "job_security", "social_status", "safety", "cost", "distance_migration", "degree_first", "other"];
export const CONCERN_COLOR: Record<string, string> = Object.fromEntries(CONCERN_ORDER.map((c, i) => [c, CATEGORICAL[i]]));

export const ALIGN_ORDER = ["earning_soon", "near_home", "respect", "study_further", "safety"];
export const ALIGN_COLOR: Record<string, string> = Object.fromEntries(ALIGN_ORDER.map((c, i) => [c, CATEGORICAL[i]]));

/** Sequential single-hue ramp (light → dark) for magnitudes such as resistance share. */
export const SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"];

export function sequentialColor(value: number, max: number): string {
  if (max <= 0) return SEQUENTIAL[0];
  const i = Math.min(SEQUENTIAL.length - 1, Math.floor((value / max) * (SEQUENTIAL.length - 1) + 0.5));
  return SEQUENTIAL[Math.max(1, i)];
}

export const GRID = "#e4ddf7";
export const AXIS_TEXT = "#4E4577";
