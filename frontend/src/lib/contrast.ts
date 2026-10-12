/** WCAG 2.x contrast helpers, used by tests to verify the "Lavender Sky" token pairs. */

export function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as [number, number, number];
}

/** Composite a foreground colour with alpha over an opaque background. */
export function blend(fg: string, alpha: number, bg: string): string {
  const f = hexToRgb(fg), b = hexToRgb(bg);
  const c = f.map((v, i) => Math.round(v * alpha + b[i] * (1 - alpha)));
  return "#" + c.map((v) => v.toString(16).padStart(2, "0")).join("");
}

function luminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex).map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(a: string, b: string): number {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}

export const TOKENS = {
  lavender50: "#F8F5FF", lavender100: "#EFE9FD", lavender200: "#DED3F8", lavender300: "#C7B5F0",
  primary600: "#6B4FC4", primary700: "#56399F", ink900: "#241B4B", ink600: "#4E4577", sky200: "#C9DDFF",
  star400: "#F2CF6B", success600: "#1F7A5C", warning600: "#9A6400", info600: "#3E5BA9", danger600: "#B3261E",
  white: "#FFFFFF",
};
