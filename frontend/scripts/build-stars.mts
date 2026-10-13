/**
 * Build step: Yale Bright Star Catalogue (public domain, CDS V/50) → compact JSON + pre-rendered Lite-mode images.
 *
 *   node --experimental-strip-types scripts/build-stars.mts
 *
 * Input:  scripts/data/bsc5_catalog.gz  (downloaded from https://cdsarc.cds.unistra.fr/ftp/V/50/catalog.gz)
 * Output: src/data/stars.json            [[ra°, dec°, Vmag, B−V], …]  stars with Vmag ≤ 5.8 (4,103 stars)
 *         public/sky/stars-dark.png       the same catalogue sky, for Lite mode / static backgrounds (dark theme)
 *         public/sky/stars-light.png      only the brightest stars, faint, for the light (twilight) theme
 * Byte positions follow the catalogue ReadMe (RA/Dec J2000 at bytes 76–90, Vmag 103–107, B−V 110–114).
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { PNG } from "pngjs";
import { bvToKelvin, horizonVector, kelvinToRgb, localSiderealDeg, magToSizeAlpha, milkyWayPoints, type StarRow } from "../src/lib/sky.ts";

const MAG_LIMIT = 5.8;
const DEFAULT_BV = 0.6; // ~sun-like; used for the few stars without a measured B−V (documented)

const text = gunzipSync(readFileSync("scripts/data/bsc5_catalog.gz")).toString("latin1");
const rows: StarRow[] = [];
let missingBv = 0;
for (const line of text.split("\n")) {
  if (line.length < 107 || !line.slice(75, 77).trim() || !line.slice(102, 107).trim()) continue;
  const ra = (Number(line.slice(75, 77)) + Number(line.slice(77, 79)) / 60 + Number(line.slice(79, 83)) / 3600) * 15;
  const sign = line[83] === "-" ? -1 : 1;
  const dec = sign * (Number(line.slice(84, 86)) + Number(line.slice(86, 88)) / 60 + Number(line.slice(88, 90)) / 3600);
  const mag = Number(line.slice(102, 107));
  if (!(mag <= MAG_LIMIT)) continue;
  const bvRaw = line.slice(109, 114).trim();
  const bv = bvRaw ? Number(bvRaw) : (missingBv++, DEFAULT_BV);
  rows.push([+ra.toFixed(3), +dec.toFixed(3), +mag.toFixed(2), +bv.toFixed(2)]);
}
rows.sort((a, b) => a[2] - b[2]);
mkdirSync("src/data", { recursive: true });
writeFileSync("src/data/stars.json", JSON.stringify(rows));
console.log(`stars.json: ${rows.length} stars (Vmag ≤ ${MAG_LIMIT}), ${missingBv} without B−V (default ${DEFAULT_BV})`);

// ------------------------------------------------------------------ pre-render (same projection as the WebGL camera)
const W = 1600, H = 1000, FOV = 70, LOOK_ALT = 45;
// A fixed, pleasant evening: 15 Jan 2026, 21:00 IST — Orion, Sirius and the winter Milky Way in the southern sky.
const LST = localSiderealDeg(new Date(Date.UTC(2026, 0, 15, 15, 30)));
const a = (LOOK_ALT * Math.PI) / 180;
const f = [0, Math.sin(a), Math.cos(a)];        // looking south (+z), raised 45°
const r = [-1, 0, 0];                           // facing south, west is to the right
const u = [0, Math.cos(a), -Math.sin(a)];
const scale = H / 2 / Math.tan(((FOV / 2) * Math.PI) / 180);

function project(ra: number, dec: number): [number, number, number] | null {
  const [x, y, z, alt] = horizonVector(ra, dec, LST);
  const df = x * f[0] + y * f[1] + z * f[2];
  if (df <= 0.05 || alt < 0) return null;
  const sx = (x * r[0] + y * r[1] + z * r[2]) / df;
  const sy = (x * u[0] + y * u[1] + z * u[2]) / df;
  return [W / 2 + sx * scale, H / 2 - sy * scale, alt];
}

function render(file: string, opts: { maxMag: number; tint?: [number, number, number]; gain: number; milky: number }) {
  const acc = new Float32Array(W * H * 4); // premultiplied rgb + alpha
  const splat = (px: number, py: number, radius: number, alpha: number, rgb: [number, number, number]) => {
    const R = Math.ceil(radius * 3);
    for (let yy = Math.max(0, Math.floor(py - R)); yy <= Math.min(H - 1, Math.ceil(py + R)); yy++) {
      for (let xx = Math.max(0, Math.floor(px - R)); xx <= Math.min(W - 1, Math.ceil(px + R)); xx++) {
        const d2 = ((xx - px) ** 2 + (yy - py) ** 2) / (radius * radius);
        const core = Math.exp(-d2 * 2.2) + 0.08 * Math.exp(-d2 * 0.25); // Gaussian core + faint halo
        const v = alpha * core;
        if (v < 0.002) continue;
        const i = (yy * W + xx) * 4;
        acc[i] += rgb[0] * v; acc[i + 1] += rgb[1] * v; acc[i + 2] += rgb[2] * v; acc[i + 3] += v;
      }
    }
  };
  if (opts.milky > 0) {
    for (const [ra, dec, w] of milkyWayPoints()) {
      const p = project(ra, dec);
      if (p) splat(p[0], p[1], 9, w * opts.milky, opts.tint ?? [0.85, 0.87, 1]);
    }
  }
  for (const [ra, dec, mag, bv] of rows) {
    if (mag > opts.maxMag) continue;
    const p = project(ra, dec);
    if (!p) continue;
    const { size, alpha } = magToSizeAlpha(mag);
    const horizonFade = Math.min(1, p[2] / 0.12);
    splat(p[0], p[1], Math.max(0.6, size * 0.45), alpha * opts.gain * horizonFade, opts.tint ?? kelvinToRgb(bvToKelvin(bv)));
  }
  const png = new PNG({ width: W, height: H });
  for (let i = 0; i < W * H; i++) {
    const al = Math.min(1, acc[i * 4 + 3]);
    const k = acc[i * 4 + 3] > 0 ? 1 / acc[i * 4 + 3] : 0;
    png.data[i * 4] = Math.round(Math.min(1, acc[i * 4] * k) * 255);
    png.data[i * 4 + 1] = Math.round(Math.min(1, acc[i * 4 + 1] * k) * 255);
    png.data[i * 4 + 2] = Math.round(Math.min(1, acc[i * 4 + 2] * k) * 255);
    png.data[i * 4 + 3] = Math.round(al * 255);
  }
  mkdirSync("public/sky", { recursive: true });
  writeFileSync(file, PNG.sync.write(png, { colorType: 6 }));
  console.log(`${file}: ${(readFileSync(file).length / 1024).toFixed(0)} KB`);
}

render("public/sky/stars-dark.png", { maxMag: MAG_LIMIT, gain: 1, milky: 0.035 });
render("public/sky/stars-light.png", { maxMag: 2.6, tint: [0.31, 0.27, 0.47], gain: 0.5, milky: 0 });
