/** Device capability checks used to decide Lite mode (no WebGL, minimal motion). */

export interface DeviceSignals {
  deviceMemory?: number;
  hardwareConcurrency?: number;
  prefersReducedMotion: boolean;
  saveData: boolean;
  effectiveType?: string;
  webgl: boolean;
}

export function hasWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return !!(canvas.getContext("webgl2") || canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

export function readSignals(): DeviceSignals {
  const nav = navigator as Navigator & {
    deviceMemory?: number;
    connection?: { saveData?: boolean; effectiveType?: string };
  };
  let reduced = false;
  try {
    reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
  } catch {
    reduced = false;
  }
  return {
    deviceMemory: nav.deviceMemory,
    hardwareConcurrency: nav.hardwareConcurrency,
    prefersReducedMotion: reduced,
    saveData: !!nav.connection?.saveData,
    effectiveType: nav.connection?.effectiveType,
    webgl: hasWebGL(),
  };
}

/** Pure rule so it can be unit-tested. Returns the reasons Lite mode should be on (empty = off). */
export function liteReasons(s: DeviceSignals): string[] {
  const reasons: string[] = [];
  if (s.deviceMemory !== undefined && s.deviceMemory <= 2) reasons.push("low_memory");
  if (s.hardwareConcurrency !== undefined && s.hardwareConcurrency <= 4) reasons.push("few_cores");
  if (s.prefersReducedMotion) reasons.push("reduced_motion");
  if (s.saveData) reasons.push("save_data");
  if (s.effectiveType && ["slow-2g", "2g", "3g"].includes(s.effectiveType)) reasons.push("slow_network");
  if (!s.webgl) reasons.push("no_webgl");
  return reasons;
}

const KEY = "samvaad.lite";

/** Manual override from the header toggle wins over auto-detection. */
export function initialLite(): boolean {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "1") return true;
    if (saved === "0") return false;
  } catch {
    /* ignore */
  }
  return liteReasons(readSignals()).length > 0;
}

export function saveLite(on: boolean) {
  try {
    localStorage.setItem(KEY, on ? "1" : "0");
  } catch {
    /* ignore */
  }
}
