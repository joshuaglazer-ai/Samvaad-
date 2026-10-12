import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

/** Slowly rotating glassy orb behind the wordmark (lightweight physical material, no transmission pass). */
export default function FloatingOrb({ position = [0, 1.6, -4] as [number, number, number] }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((state, delta) => {
    if (!ref.current) return;
    ref.current.rotation.y += delta * 0.15;
    ref.current.rotation.x += delta * 0.05;
    ref.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 0.6) * 0.12;
  });
  return (
    <mesh ref={ref} position={position}>
      <icosahedronGeometry args={[1.35, 6]} />
      <meshPhysicalMaterial
        color="#EFE9FD"
        roughness={0.08}
        metalness={0.05}
        clearcoat={1}
        clearcoatRoughness={0.1}
        iridescence={0.6}
        iridescenceIOR={1.3}
        sheen={0.6}
        sheenColor={new THREE.Color("#C9DDFF")}
        transparent
        opacity={0.28}
      />
    </mesh>
  );
}
