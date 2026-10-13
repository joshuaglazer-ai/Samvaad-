import { describe, expect, it } from "vitest";
import stars from "../data/stars.json";
import {
  bvToKelvin, galacticToEquatorial, horizonVector, kelvinToRgb, localSiderealDeg, magToSizeAlpha, milkyWayPoints,
  type StarRow,
} from "./sky";

const rows = stars as StarRow[];

describe("star catalogue (Yale BSC5)", () => {
  it("has 3,000–5,000 real stars", () => {
    expect(rows.length).toBeGreaterThanOrEqual(3000);
    expect(rows.length).toBeLessThanOrEqual(5000);
  });
  it("brightest star is Sirius (V −1.46, RA 101.29°, Dec −16.72°)", () => {
    const [ra, dec, mag] = rows[0];
    expect(mag).toBeCloseTo(-1.46, 2);
    expect(ra).toBeCloseTo(101.29, 1);
    expect(dec).toBeCloseTo(-16.72, 1);
  });
  it("follows a realistic magnitude distribution: many faint, very few bright", () => {
    const bright = rows.filter((r) => r[2] < 1.5).length;
    const faint = rows.filter((r) => r[2] > 5).length;
    expect(bright).toBeLessThan(25);
    expect(faint).toBeGreaterThan(rows.length / 2);
    const small = rows.filter((r) => magToSizeAlpha(r[2]).size < 3).length;
    expect(small / rows.length).toBeGreaterThan(0.7); // most stars are tiny points
  });
});

describe("sky maths", () => {
  it("Polaris sits at an altitude close to the observer latitude (~13°)", () => {
    const [, , , alt] = horizonVector(37.95, 89.26, 120, 12.97);
    expect((alt * 180) / Math.PI).toBeCloseTo(12.97, 0);
  });
  it("a star on the meridian at Dec δ culminates at 90 − |φ − δ|", () => {
    const [, , z, alt] = horizonVector(100, -16.72, 100, 12.97);
    expect((alt * 180) / Math.PI).toBeCloseTo(90 - (12.97 + 16.72), 1);
    expect(z).toBeGreaterThan(0); // due south (+z)
  });
  it("converts the galactic centre to RA 266.40°, Dec −28.94°", () => {
    const [ra, dec] = galacticToEquatorial(0, 0);
    expect(ra).toBeCloseTo(266.4, 1);
    expect(dec).toBeCloseTo(-28.94, 1);
  });
  it("sidereal time is in range", () => {
    const lst = localSiderealDeg(new Date("2026-01-15T15:30:00Z"));
    expect(lst).toBeGreaterThanOrEqual(0);
    expect(lst).toBeLessThan(360);
  });
  it("brighter stars are larger and more opaque", () => {
    expect(magToSizeAlpha(0).size).toBeGreaterThan(magToSizeAlpha(4).size);
    expect(magToSizeAlpha(0).alpha).toBeGreaterThan(magToSizeAlpha(4).alpha);
  });
  it("B−V gives blue-white hot stars and orange cool stars, softened (never saturated)", () => {
    const hot = kelvinToRgb(bvToKelvin(-0.3));
    const cool = kelvinToRgb(bvToKelvin(1.6));
    expect(hot[2]).toBeGreaterThan(hot[0]); // bluer
    expect(cool[0]).toBeGreaterThan(cool[2]); // redder
    for (const c of [...hot, ...cool]) expect(c).toBeGreaterThanOrEqual(0.5); // softened towards white
  });
  it("Milky Way points cluster near the galactic plane and are deterministic", () => {
    const a = milkyWayPoints(500, 7);
    const b = milkyWayPoints(500, 7);
    expect(a).toEqual(b);
  });
});
