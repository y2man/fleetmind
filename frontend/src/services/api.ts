import { API_URL } from "@/config/env";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

let accessToken: string | null = null;
let refresher: (() => Promise<string | null>) | null = null;
export const setAccessToken = (t: string | null) => { accessToken = t; };
export const setRefresher = (fn: () => Promise<string | null>) => { refresher = fn; };
export const getAccessToken = () => accessToken;
export const refreshAccessToken = async (): Promise<string | null> => (refresher ? refresher() : null);

async function request(path: string, init: RequestInit): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return fetch(`${API_URL}/api/v1${path}`, { ...init, headers, credentials: "include" });
}

async function failure(res: Response): Promise<ApiError> {
  let msg = `Request failed (${res.status})`;
  try {
    const b = await res.json();
    if (typeof b.detail === "string") msg = b.detail;
    else if (Array.isArray(b.detail)) msg = b.detail.map((d: { msg: string }) => d.msg).join(", ");
  } catch { /* non-JSON error body */ }
  return new ApiError(res.status, msg);
}

/** Download a file from an authenticated endpoint (a plain link cannot send the access token). */
export async function download(path: string, fallbackName: string): Promise<void> {
  let res = await request(path, {});
  if (res.status === 401 && refresher && (await refresher())) res = await request(path, {});
  if (!res.ok) throw await failure(res);
  const name = /filename="([^"\\/]+)"/.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ?? fallbackName;
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res = await request(path, init);
  if (res.status === 401 && refresher && !path.startsWith("/auth/")) {
    if (await refresher()) res = await request(path, init); // one silent retry with a fresh token
  }
  if (!res.ok) throw await failure(res);
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const post = <T>(path: string, body?: unknown) => api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const del = (path: string) => api<void>(path, { method: "DELETE" });
