import { describe, expect, it } from "vitest";
import { liteReasons, type DeviceSignals } from "./device";

const capable: DeviceSignals = {
  deviceMemory: 8, hardwareConcurrency: 8, prefersReducedMotion: false, saveData: false, effectiveType: "4g", webgl: true,
};

describe("Lite mode detection", () => {
  it("is off on a capable device", () => {
    expect(liteReasons(capable)).toEqual([]);
  });
  it("turns on for low memory", () => {
    expect(liteReasons({ ...capable, deviceMemory: 2 })).toContain("low_memory");
  });
  it("turns on for few CPU cores", () => {
    expect(liteReasons({ ...capable, hardwareConcurrency: 4 })).toContain("few_cores");
  });
  it("turns on for reduced motion", () => {
    expect(liteReasons({ ...capable, prefersReducedMotion: true })).toContain("reduced_motion");
  });
  it("turns on for data saver and slow networks", () => {
    expect(liteReasons({ ...capable, saveData: true })).toContain("save_data");
    expect(liteReasons({ ...capable, effectiveType: "3g" })).toContain("slow_network");
    expect(liteReasons({ ...capable, effectiveType: "2g" })).toContain("slow_network");
  });
  it("turns on when WebGL is unavailable", () => {
    expect(liteReasons({ ...capable, webgl: false })).toContain("no_webgl");
  });
  it("ignores signals the browser does not expose", () => {
    expect(liteReasons({ ...capable, deviceMemory: undefined, hardwareConcurrency: undefined, effectiveType: undefined })).toEqual([]);
  });
});
