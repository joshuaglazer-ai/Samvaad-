/** Formatting helpers. Numbers shown here always come from backend tool results. */

/** Indian digit grouping: 118000 → "1,18,000". */
export function inr(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const neg = n < 0;
  const s = Math.round(Math.abs(n)).toString();
  if (s.length <= 3) return (neg ? "-" : "") + s;
  const tail = s.slice(-3);
  const head = s.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  return (neg ? "-" : "") + head + "," + tail;
}

export function rupees(n: number | null | undefined): string {
  return n === null || n === undefined ? "—" : `₹${inr(n)}`;
}

export function pct(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return `${Number.isInteger(n) ? n : n.toFixed(1)}%`;
}

const KN_DIGITS = "೦೧೨೩೪೫೬೭೮೯";
/** Optional Kannada numerals for display (the guardrail accepts both). */
export function toKannadaDigits(s: string): string {
  return s.replace(/\d/g, (d) => KN_DIGITS[Number(d)]);
}

export function minutesSince(iso: string, now: Date = new Date()): number {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return 0;
  return Math.max(0, Math.floor((now.getTime() - t) / 60000));
}

/** Clamp a value into [min, max]. */
export function clamp(v: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, v));
}

/** Percentage width (0–100) of `v` within [lo, hi], used for earnings range bars. */
export function rangePosition(v: number | null | undefined, lo: number | null | undefined, hi: number | null | undefined): number {
  if (v == null || lo == null || hi == null || hi <= lo) return 50;
  return clamp(((v - lo) / (hi - lo)) * 100, 0, 100);
}
