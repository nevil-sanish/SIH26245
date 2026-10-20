// Thin client for the SAKSHI cloud API (cloud/api.py). Token lives in sessionStorage (cleared on tab close).
export const API = process.env.NEXT_PUBLIC_API ?? "http://localhost:8000";

export type Label = "measured" | "simulated" | "mock";
export type Evidence = "FULL" | "REDUCED" | "INSUFFICIENT";

export interface Reason { flag_id: number; type: string; weight: number; evidence_level: Evidence; explanation: string }
export interface CentreRow {
  id: string; name: string; state: string; district: string; lat: number; lon: number; label: Label;
  risk: number; reasons: Reason[]; evidence_level: Evidence | null; rupees_at_risk: number;
  unverified_trainee_hours: number; open_flags: number; flag_labels: Label[]; last_inspection: string | null; data_gaps: number;
}
export interface FlagRow {
  id: number; centre_id: string; batch_id: string | null; date: string; type: string; severity: number;
  confidence: "high" | "medium" | "low"; evidence_level: Evidence; explanation: string; next_step: string;
  status: string; label: Label; links: Record<string, unknown>;
}

export function session() {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem("sakshi");
  return raw ? (JSON.parse(raw) as { token: string; role: string; centre_id: string | null; user: string }) : null;
}

export async function login(username: string, password: string) {
  const r = await fetch(`${API}/v1/auth/login`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }),
  });
  if (!r.ok) throw new Error("bad credentials");
  const d = await r.json();
  sessionStorage.setItem("sakshi", JSON.stringify({ ...d, user: username }));
  return d;
}

export function logout() { sessionStorage.removeItem("sakshi"); location.href = "/login/"; }

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const s = session();
  const r = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(s ? { Authorization: `Bearer ${s.token}` } : {}), ...init.headers },
  });
  if (r.status === 401) { logout(); throw new Error("login required"); }
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? r.statusText);
  return r.json();
}

export const fmtDate = (t: number) => new Date(t * 1000).toLocaleString("en-IN", { hour12: false });
export const fmtTime = (t: number) => new Date(t * 1000).toLocaleTimeString("en-IN", { hour12: false, hour: "2-digit", minute: "2-digit" });
export const rupees = (n: number) => "₹" + Math.round(n).toLocaleString("en-IN");
