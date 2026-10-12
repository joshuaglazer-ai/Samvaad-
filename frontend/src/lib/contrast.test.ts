import { describe, expect, it } from "vitest";
import { blend, contrast, TOKENS as T } from "./contrast";

// Every text/background pair actually used in the UI must meet WCAG AA (4.5:1 for normal text).
const PAIRS: [string, string, string][] = [
  ["body text on page top", T.ink900, T.lavender50],
  ["body text on page bottom (sky)", T.ink900, T.sky200],
  ["secondary text on page bottom (sky)", T.ink600, T.sky200],
  ["secondary text on glass card", T.ink600, blend(T.white, 0.72, T.lavender50)],
  ["secondary text on lavender-100", T.ink600, T.lavender100],
  ["body text on lavender-100", T.ink900, T.lavender100],
  ["primary button label", T.white, T.primary600],
  ["primary button hover label", T.white, T.primary700],
  ["link / ghost button on white", T.primary700, T.white],
  ["link / ghost button on lavender-100", T.primary700, T.lavender100],
  ["user chat bubble", T.white, T.primary600],
  ["Verified badge", T.white, T.success600],
  ["Historical badge", T.white, T.warning600],
  ["Demo badge", T.white, T.info600],
  ["Unavailable badge", T.white, T.ink600],
  ["Demo label text on card", T.info600, T.white],
  ["error text", T.danger600, T.white],
  ["text on star highlight", T.ink900, blend(T.star400, 0.25, T.white)],
  ["text on eligible ladder step", T.ink900, blend(T.star400, 0.25, T.white)],
  ["secondary text on eligible ladder step", T.ink600, blend(T.star400, 0.25, T.white)],
  ["Lite mode button (on)", T.white, T.primary600],
];

describe("WCAG AA contrast for Lavender Sky tokens", () => {
  it.each(PAIRS)("%s ≥ 4.5:1", (_name, fg, bg) => {
    expect(contrast(fg, bg)).toBeGreaterThanOrEqual(4.5);
  });

  it("decorative tokens are never used for text (documented: lavender-300/500 fail)", () => {
    expect(contrast(T.ink900, T.lavender300)).toBeGreaterThan(4.5); // ink on it is fine…
    expect(contrast(T.white, T.lavender300)).toBeLessThan(4.5); // …but white on it is not, so we never do it
  });
});

// ---------------------------------------------------------------- dark mode (pure black, Update 2)
const D = {
  bg: "#000000", surface1: "#0B0B0B", surface2: "#141414", border: "#262626", text: "#F5F5F5", text2: "#A3A3A3",
  button: "#FFFFFF", buttonHover: "#E5E5E5", green: "#4ADE80", amber: "#FBBF24", blue: "#93C5FD", grey: "#D4D4D4",
  danger: "#F87171", gold: "#F2CF6B",
};
const DARK_PAIRS: [string, string, string][] = [
  ["body text on page", D.text, D.bg],
  ["body text on surface", D.text, D.surface2],
  ["body text on inset surface", D.text, D.surface1],
  ["secondary text on page", D.text2, D.bg],
  ["secondary text on surface", D.text2, D.surface2],
  ["secondary text on inset surface", D.text2, D.surface1],
  ["primary button label (near-black on white)", D.surface2, D.button],
  ["primary button hover label", D.surface2, D.buttonHover],
  ["user chat bubble", D.surface2, D.button],
  ["links / ghost buttons", D.buttonHover, D.surface2],
  ["Verified badge", D.green, D.surface2],
  ["Historical badge", D.amber, D.surface2],
  ["Demo badge", D.blue, D.surface2],
  ["Unavailable badge", D.grey, D.surface2],
  ["Demo label text", D.blue, D.surface2],
  ["info banner", D.surface2, D.blue],
  ["error text", D.danger, D.surface2],
  ["danger button label", D.surface2, D.danger],
  ["reading highlight", D.text, blend(D.gold, 0.35, D.surface2)],
  ["eligible ladder step", D.text, blend(D.gold, 0.12, D.surface2)],
  ["eligible ladder step secondary text", D.text2, blend(D.gold, 0.12, D.surface2)],
  ["chart axis text", D.text2, D.surface2],
];

describe("WCAG AA contrast for dark mode", () => {
  it.each(DARK_PAIRS)("%s ≥ 4.5:1", (_name, fg, bg) => {
    expect(contrast(fg, bg)).toBeGreaterThanOrEqual(4.5);
  });
  it("focus ring (white) is clearly visible on every dark surface (≥ 3:1 non-text)", () => {
    for (const bg of [D.bg, D.surface1, D.surface2]) expect(contrast("#FFFFFF", bg)).toBeGreaterThanOrEqual(3);
  });
});
