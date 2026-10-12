import { describe, expect, it } from "vitest";
import { detectVoiceSupport, pickVoice } from "./voice";

describe("voice feature detection", () => {
  it("detects nothing without a window", () => {
    expect(detectVoiceSupport(undefined)).toEqual({ recognition: false, synthesis: false });
  });
  it("detects webkit-prefixed recognition", () => {
    expect(detectVoiceSupport({ webkitSpeechRecognition: function () {} }).recognition).toBe(true);
  });
  it("detects speech synthesis", () => {
    expect(detectVoiceSupport({ speechSynthesis: { getVoices: () => [] } }).synthesis).toBe(true);
    expect(detectVoiceSupport({}).synthesis).toBe(false);
  });
});

describe("voice selection", () => {
  const voices = [
    { lang: "en-US", localService: true },
    { lang: "en-IN", localService: false },
    { lang: "hi-IN", localService: true },
  ];
  it("prefers en-IN for English", () => {
    expect(pickVoice(voices, "en")?.lang).toBe("en-IN");
  });
  it("returns nothing for Kannada when no Kannada voice is installed (UI shows a notice)", () => {
    expect(pickVoice(voices, "kn")).toBeUndefined();
  });
  it("finds a Kannada voice when present, including underscore locales", () => {
    expect(pickVoice([...voices, { lang: "kn_IN" }], "kn")?.lang).toBe("kn_IN");
  });
  it("falls back to any English voice", () => {
    expect(pickVoice([{ lang: "en-GB" }], "en")?.lang).toBe("en-GB");
  });
});
