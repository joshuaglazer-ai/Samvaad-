import { useEffect, useState } from "react";
import { Canvas } from "@react-three/fiber";
import StarField, { Meteor } from "./StarField";
import { useAppState } from "../../lib/state";

interface Props {
  variant?: "landing" | "onboarding";
}

/** Lazy-loaded WebGL sky. Never rendered in Lite mode (the pre-rendered catalogue image is shown instead).
 * DPR capped at 1.5; the render loop pauses when the tab is hidden. */
export default function SkyScene({ variant = "landing" }: Props) {
  const { theme } = useAppState();
  const [visible, setVisible] = useState(!document.hidden);

  useEffect(() => {
    const onVis = () => setVisible(!document.hidden);
    document.addEventListener("visibilitychange", onVis);
    // While the live sky is on screen, hide the static star image underneath so stars are not doubled.
    document.documentElement.classList.add("webgl-sky");
    return () => {
      document.removeEventListener("visibilitychange", onVis);
      document.documentElement.classList.remove("webgl-sky");
    };
  }, []);

  return (
    <div className="pointer-events-none fixed inset-0 z-0" aria-hidden="true">
      <Canvas
        dpr={[1, 1.5]}
        frameloop={visible ? "always" : "never"}
        camera={{ position: [0, 0, 0], fov: 70, near: 0.1, far: 500 }}
        gl={{ antialias: false, alpha: true, powerPreference: "low-power" }}
      >
        <StarField theme={theme} />
        {/* At most one very rare, subtle meteor, on the Landing page at night only. */}
        {variant === "landing" && theme === "dark" && <Meteor />}
      </Canvas>
    </div>
  );
}
