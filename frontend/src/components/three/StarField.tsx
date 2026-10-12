import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

function makeStarTexture(): THREE.Texture {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d")!;
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, "rgba(255,255,255,1)");
  grad.addColorStop(0.25, "rgba(255,255,255,0.8)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}

const PALETTE = ["#9277DB", "#6B4FC4", "#C7B5F0", "#F2CF6B", "#8FB3F5"];

/** A few thousand soft points with gentle parallax drift and slow twinkle. */
export default function StarField({ count = 2400 }: { count?: number }) {
  const group = useRef<THREE.Group>(null);
  const twinkleA = useRef<THREE.PointsMaterial>(null);
  const twinkleB = useRef<THREE.PointsMaterial>(null);
  const { pointer } = useThree();
  const texture = useMemo(makeStarTexture, []);

  const [a, b] = useMemo(() => {
    const build = (n: number, seed: number) => {
      const pos = new Float32Array(n * 3);
      const col = new Float32Array(n * 3);
      let s = seed;
      const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
      const c = new THREE.Color();
      for (let i = 0; i < n; i++) {
        const r = 6 + rnd() * 22;
        const th = rnd() * Math.PI * 2;
        const ph = Math.acos(2 * rnd() - 1);
        pos[i * 3] = r * Math.sin(ph) * Math.cos(th);
        pos[i * 3 + 1] = r * Math.sin(ph) * Math.sin(th) * 0.7;
        pos[i * 3 + 2] = -Math.abs(r * Math.cos(ph)) - 2;
        c.set(PALETTE[Math.floor(rnd() * PALETTE.length)]);
        col.set([c.r, c.g, c.b], i * 3);
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
      return geo;
    };
    return [build(Math.floor(count * 0.6), 7), build(Math.floor(count * 0.4), 13)];
  }, [count]);

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime;
    if (group.current) {
      group.current.rotation.y += delta * 0.006;
      // parallax: ease towards the pointer
      group.current.rotation.x += (pointer.y * 0.05 - group.current.rotation.x) * 0.03;
      group.current.position.x += (pointer.x * 0.4 - group.current.position.x) * 0.03;
    }
    if (twinkleA.current) twinkleA.current.opacity = 0.65 + Math.sin(t * 0.9) * 0.2;
    if (twinkleB.current) twinkleB.current.opacity = 0.65 + Math.sin(t * 1.3 + 1.7) * 0.25;
  });

  return (
    <group ref={group}>
      <points geometry={a}>
        <pointsMaterial ref={twinkleA} size={0.14} map={texture} vertexColors transparent depthWrite={false} sizeAttenuation />
      </points>
      <points geometry={b}>
        <pointsMaterial ref={twinkleB} size={0.22} map={texture} vertexColors transparent depthWrite={false} sizeAttenuation />
      </points>
    </group>
  );
}

/** Occasional shooting star streaking across the sky. */
export function ShootingStar() {
  const mesh = useRef<THREE.Mesh>(null);
  const state = useRef({ t: 0, next: 3, x: 0, y: 0, active: false });

  useFrame((_, delta) => {
    const s = state.current;
    s.t += delta;
    const m = mesh.current;
    if (!m) return;
    if (!s.active && s.t > s.next) {
      s.active = true;
      s.t = 0;
      s.x = -6 + Math.random() * 6;
      s.y = 2 + Math.random() * 3;
    }
    if (s.active) {
      const p = s.t / 1.1;
      m.visible = true;
      m.position.set(s.x + p * 9, s.y - p * 4, -6);
      (m.material as THREE.MeshBasicMaterial).opacity = Math.max(0, 1 - p);
      if (p >= 1) {
        s.active = false;
        s.t = 0;
        s.next = 5 + Math.random() * 7;
        m.visible = false;
      }
    }
  });

  return (
    <mesh ref={mesh} visible={false} rotation={[0, 0, -0.42]}>
      <planeGeometry args={[1.6, 0.03]} />
      <meshBasicMaterial color="#F2CF6B" transparent opacity={0} />
    </mesh>
  );
}

/** Faint lavender nebula: a large soft gradient plane behind everything. */
export function Nebula() {
  const texture = useMemo(() => {
    const c = document.createElement("canvas");
    c.width = c.height = 256;
    const g = c.getContext("2d")!;
    const grad = g.createRadialGradient(128, 128, 10, 128, 128, 128);
    grad.addColorStop(0, "rgba(199,181,240,0.55)");
    grad.addColorStop(0.5, "rgba(201,221,255,0.25)");
    grad.addColorStop(1, "rgba(248,245,255,0)");
    g.fillStyle = grad;
    g.fillRect(0, 0, 256, 256);
    return new THREE.CanvasTexture(c);
  }, []);
  return (
    <mesh position={[2, 1, -14]}>
      <planeGeometry args={[34, 22]} />
      <meshBasicMaterial map={texture} transparent depthWrite={false} />
    </mesh>
  );
}
