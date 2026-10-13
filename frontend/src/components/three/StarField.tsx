import { useEffect, useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import catalogue from "../../data/stars.json";
import { bvToKelvin, kelvinToRgb, localSiderealDeg, magToSizeAlpha, milkyWayPoints, OBSERVER, type StarRow } from "../../lib/sky";

/**
 * Real night sky from the Yale Bright Star Catalogue (public domain): 4,103 stars (V ≤ 5.8) at their true positions,
 * shown as seen from Bengaluru at the current local time. Size and opacity follow apparent magnitude; colour follows
 * the B–V index (softened). The sky turns slowly about the celestial pole (Earth's rotation, sped up 30×).
 */
const SIDEREAL_SPEEDUP = 30;
const RADIUS = 100;

const vertex = /* glsl */ `
  attribute vec2 aRaDec;   // degrees
  attribute float aSize;
  attribute float aAlpha;
  attribute vec3 aColor;
  attribute float aSeed;
  uniform float uLst;      // local sidereal time, degrees
  uniform float uLat;      // observer latitude, degrees
  uniform float uTime;
  uniform float uPixelRatio;
  uniform float uTwinkle;  // 0 = no scintillation (Milky Way layer)
  varying vec3 vColor;
  varying float vAlpha;
  varying float vHalo;
  const float D2R = 0.017453292519943295;

  void main() {
    float h = (uLst - aRaDec.x) * D2R;
    float d = aRaDec.y * D2R;
    float p = uLat * D2R;
    float sinAlt = sin(d) * sin(p) + cos(d) * cos(p) * cos(h);
    float alt = asin(clamp(sinAlt, -1.0, 1.0));
    float cosAlt = cos(alt);
    vec2 az = normalize(vec2(-cos(d) * sin(h), sin(d) * cos(p) - cos(d) * sin(p) * cos(h)) + 1e-6);
    vec3 dir = vec3(cosAlt * az.x, sinAlt, -cosAlt * az.y);      // x = East, y = Up, z = South
    vec4 mv = modelViewMatrix * vec4(dir * ${RADIUS.toFixed(1)}, 1.0);
    gl_Position = projectionMatrix * mv;

    // Atmospheric scintillation: small, irregular, unsynchronised; stronger for bright stars low in the sky.
    float bright = clamp((aSize - 2.0) / 8.0, 0.0, 1.0);
    float low = 1.0 - clamp(alt / 1.1, 0.0, 1.0);
    float amp = uTwinkle * (0.05 + 0.22 * bright * low + 0.06 * low);
    float f1 = 0.25 + aSeed * 0.7;
    float f2 = 0.9 + fract(aSeed * 7.31) * 1.1;
    float flicker = 1.0 + amp * (0.6 * sin(uTime * f1 + aSeed * 40.0) + 0.4 * sin(uTime * f2 + aSeed * 13.0));

    float horizon = smoothstep(0.0, 0.12, alt);                   // fade near / below the horizon
    vAlpha = aAlpha * flicker * horizon;
    vColor = aColor;
    vHalo = bright;
    gl_PointSize = max(1.0, aSize * uPixelRatio * (1.0 + 0.15 * (flicker - 1.0)));
  }
`;

const fragment = /* glsl */ `
  uniform float uOpacity;
  uniform vec3 uTint;
  uniform float uTintMix;
  varying vec3 vColor;
  varying float vAlpha;
  varying float vHalo;
  void main() {
    vec2 c = gl_PointCoord - 0.5;
    float r2 = dot(c, c) * 4.0;                                     // 0 at centre, 1 at the sprite edge
    float core = exp(-r2 * 9.0);                                    // soft Gaussian core
    float halo = vHalo * 0.10 * exp(-r2 * 2.2);                     // very subtle glow for the brightest stars
    float a = vAlpha * (core + halo) * uOpacity;
    if (a < 0.004) discard;
    gl_FragColor = vec4(mix(vColor, uTint, uTintMix), a);
  }
`;

interface Props {
  theme: "light" | "dark";
}

function buildStars(maxMag: number) {
  const rows = (catalogue as StarRow[]).filter((r) => r[2] <= maxMag);
  const n = rows.length;
  const raDec = new Float32Array(n * 2), size = new Float32Array(n), alpha = new Float32Array(n);
  const color = new Float32Array(n * 3), seed = new Float32Array(n);
  rows.forEach(([ra, dec, mag, bv], i) => {
    const s = magToSizeAlpha(mag);
    raDec.set([ra, dec], i * 2);
    size[i] = s.size;
    alpha[i] = s.alpha;
    color.set(kelvinToRgb(bvToKelvin(bv)), i * 3);
    seed[i] = ((i * 2654435761) % 1000) / 1000;
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(n * 3), 3)); // computed in the shader
  g.setAttribute("aRaDec", new THREE.BufferAttribute(raDec, 2));
  g.setAttribute("aSize", new THREE.BufferAttribute(size, 1));
  g.setAttribute("aAlpha", new THREE.BufferAttribute(alpha, 1));
  g.setAttribute("aColor", new THREE.BufferAttribute(color, 3));
  g.setAttribute("aSeed", new THREE.BufferAttribute(seed, 1));
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), RADIUS * 2); // never frustum-cull the sky
  return g;
}

function buildMilkyWay() {
  const pts = milkyWayPoints();
  const n = pts.length;
  const raDec = new Float32Array(n * 2), size = new Float32Array(n), alpha = new Float32Array(n);
  const color = new Float32Array(n * 3), seed = new Float32Array(n);
  pts.forEach(([ra, dec, w], i) => {
    raDec.set([ra, dec], i * 2);
    size[i] = 26;
    alpha[i] = 0.05 * w;
    color.set([0.85, 0.87, 1.0], i * 3);
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
  g.setAttribute("aRaDec", new THREE.BufferAttribute(raDec, 2));
  g.setAttribute("aSize", new THREE.BufferAttribute(size, 1));
  g.setAttribute("aAlpha", new THREE.BufferAttribute(alpha, 1));
  g.setAttribute("aColor", new THREE.BufferAttribute(color, 3));
  g.setAttribute("aSeed", new THREE.BufferAttribute(seed, 1));
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), RADIUS * 2);
  return g;
}

function material(theme: "light" | "dark", twinkle: number) {
  const dark = theme === "dark";
  return new THREE.ShaderMaterial({
    vertexShader: vertex,
    fragmentShader: fragment,
    transparent: true,
    depthWrite: false,
    blending: dark ? THREE.AdditiveBlending : THREE.NormalBlending,
    uniforms: {
      uLst: { value: 0 },
      uLat: { value: OBSERVER.latDeg },
      uTime: { value: 0 },
      uPixelRatio: { value: 1 },
      uTwinkle: { value: twinkle },
      // Light (twilight) theme: only the brightest stars, faint, tinted with the ink colour.
      uOpacity: { value: dark ? 1 : 0.55 },
      uTint: { value: new THREE.Color("#4E4577") },
      uTintMix: { value: dark ? 0 : 1 },
    },
  });
}

export default function StarField({ theme }: Props) {
  const { gl, camera, pointer } = useThree();
  const startLst = useRef(localSiderealDeg(new Date()));
  const scroll = useRef(0);
  const stars = useMemo(() => buildStars(theme === "dark" ? 5.8 : 2.6), [theme]);
  const milky = useMemo(() => (theme === "dark" ? buildMilkyWay() : null), [theme]);
  const starMat = useMemo(() => material(theme, 1), [theme]);
  const milkyMat = useMemo(() => material(theme, 0), [theme]);

  useEffect(() => {
    const onScroll = () => (scroll.current = window.scrollY);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    const lst = startLst.current + (t / 3600) * 15 * SIDEREAL_SPEEDUP; // degrees
    for (const m of [starMat, milkyMat]) {
      m.uniforms.uLst.value = lst;
      m.uniforms.uTime.value = t;
      m.uniforms.uPixelRatio.value = gl.getPixelRatio();
    }
    // Look south, raised 45°, with gentle parallax from pointer and scroll.
    const alt = THREE.MathUtils.degToRad(45 + pointer.y * 1.5 - Math.min(scroll.current, 600) * 0.004);
    const az = THREE.MathUtils.degToRad(pointer.x * -2);
    camera.lookAt(Math.sin(az) * Math.cos(alt), Math.sin(alt), Math.cos(az) * Math.cos(alt));
  });

  return (
    <group>
      {milky && <points geometry={milky} material={milkyMat} frustumCulled={false} />}
      <points geometry={stars} material={starMat} frustumCulled={false} />
    </group>
  );
}

/** At most one very rare, subtle meteor (Landing only). */
export function Meteor() {
  const mesh = useRef<THREE.Mesh>(null);
  const s = useRef({ t: 0, next: 50 + Math.random() * 70, active: false, x: 0, y: 0 });
  useFrame((_, delta) => {
    const st = s.current;
    const m = mesh.current;
    if (!m) return;
    st.t += delta;
    if (!st.active && st.t > st.next) {
      st.active = true;
      st.t = 0;
      st.x = -20 + Math.random() * 30;
      st.y = 20 + Math.random() * 25;
    }
    if (st.active) {
      const p = st.t / 0.9;
      m.visible = true;
      m.position.set(st.x + p * 14, st.y - p * 6, 60);
      (m.material as THREE.MeshBasicMaterial).opacity = 0.35 * Math.sin(Math.PI * Math.min(1, p));
      if (p >= 1) {
        st.active = false;
        st.t = 0;
        st.next = 60 + Math.random() * 90;
        m.visible = false;
      }
    }
  });
  return (
    <mesh ref={mesh} visible={false} rotation={[0, 0, -0.4]}>
      <planeGeometry args={[3.2, 0.04]} />
      <meshBasicMaterial color="#ffffff" transparent opacity={0} depthWrite={false} side={THREE.DoubleSide} />
    </mesh>
  );
}
