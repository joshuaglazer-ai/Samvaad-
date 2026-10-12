import { describe, expect, it } from "vitest";
import { inr, minutesSince, pct, rangePosition, rupees, toKannadaDigits } from "./format";

describe("format helpers", () => {
  it("groups digits the Indian way", () => {
    expect(inr(999)).toBe("999");
    expect(inr(15500)).toBe("15,500");
    expect(inr(118000)).toBe("1,18,000");
    expect(inr(12345678)).toBe("1,23,45,678");
    expect(inr(null)).toBe("—");
  });
  it("formats rupees and percentages", () => {
    expect(rupees(15500)).toBe("₹15,500");
    expect(rupees(undefined)).toBe("—");
    expect(pct(74)).toBe("74%");
    expect(pct(66.666)).toBe("66.7%");
  });
  it("converts to Kannada digits", () => {
    expect(toKannadaDigits("₹15,500")).toBe("₹೧೫,೫೦೦");
  });
  it("positions a value inside a range", () => {
    expect(rangePosition(15, 10, 20)).toBe(50);
    expect(rangePosition(30, 10, 20)).toBe(100);
    expect(rangePosition(null, 10, 20)).toBe(50);
  });
  it("computes waiting minutes", () => {
    const now = new Date("2026-01-01T10:30:00Z");
    expect(minutesSince("2026-01-01T10:00:00Z", now)).toBe(30);
    expect(minutesSince("bad", now)).toBe(0);
  });
});
