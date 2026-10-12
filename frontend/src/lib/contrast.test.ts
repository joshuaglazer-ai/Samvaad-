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
  ["text on eligible ladder step", T.ink900, blend(T.star400, 0.3, T.white)],
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
