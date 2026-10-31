const PASS_KEY = "warden-passcode";
const INJECT_KEY = "warden-inject";

export function passcode(): string {
  return sessionStorage.getItem(PASS_KEY) || "";
}

export function setPasscode(value: string): void {
  sessionStorage.setItem(PASS_KEY, value);
}

export function injectToken(): string {
  return sessionStorage.getItem(INJECT_KEY) || "change-me";
}

export function setInjectToken(value: string): void {
  sessionStorage.setItem(INJECT_KEY, value);
}

async function req(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (passcode()) headers.set("X-Passcode", passcode());
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json");
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401) {
    sessionStorage.removeItem(PASS_KEY);
  }
  return res;
}

export async function get<T>(path: string): Promise<T> {
  const res = await req(path);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function post<T>(path: string, body: unknown, extra: HeadersInit = {}): Promise<T> {
  const res = await req(path, { method: "POST", body: JSON.stringify(body), headers: extra });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export function authHeaders(): HeadersInit {
  return { "X-Passcode": passcode(), "X-Inject-Token": injectToken() };
}
