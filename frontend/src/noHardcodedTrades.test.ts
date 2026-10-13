import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

// Update 3: every trade, sector, icon and synonym comes from the database through the API. This test fails if any
// seeded trade/sector slug (as a string literal or key) or English trade/sector name shows up in frontend/src.
// Lowercase everyday words in prose — e.g. the placeholder "For example: electrician, nurse…" — are allowed.

const SRC = resolve(__dirname);
const SEED = readFileSync(resolve(__dirname, "../../backend/seed/reference_data.py"), "utf-8");

const tradeSlugs = [...SEED.matchAll(/"slug":\s*"([a-z0-9-]+)",\s*"sector"/g)].map((m) => m[1]);
const sectorSlugs = [...SEED.matchAll(/\{"slug":\s*"([a-z0-9-]+)",\s*"icon"/g)].map((m) => m[1]);
const englishNames = [...SEED.matchAll(/"names":\s*L\("([^"]+)"/g)].map((m) => m[1]);

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    if (statSync(p).isDirectory()) return files(p);
    return /\.(tsx?|json)$/.test(f) && !/\.test\.tsx?$/.test(f) ? [p] : [];
  });
}

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

describe("no hard-coded trades or sectors in frontend/src", () => {
  it("reads the seeded catalogue", () => {
    expect(tradeSlugs.length).toBeGreaterThanOrEqual(8);
    expect(sectorSlugs.length).toBeGreaterThanOrEqual(4);
    expect(englishNames).toContain("Electrician");
  });

  it("finds no seeded slug or English name in the source", () => {
    const hits: string[] = [];
    const patterns = [
      ...[...tradeSlugs, ...sectorSlugs].map((s) => [s, new RegExp(`["'\`]${escape(s)}["'\`]`)] as const),
      ...englishNames.map((n) => [n, new RegExp(`\\b${escape(n)}\\b`)] as const),
    ];
    for (const f of files(SRC)) {
      const text = readFileSync(f, "utf-8");
      for (const [label, re] of patterns) if (re.test(text)) hits.push(`${f.slice(SRC.length + 1)}: ${label}`);
    }
    expect(hits).toEqual([]);
  });
});
