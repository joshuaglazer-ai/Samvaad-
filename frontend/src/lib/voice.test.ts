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

describe("Hindi and Telugu voices", () => {
  const voices = [{ lang: "en-IN" }, { lang: "hi-IN" }, { lang: "te_IN" }];
  it("picks hi-IN and te-IN voices when installed", () => {
    expect(pickVoice(voices, "hi")?.lang).toBe("hi-IN");
    expect(pickVoice(voices, "te")?.lang).toBe("te_IN");
  });
  it("returns nothing (UI shows the calm notice) when the language has no voice", () => {
    expect(pickVoice([{ lang: "en-IN" }], "te")).toBeUndefined();
    expect(pickVoice([{ lang: "en-IN" }], "hi")).toBeUndefined();
  });
});

describe("server voice fallback routing (browser first, to save credits)", () => {
  it("uses the browser voice whenever the phone has one", async () => {
    const { chooseSpeakRoute } = await import("./voice");
    expect(chooseSpeakRoute(true, true)).toBe("browser");
    expect(chooseSpeakRoute(true, false)).toBe("browser");
  });
  it("uses server speech only when the phone has no voice for the language", async () => {
    const { chooseSpeakRoute } = await import("./voice");
    expect(chooseSpeakRoute(false, true)).toBe("server");
    expect(chooseSpeakRoute(false, false)).toBe("none"); // the calm notice is shown and tap options keep working
  });
  it("switches listening to the server only when the browser has no recogniser for the language", async () => {
    const { chooseListenRoute } = await import("./voice");
    expect(chooseListenRoute(true, null, true, true)).toBe("browser");
    expect(chooseListenRoute(true, "no-speech", true, true)).toBe("browser");
    expect(chooseListenRoute(true, "language-not-supported", true, true)).toBe("server");
    expect(chooseListenRoute(false, null, true, true)).toBe("server");
    expect(chooseListenRoute(false, null, true, false)).toBe("none"); // cannot record on this phone
    expect(chooseListenRoute(false, null, false, true)).toBe("none");
  });
});
