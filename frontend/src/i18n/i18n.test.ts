import { describe, expect, it } from "vitest";
import en from "./en.json";
import kn from "./kn.json";
import hi from "./hi.json";
import te from "./te.json";

type Tree = { [k: string]: string | Tree };

function flatten(t: Tree, prefix = ""): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(t)) {
    if (k.startsWith("_")) continue;
    const key = prefix ? `${prefix}.${k}` : k;
    if (typeof v === "string") out[key] = v;
    else Object.assign(out, flatten(v, key));
  }
  return out;
}

const placeholders = (s: string) => (s.match(/\{\{\s*\w+\s*\}\}/g) ?? []).map((p) => p.replace(/\s/g, "")).sort();
const base = flatten(en as Tree);
const SCRIPT: Record<string, RegExp> = { kn: /[ಀ-೿]/, hi: /[ऀ-ॿ]/, te: /[ఀ-౿]/ };

describe.each([["kn", kn], ["hi", hi], ["te", te]] as const)("%s translations", (lang, dict) => {
  const flat = flatten(dict as Tree);

  it("is marked for native review", () => {
    expect((dict as Record<string, unknown>)._review_status).toBe("needs_native_review");
  });
  it("has every key that English has (no missing strings)", () => {
    expect(Object.keys(base).filter((k) => !(k in flat))).toEqual([]);
  });
  it("has no extra keys", () => {
    expect(Object.keys(flat).filter((k) => !(k in base))).toEqual([]);
  });
  it("keeps the same {{placeholders}}", () => {
    const bad = Object.keys(base).filter((k) => k in flat && placeholders(base[k]).join() !== placeholders(flat[k]).join());
    expect(bad).toEqual([]);
  });
  it("is actually written in its own script (not left in English)", () => {
    const own = Object.values(flat).filter((v) => SCRIPT[lang].test(v)).length;
    expect(own / Object.keys(flat).length).toBeGreaterThan(0.85);
  });
});
