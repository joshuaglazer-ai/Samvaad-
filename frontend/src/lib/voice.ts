/**
 * Voice in/out behind a small interface so a server-side provider (e.g. Bhashini) can be plugged in later.
 * Browser implementation: Web Speech API (SpeechRecognition) + speechSynthesis. Everything is feature-detected.
 * Optional server fallback: Sarvam speech (Bulbul TTS, Saaras STT) through our backend, used only when the phone has
 * no voice or recogniser for the chosen language — the browser stays the default so credits are spent sparingly.
 */
import { API_BASE } from "./api";

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

// ---------------------------------------------------------------- optional server voice (Sarvam, via our backend)
/** Which engine to use. The browser is always first (free); the server is only for languages the phone lacks. */
export function chooseSpeakRoute(browserHasVoice: boolean, serverTts: boolean): "browser" | "server" | "none" {
  if (browserHasVoice) return "browser";
  return serverTts ? "server" : "none";
}

export function chooseListenRoute(browserCanListen: boolean, browserError: string | null, serverStt: boolean,
  canRecord: boolean): "browser" | "server" | "none" {
  // "language-not-supported": this phone's recogniser has no Kannada/Telugu/Hindi model.
  const browserOk = browserCanListen && browserError !== "language-not-supported";
  if (browserOk) return "browser";
  return serverStt && canRecord ? "server" : "none";
}

const MAX_RECORD_MS = 8000;

class ServerVoice {
  tts = false;
  stt = false;
  private audio: HTMLAudioElement | null = null;
  private recorder: MediaRecorder | null = null;

  constructor(private base: string) {}

  async init() {
    try {
      const r = await fetch(`${this.base}/api/voice/status`);
      const s = await r.json();
      this.tts = !!s.server_tts;
      this.stt = !!s.server_stt;
    } catch {
      /* offline or server voice off: browser only */
    }
  }

  static canRecord() {
    return typeof window !== "undefined" && typeof (window as any).MediaRecorder !== "undefined" &&
      !!navigator.mediaDevices?.getUserMedia;
  }

  speak(text: string, lang: VoiceLang, onEnd?: () => void) {
    this.cancel();
    fetch(`${this.base}/api/voice/tts`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: text.slice(0, 600), language: lang }),
    })
      .then((r) => (r.ok ? r.blob() : Promise.reject(new Error(String(r.status)))))
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        this.audio = new Audio(url);
        this.audio.onended = () => { URL.revokeObjectURL(url); onEnd?.(); };
        this.audio.onerror = () => onEnd?.();
        return this.audio.play();
      })
      .catch(() => onEnd?.());
  }

  listen(lang: VoiceLang, h: ListenHandlers): () => void {
    let stopped = false;
    const stop = () => {
      stopped = true;
      if (this.recorder?.state === "recording") this.recorder.stop();
    };
    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
      if (stopped) { stream.getTracks().forEach((t) => t.stop()); h.onEnd?.(); return; }
      const chunks: Blob[] = [];
      const rec = new MediaRecorder(stream);
      this.recorder = rec;
      rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        try {
          const form = new FormData();
          form.append("language", lang);
          form.append("file", new Blob(chunks, { type: rec.mimeType || "audio/webm" }), "speech.webm");
          const r = await fetch(`${this.base}/api/voice/stt`, { method: "POST", body: form });
          const body = r.ok ? await r.json() : null;
          if (body?.transcript) h.onFinal(body.transcript);
          else h.onError?.("server_unavailable");
        } catch {
          h.onError?.("server_unavailable");
        } finally {
          h.onEnd?.();
        }
      };
      rec.start();
      window.setTimeout(stop, MAX_RECORD_MS);
    }).catch(() => { h.onError?.("not-allowed"); h.onEnd?.(); });
    return stop;
  }

  cancel() {
    this.audio?.pause();
    this.audio = null;
  }
}

/** Browser first; Sarvam (through our backend) only when the browser has no voice or recogniser for the language. */
class FallbackSpeechProvider implements SpeechProvider {
  readonly name = "browser+server";
  constructor(private browser: SpeechProvider, private server: ServerVoice) {}

  canListen() {
    return this.browser.canListen() || (this.server.stt && ServerVoice.canRecord());
  }
  canSpeak() {
    return this.browser.canSpeak() || this.server.tts;
  }
  hasVoiceFor(lang: VoiceLang) {
    return this.browser.hasVoiceFor(lang) || this.server.tts;
  }

  listen(lang: VoiceLang, h: ListenHandlers): () => void {
    const route = chooseListenRoute(this.browser.canListen(), null, this.server.stt, ServerVoice.canRecord());
    if (route === "server") return this.server.listen(lang, h);
    let current = () => undefined as void;
    current = this.browser.listen(lang, {
      ...h,
      onError: (reason) => {
        if (chooseListenRoute(true, reason, this.server.stt, ServerVoice.canRecord()) === "server") {
          current = this.server.listen(lang, h); // the phone has no recogniser for this language
        } else {
          h.onError?.(reason);
        }
      },
    });
    return () => current();
  }

  speak(text: string, lang: VoiceLang, onEnd?: () => void): SpeakResult {
    const route = chooseSpeakRoute(this.browser.hasVoiceFor(lang), this.server.tts);
    if (route === "browser") return this.browser.speak(text, lang, onEnd);
    if (route === "server") {
      this.browser.cancel();
      this.server.speak(text, lang, onEnd);
      return { ok: true };
    }
    return this.browser.speak(text, lang, onEnd); // reports no_voice → calm notice in the UI
  }

  cancel() {
    this.browser.cancel();
    this.server.cancel();
  }
}

let provider: SpeechProvider | null = null;
let server: ServerVoice | null = null;

export function getSpeech(): SpeechProvider {
  if (!provider) {
    const browser = new BrowserSpeechProvider();
    if (typeof window !== "undefined" && typeof fetch !== "undefined") {
      server = new ServerVoice(API_BASE);
      provider = new FallbackSpeechProvider(browser, server);
      void server.init();
    } else {
      provider = browser;
    }
  }
  return provider;
}

/** Swap in another provider (e.g. a Bhashini-backed one) without touching UI code. */
export function setSpeechProvider(p: SpeechProvider) {
  provider = p;
}
