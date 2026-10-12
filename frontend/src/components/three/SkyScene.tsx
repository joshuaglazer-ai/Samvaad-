import { useEffect, useState } from "react";
import { Canvas } from "@react-three/fiber";
import StarField, { Nebula, ShootingStar } from "./StarField";
import FloatingOrb from "./FloatingOrb";
import ConstellationLadder from "./ConstellationLadder";

interface Props {
  variant?: "landing" | "onboarding";
}

/** Lazy-loaded WebGL background. Never rendered in Lite mode. DPR capped at 1.5; paused when the tab is hidden. */
export default function SkyScene({ variant = "landing" }: Props) {
  const [visible, setVisible] = useState(!document.hidden);
  useEffect(() => {
    const onVis = () => setVisible(!document.hidden);
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, []);

  return (
    <div className="pointer-events-none fixed inset-0 z-0" aria-hidden="true">
      <Canvas
        dpr={[1, 1.5]}
        frameloop={visible ? "always" : "never"}
        camera={{ position: [0, 0, 6], fov: 55 }}
        gl={{ antialias: false, alpha: true, powerPreference: "low-power" }}
      >
        <ambientLight intensity={0.9} />
        <directionalLight position={[3, 4, 5]} intensity={1.2} color="#ffffff" />
        <Nebula />
        <StarField count={variant === "landing" ? 2600 : 1400} />
        {variant === "landing" && (
          <>
            <ShootingStar />
            <FloatingOrb />
            <ConstellationLadder />
          </>
        )}
      </Canvas>
    </div>
  );
}
