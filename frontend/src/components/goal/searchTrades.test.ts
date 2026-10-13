import { describe, expect, it } from "vitest";
import { searchTrades } from "./GoalPicker";
import type { Trade } from "../../lib/api";

// Fixture trades are made up for the test (never the seeded catalogue).
const trade = (slug: string, names: Trade["names"], synonyms: Trade["synonyms"], sector_name = "Area"): Trade => ({
  slug, name: names.en ?? slug, name_en: names.en ?? slug, names, synonyms, sector: "area", sector_name,
  nsqf_level: 4, duration_months: 6, icon: "tool", traits: [], data_status: "demo",
});

const TRADES = [
  trade("pump-fitter", { en: "Pump Fitter", hi: "पंप फिटर", kn: "ಪಂಪ್ ಫಿಟ್ಟರ್" }, { hi: ["pani ki motor"], te: ["మోటార్ పని"] }, "Water"),
  trade("tile-layer", { en: "Tile Layer", te: "టైల్స్ పని" }, { en: ["flooring"] }),
];

describe("searchTrades", () => {
  it("finds trades by name in any language", () => {
    expect(searchTrades(TRADES, "पंप").map((t) => t.slug)).toEqual(["pump-fitter"]);
    expect(searchTrades(TRADES, "ಪಂಪ್").map((t) => t.slug)).toEqual(["pump-fitter"]);
    expect(searchTrades(TRADES, "TILE").map((t) => t.slug)).toEqual(["tile-layer"]);
  });
  it("finds trades by everyday words and sector name", () => {
    expect(searchTrades(TRADES, "motor").map((t) => t.slug)).toEqual(["pump-fitter"]);
    expect(searchTrades(TRADES, "మోటార్").map((t) => t.slug)).toEqual(["pump-fitter"]);
    expect(searchTrades(TRADES, "floor").map((t) => t.slug)).toEqual(["tile-layer"]);
    expect(searchTrades(TRADES, "water").map((t) => t.slug)).toEqual(["pump-fitter"]);
  });
  it("returns nothing for an empty or unknown query", () => {
    expect(searchTrades(TRADES, "  ")).toEqual([]);
    expect(searchTrades(TRADES, "astronaut")).toEqual([]);
  });
});
