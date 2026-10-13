/** Typed client for the SAMVAAD backend. The frontend never talks to the LLM directly. */
import { getDeviceId } from "./deviceId";

export const API_BASE: string = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

export type DataStatus = "verified" | "historical" | "demo" | "unavailable";

export interface Evidence {
  source: string | null;
  source_url?: string | null;
  reporting_period: string | null;
  sample_size: number | null;
  geo_level: "district" | "state" | "national" | null;
  data_status: DataStatus;
  limitations?: string[];
}

export interface OutcomeData {
  trade_slug: string;
  trade_name: string;
  district: string | null;
  year: number;
  placement_rate: number | null;
  placement_numerator: number | null;
  placement_denominator: number | null;
  earnings_min: number | null;
  earnings_max: number | null;
  earnings_median: number | null;
  earnings_basis: "monthly" | "annual";
  fallback_note?: string | null;
}

export interface LadderStep {
  step_order: number;
  kind: string;
  title: string;
  nsqf_level: number | null;
  entry_requirement: string;
  duration_months: number | null;
  eligible: boolean;
}

export interface Card {
  type: "outcome" | "ladder" | "providers" | "costs";
  data: Record<string, unknown>;
  evidence: Evidence;
}

export interface ChatResponse {
  message_id: number;
  reply_text: string;
  cards: Card[];
  quick_replies: string[];
  guardrail_status: "pass" | "regenerated" | "fallback" | "na";
  escalation: EscalationInfo | null;
  reply_language?: string;
  suggest_language?: "en" | "kn" | "hi" | "te" | null;
}

export interface EscalationInfo {
  id: number;
  trigger: string;
  status: string;
  counsellor_online: boolean;
}

export interface TranscriptMessage {
  id: number;
  role: "user" | "assistant" | "counsellor";
  speaker: string;
  text: string;
  language: string;
  cards: Card[];
  created_at: string;
  device_id?: string | null;
  concern_category?: string | null;
  sentiment?: number | null;
  guardrail_status?: string;
}

export interface SessionStatus {
  participation_mode: "together" | "two_devices" | "learner_only";
  parent_joined: boolean;
  parent_language: string | null;
  learner_language: string;
  alignment: { learner_done: boolean; parent_done: boolean };
  mood_pre: { learner: boolean; parent: boolean };
  family_code: string | null;
}

export interface Trade {
  slug: string;
  name: string;
  name_en: string;
  name_kn: string;
  sector: string;
  nsqf_level: number;
  duration_months: number;
  icon: string;
}

export interface AlignmentResult {
  complete: boolean;
  learner: string[] | null;
  parent: string[] | null;
  shared_top: string[];
  biggest_difference: string | null;
  differences: { value: string; learner_rank: number; parent_rank: number; gap: number }[];
}

export interface SummaryData {
  session_id: string;
  language: string;
  district: string;
  trades_discussed: { slug: string; name: string }[];
  figures: Card[];
  ladder: Card | null;
  alignment: AlignmentResult | null;
  concerns: string[];
  has_demo_data: boolean;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}, pin?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (pin) headers["X-Role-Pin"] = pin;
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers: { ...headers, ...(init.headers as Record<string, string>) } });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.headers.get("content-type")?.includes("application/json")) return res.json() as Promise<T>;
  return (await res.text()) as unknown as T;
}

const post = <T>(path: string, body: unknown, pin?: string) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) }, pin);

export const api = {
  health: () => request<{ status: string; llm_mode: string }>("/api/health"),
  createSession: (body: {
    language: string; district: string; learner_education: string; learner_interests: string[];
    top_concerns: string[]; income_bracket?: string | null; helper_mode: boolean; consent_given: boolean;
    participation_mode: string;
  }) => post<{ session_id: string; family_code: string | null }>("/api/session", { ...body, device_id: getDeviceId() }),
  familyCode: (id: string) => post<{ family_code: string }>(`/api/session/${id}/family-code`, {}),
  status: (id: string) => request<SessionStatus>(`/api/session/${id}/status`),
  join: (code: string, language: string) =>
    post<{ session_id: string; district: string; learner_language: string; learner_education: string }>(
      "/api/join", { code, language, device_id: getDeviceId() }),
  updateSession: (id: string, body: { language?: string; helper_mode?: boolean }) =>
    request<{ ok: boolean }>(`/api/session/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  endSession: (id: string) => post<{ ok: boolean }>(`/api/session/${id}/end`, {}),
  mood: (id: string, body: { respondent: "learner" | "parent"; phase: "pre" | "post"; value: number }) =>
    post<{ ok: boolean }>(`/api/session/${id}/mood`, { ...body, device_id: getDeviceId() }),
  saveAlignment: (id: string, body: { respondent: "learner" | "parent"; ranking: string[] }) =>
    post<AlignmentResult>(`/api/session/${id}/alignment`, { ...body, device_id: getDeviceId() }),
  getAlignment: (id: string) => request<AlignmentResult>(`/api/session/${id}/alignment`),
  chat: (body: { session_id: string; speaker: string; text: string; language: string }) =>
    post<ChatResponse>("/api/chat", { ...body, device_id: getDeviceId() }),
  transcript: (id: string) => request<TranscriptMessage[]>(`/api/session/${id}/messages`),
  summary: (id: string) => request<SummaryData>(`/api/session/${id}/summary`),
  event: (body: { session_id?: string | null; event_type: string; payload?: Record<string, unknown> }) =>
    post<{ ok: boolean }>("/api/events", body),
  trades: (lang: string) => request<Trade[]>(`/api/trades?language=${lang}`),
  districts: () => request<{ name: string; lat: number; lng: number }[]>("/api/districts"),
  config: () => request<{ income_brackets: string[]; districts: string[]; concerns: string[]; education_levels: string[] }>("/api/config"),
  escalate: (body: { session_id: string; trigger: string }) => post<EscalationInfo>("/api/escalate", body),
  callback: (id: number, body: { phone: string; preferred_time: string; consent: boolean }) =>
    post<{ ok: boolean }>(`/api/escalate/${id}/callback`, body),
  escalationMessages: (id: number, after = 0) =>
    request<TranscriptMessage[]>(`/api/escalations/${id}/messages?after=${after}`),
  escalationStatus: (id: number) => request<EscalationInfo>(`/api/escalations/${id}`),
  sendEscalationMessage: (id: number, body: { text: string; speaker: string }) =>
    post<TranscriptMessage>(`/api/escalations/${id}/messages`, body),

  // PIN-protected (demo-grade auth)
  counsellor: {
    queue: (pin: string) => request<CounsellorCase[]>("/api/counsellor/queue", {}, pin),
    caseDetail: (pin: string, id: number) => request<CounsellorCaseDetail>(`/api/counsellor/cases/${id}`, {}, pin),
    update: (pin: string, id: number, body: { status?: string; assigned_to?: string }) =>
      request<CounsellorCase>(`/api/counsellor/cases/${id}`, { method: "PATCH", body: JSON.stringify(body) }, pin),
    callbacks: (pin: string) => request<CallbackItem[]>("/api/counsellor/callbacks", {}, pin),
    deleteCallback: (pin: string, id: number) =>
      request<{ ok: boolean }>(`/api/counsellor/callbacks/${id}`, { method: "DELETE" }, pin),
    reply: (pin: string, id: number, text: string) =>
      post<TranscriptMessage>(`/api/counsellor/cases/${id}/reply`, { text }, pin),
  },
  admin: {
    get: <T>(pin: string, path: string) => request<T>(`/api/admin/${path}`, {}, pin),
    exportUrl: () => `${API_BASE}/api/admin/export.csv`,
  },
};

export interface CounsellorCase {
  id: number;
  session_id: string;
  trigger: string;
  status: string;
  summary_en: string;
  summary_local: string;
  summary_language: string;
  assigned_to: string | null;
  created_at: string;
  waiting_minutes: number;
  district: string;
  language: string;
  has_callback: boolean;
}

export interface CounsellorCaseDetail extends CounsellorCase {
  transcript: TranscriptMessage[];
  top_concerns: string[];
}

export interface CallbackItem {
  id: number;
  escalation_id: number;
  phone: string | null;
  preferred_time: string | null;
  created_at: string;
  district: string;
}

export function wsUrl(path: string): string {
  return API_BASE.replace(/^http/, "ws") + path;
}

export { ApiError };
