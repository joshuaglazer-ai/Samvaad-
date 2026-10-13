/**
 * Shared sky maths for the real star catalogue (used by the WebGL sky, the build-time pre-render, and tests).
 *
 * Data: Yale Bright Star Catalogue, 5th revised ed. (Hoffleit & Warren 1991), public domain, via CDS (V/50).
 * Stars are placed with their real right ascension / declination and shown as seen from Bengaluru (≈13°N, 77.6°E).
 */

export const OBSERVER = { latDeg: 12.97, lonDeg: 77.59 };

/** Compact catalogue row: [RA degrees, Dec degrees, visual magnitude, B–V colour index]. */
export type StarRow = [number, number, number, number];

const D2R = Math.PI / 180;

/** Greenwich mean sidereal time in degrees for a JS Date (IAU 1982 approximation, good to ~0.1 s). */
export function gmstDeg(date: Date): number {
  const jd = date.getTime() / 86400000 + 2440587.5;
  const t = (jd - 2451545.0) / 36525;
  const g = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t * t - (t * t * t) / 38710000;
  return ((g % 360) + 360) % 360;
}

export function localSiderealDeg(date: Date, lonDeg = OBSERVER.lonDeg): number {
  return (gmstDeg(date) + lonDeg + 360) % 360;
}

/**
 * Equatorial (RA, Dec) → local horizon direction as a unit vector in world space:
 * x = East, y = Up (zenith), z = South (so North is −z). Returns [x, y, z, altitudeRad].
 */
export function horizonVector(raDeg: number, decDeg: number, lstDeg: number, latDeg = OBSERVER.latDeg): [number, number, number, number] {
  const h = (lstDeg - raDeg) * D2R;
  const d = decDeg * D2R;
  const p = latDeg * D2R;
  const sinAlt = Math.sin(d) * Math.sin(p) + Math.cos(d) * Math.cos(p) * Math.cos(h);
  const alt = Math.asin(Math.max(-1, Math.min(1, sinAlt)));
  const cosAlt = Math.cos(alt);
  // Azimuth measured from North towards East.
  const sinAzCos = -Math.cos(d) * Math.sin(h);
  const cosAzCos = Math.sin(d) * Math.cos(p) - Math.cos(d) * Math.sin(p) * Math.cos(h);
  const norm = Math.hypot(sinAzCos, cosAzCos) || 1;
  const sinAz = sinAzCos / norm;
  const cosAz = cosAzCos / norm;
  return [cosAlt * sinAz, sinAlt, -cosAlt * cosAz, alt];
}

/** B–V colour index → effective temperature (Ballesteros 2012). */
export function bvToKelvin(bv: number): number {
  const b = Math.max(-0.4, Math.min(2.0, bv));
  return 4600 * (1 / (0.92 * b + 1.7) + 1 / (0.92 * b + 0.62));
}

/** Black-body temperature → RGB 0..1 (Tanner Helland approximation), softened towards white so colours stay subtle. */
export function kelvinToRgb(k: number, softness = 0.55): [number, number, number] {
  const t = k / 100;
  let r: number, g: number, b: number;
  if (t <= 66) {
    r = 255;
    g = 99.4708025861 * Math.log(t) - 161.1195681661;
    b = t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307;
  } else {
    r = 329.698727446 * Math.pow(t - 60, -0.1332047592);
    g = 288.1221695283 * Math.pow(t - 60, -0.0755148492);
    b = 255;
  }
  const c = [r, g, b].map((v) => Math.max(0, Math.min(255, v)) / 255);
  return c.map((v) => v + (1 - v) * softness) as [number, number, number];
}

/**
 * Apparent magnitude → point size (px at DPR 1) and opacity. Flux grows 2.512× per magnitude; we use a
 * log-compressed scale so most stars are tiny faint points and only a handful are bright.
 */
export function magToSizeAlpha(mag: number): { size: number; alpha: number } {
  const brightness = Math.pow(10, -0.4 * (mag - 6.0)); // 1 at mag 6, ~250 at mag 0
  const l = Math.log2(brightness);
  return { size: Math.min(11, 1.1 + 0.95 * l), alpha: Math.max(0.18, Math.min(1, 0.2 + 0.11 * l)) };
}

/** Galactic (l, b) → equatorial (RA, Dec) in degrees, J2000. Used to lay out the faint Milky Way band. */
export function galacticToEquatorial(lDeg: number, bDeg: number): [number, number] {
  const l = lDeg * D2R;
  const b = bDeg * D2R;
  const g = [Math.cos(b) * Math.cos(l), Math.cos(b) * Math.sin(l), Math.sin(b)];
  // Transpose of the J2000 equatorial → galactic rotation matrix.
  const T = [
    [-0.0548755604, -0.873437090, -0.4838350155],
    [0.4941094279, -0.44482963, 0.7469822445],
    [-0.867666149, -0.1980763734, 0.4559837762],
  ];
  const x = T[0][0] * g[0] + T[1][0] * g[1] + T[2][0] * g[2];
  const y = T[0][1] * g[0] + T[1][1] * g[1] + T[2][1] * g[2];
  const z = T[0][2] * g[0] + T[1][2] * g[1] + T[2][2] * g[2];
  const ra = (Math.atan2(y, x) / D2R + 360) % 360;
  const dec = Math.asin(Math.max(-1, Math.min(1, z))) / D2R;
  return [ra, dec];
}

/** Deterministic PRNG so the Milky Way layout is identical in the WebGL scene and the pre-rendered image. */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Faint Milky Way band: soft points along the galactic plane (Gaussian in latitude, brighter and wider towards the
 * galactic centre). This is a visual texture, not catalogue data, and is drawn at very low opacity.
 * Returns rows [RA°, Dec°, weight 0..1].
 */
export function milkyWayPoints(n = 5000, seed = 7): [number, number, number][] {
  const rnd = mulberry32(seed);
  const gauss = () => Math.sqrt(-2 * Math.log(rnd() + 1e-9)) * Math.cos(2 * Math.PI * rnd());
  const out: [number, number, number][] = [];
  for (let i = 0; i < n; i++) {
    const l = rnd() * 360;
    const towardsCentre = Math.cos((l * Math.PI) / 180) * 0.5 + 0.5; // 1 at l = 0
    const width = 5 + 7 * towardsCentre;
    const b = gauss() * width;
    // patchy: modulate with a few low-frequency waves so the band is uneven, like dust lanes
    const patch = 0.55 + 0.45 * Math.sin(l * 0.11 + 1.3) * Math.sin(l * 0.037 + b * 0.2);
    const [ra, dec] = galacticToEquatorial(l, b);
    out.push([ra, dec, Math.max(0, (0.35 + 0.65 * towardsCentre) * patch)]);
  }
  return out;
}
