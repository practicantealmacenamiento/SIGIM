import { API_BASE } from "./constants";
import { getAuthToken, clearAuthToken } from "./auth-storage";

export async function parseError(res: Response) {
  try {
    const data = await res.json();
    if (typeof data === "string") return data;
    if (data?.detail) return data.detail;
    if (data?.error) return data.error;
    if (data && typeof data === "object") return JSON.stringify(data);
  } catch {
    /* ignore */
  }
  return `${res.status} ${res.statusText}`;
}

export async function apiFetch<T = any>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  const url = `${API_BASE}${path}`;

  const incomingHeaders =
    init.headers instanceof Headers
      ? Object.fromEntries(init.headers.entries())
      : (init.headers as Record<string, string>) || {};

  const hasStringBody = typeof init.body === "string";
  const baseHeaders: Record<string, string> = {
    Accept: "application/json",
    ...(hasStringBody ? { "Content-Type": "application/json" } : {}),
  };

  const headers: Record<string, string> = {
    ...baseHeaders,
    ...incomingHeaders,
  };

  if (token && !headers.Authorization) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(url, {
    ...init,
    headers,
    credentials: "omit",
  });

  if (res.status === 401) {
    clearAuthToken();
    throw new Error("No autorizado. Inicia sesión nuevamente.");
  }

  if (!res.ok) throw new Error(await parseError(res));
  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}

export async function apiTry<T = any>(
  paths: string[],
  init: RequestInit = {}
): Promise<T> {
  let lastErr: unknown = null;
  for (const p of paths) {
    try {
      return await apiFetch<T>(p, init);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("No se pudo resolver el endpoint");
}

export function toQuery(params?: Record<string, any>) {
  if (!params) return "";
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    usp.append(key, String(value));
  });
  const query = usp.toString();
  return query ? `?${query}` : "";
}
