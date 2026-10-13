/**
 * Voice in/out behind a small interface so a server-side provider (e.g. Bhashini) can be plugged in later.
 * Browser implementation: Web Speech API (SpeechRecognition) + speechSynthesis. Everything is feature-detected.
 */
export type VoiceLang = "en" | "kn" | "hi" | "te";

export const LOCALE: Record<VoiceLang, string> = { en: "en-IN", kn: "kn-IN", hi: "hi-IN", te: "te-IN" };

export interface ListenHandlers {
  onInterim?: (text: string) => void;
  onFinal: (text: string) => void;
  onEnd?: () => void;
  onError?: (reason: string) => void;
}

export interface SpeakResult {
  ok: boolean;
  /** "no_voice" when the device has no voice for this language (e.g. no Kannada voice installed). */
  reason?: "unsupported" | "no_voice";
}

export interface SpeechProvider {
  readonly name: string;
  canListen(): boolean;
  canSpeak(): boolean;
  hasVoiceFor(lang: VoiceLang): boolean;
  listen(lang: VoiceLang, handlers: ListenHandlers): () => void;
  speak(text: string, lang: VoiceLang, onEnd?: () => void): SpeakResult;
  cancel(): void;
}

// ---------------------------------------------------------------- feature detection (pure, testable)
type AnyWindow = {
  SpeechRecognition?: unknown;
  webkitSpeechRecognition?: unknown;
  speechSynthesis?: { getVoices: () => { lang: string }[] };
};

export function detectVoiceSupport(win: AnyWindow | undefined) {
  const recognition = !!(win && (win.SpeechRecognition || win.webkitSpeechRecognition));
  const synthesis = !!(win && win.speechSynthesis && typeof win.speechSynthesis.getVoices === "function");
  return { recognition, synthesis };
}

export function pickVoice<T extends { lang: string; localService?: boolean }>(voices: T[], lang: VoiceLang): T | undefined {
  const want = LOCALE[lang].toLowerCase();
  const exact = voices.filter((v) => v.lang.toLowerCase().replace("_", "-") === want);
  if (exact.length) return exact.find((v) => v.localService) ?? exact[0];
  const prefix = lang === "en" ? "en-in" : lang;
  const loose = voices.find((v) => v.lang.toLowerCase().replace("_", "-").startsWith(prefix));
  if (loose) return loose;
  return lang === "en" ? voices.find((v) => v.lang.toLowerCase().startsWith("en")) : undefined;
}

// ---------------------------------------------------------------- browser implementation
/* eslint-disable @typescript-eslint/no-explicit-any */
class BrowserSpeechProvider implements SpeechProvider {
  readonly name = "browser";
  private voices: SpeechSynthesisVoice[] = [];

  constructor() {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      const load = () => {
        this.voices = window.speechSynthesis.getVoices();
      };
      load();
      window.speechSynthesis.addEventListener?.("voiceschanged", load);
    }
  }

  canListen() {
    return typeof window !== "undefined" && detectVoiceSupport(window as any).recognition;
  }
  canSpeak() {
    return typeof window !== "undefined" && detectVoiceSupport(window as any).synthesis;
  }
  hasVoiceFor(lang: VoiceLang) {
    if (!this.canSpeak()) return false;
    if (!this.voices.length) this.voices = window.speechSynthesis.getVoices();
    return !!pickVoice(this.voices, lang);
  }

  listen(lang: VoiceLang, h: ListenHandlers): () => void {
    const Ctor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Ctor) {
      h.onError?.("unsupported");
      return () => undefined;
    }
    const rec = new Ctor();
    rec.lang = LOCALE[lang];
    rec.interimResults = true;
    rec.continuous = false; // stops on silence
    rec.maxAlternatives = 1;
    let finalText = "";
    rec.onresult = (e: any) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) finalText += r[0].transcript;
        else interim += r[0].transcript;
      }
      if (interim) h.onInterim?.(interim);
    };
    rec.onerror = (e: any) => h.onError?.(e?.error ?? "error");
    rec.onend = () => {
      if (finalText.trim()) h.onFinal(finalText.trim());
      h.onEnd?.();
    };
    try {
      rec.start();
    } catch {
      h.onError?.("start_failed");
    }
    return () => {
      try {
        rec.stop();
      } catch {
        /* already stopped */
      }
    };
  }

  speak(text: string, lang: VoiceLang, onEnd?: () => void): SpeakResult {
    if (!this.canSpeak()) return { ok: false, reason: "unsupported" };
    if (!this.voices.length) this.voices = window.speechSynthesis.getVoices();
    const voice = pickVoice(this.voices, lang);
    if (!voice) return { ok: false, reason: "no_voice" };
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.voice = voice;
    u.lang = voice.lang;
    u.rate = 0.92; // a little slower for clarity
    u.onend = () => onEnd?.();
    u.onerror = () => onEnd?.();
    window.speechSynthesis.speak(u);
    return { ok: true };
  }

  cancel() {
    if (this.canSpeak()) window.speechSynthesis.cancel();
  }
}

let provider: SpeechProvider | null = null;

export function getSpeech(): SpeechProvider {
  if (!provider) provider = new BrowserSpeechProvider();
  return provider;
}

/** Swap in another provider (e.g. a Bhashini-backed one) without touching UI code. */
export function setSpeechProvider(p: SpeechProvider) {
  provider = p;
}
