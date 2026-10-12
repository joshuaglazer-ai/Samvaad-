import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

/** Showcase ladder for the Landing page: stars rise and connect, step by step (job → upskill → … → degree). */
export default function ConstellationLadder({ steps = 5, position = [3.2, -1.6, -3] as [number, number, number] }) {
  const group = useRef<THREE.Group>(null);
  const progress = useRef(0);
  const lineRef = useRef<THREE.Line>(null);
  const starRefs = useRef<(THREE.Mesh | null)[]>([]);

  const points = useMemo(
    () => Array.from({ length: steps }, (_, i) => new THREE.Vector3(i * 0.55 + Math.sin(i * 1.7) * 0.25, i * 0.75, 0)),
    [steps],
  );
  const lineObj = useMemo(() => {
    const geo = new THREE.BufferGeometry().setFromPoints(points);
    geo.setDrawRange(0, 0);
    const mat = new THREE.LineBasicMaterial({ color: "#9277DB", transparent: true, opacity: 0.8 });
    return new THREE.Line(geo, mat);
  }, [points]);

  useFrame((state, delta) => {
    progress.current = Math.min(steps, progress.current + delta * 0.9);
    const shown = progress.current;
    lineObj.geometry.setDrawRange(0, Math.max(0, Math.floor(shown) + 1));
    starRefs.current.forEach((m, i) => {
      if (!m) return;
      const k = THREE.MathUtils.clamp(shown - i, 0, 1);
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 2 + i) * 0.08;
      m.scale.setScalar(k * pulse * (i === steps - 1 ? 1.4 : 1));
    });
    if (group.current) group.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.25) * 0.25;
  });

  return (
    <group ref={group} position={position}>
      <primitive object={lineObj} ref={lineRef} />
      {points.map((p, i) => (
        <mesh key={i} position={p} ref={(el) => (starRefs.current[i] = el)} scale={0}>
          <octahedronGeometry args={[0.12, 0]} />
          <meshBasicMaterial color={i === steps - 1 ? "#F2CF6B" : "#6B4FC4"} />
        </mesh>
      ))}
    </group>
  );
}
