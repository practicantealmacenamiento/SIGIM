// lib/http.ts

// ============ Cookies helpers ============
export function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}
export function setCookie(name: string, value: string, days = 7) {
  const exp = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; Expires=${exp}; SameSite=Lax`;
}
export function delCookie(name: string) {
  document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax`;
}
export const cookies = { get: getCookie, set: setCookie, del: delCookie };

// ============ URL helpers ============
const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "/api/").replace(/\/?$/, "/");
const ADMIN_API_BASE = (process.env.NEXT_PUBLIC_ADMIN_API_URL || API_BASE).replace(/\/?$/, "/");

function buildUrl(path: string, base = API_BASE) {
  const p0 = String(path || "");
  const p = p0.replace(/^\/+/, "");
  const hasQuery = p.includes("?");
  const looksLikeFile = /\.[a-z0-9]+$/i.test(p);
  const endsWithSlash = p.endsWith("/");
  const finalPath = hasQuery || looksLikeFile || endsWithSlash ? p : p + "/";
  return base + finalPath;
}

// ============ Token helpers ============
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  // Unificar: leemos un solo origen (admin_token primero)
  return (
    localStorage.getItem("admin_token") ||
    localStorage.getItem("AUTH_TOKEN") ||
    localStorage.getItem("auth_token")
  );
}
export function setToken(tok: string) {
  if (typeof window !== "undefined") localStorage.setItem("admin_token", tok);
}
export function clearToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("AUTH_TOKEN");
    localStorage.removeItem("auth_token");
  }
}

// ============ HTTP core ============
export type HttpOptions = RequestInit & {
  json?: unknown;           // atajo: manda JSON
  useAdminBase?: boolean;   // apunta a ADMIN_API_BASE
  useSession?: boolean;     // si necesitas cookies (p. ej. /admin/login o whoami SSR)
};

export async function http<T = any>(path: string, opts: HttpOptions = {}): Promise<T> {
  const base = opts.useAdminBase ? ADMIN_API_BASE : API_BASE;
  const url = buildUrl(path, base);

  const headers = new Headers(opts.headers || {});
  const init: RequestInit = { ...opts };

  // JSON helper
  if (opts.json !== undefined) {
    if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    init.body = JSON.stringify(opts.json);
  }

  // Auth header (token) — no mezclar con sesión por defecto
  const token = getToken();
  if (token && !headers.has("Authorization")) headers.set("Authorization", `Token ${token}`);

  // CSRF solo cuando explícitamente useSession (no lo forzamos)
  const method = (init.method || "GET").toUpperCase();
  const wantsSession = !!opts.useSession;
  init.credentials = wantsSession ? "include" : "omit";

  // En multipart NO fijes Content-Type (el browser pone boundary)
  if (init.body instanceof FormData) {
    headers.delete("Content-Type");
  }

  // Nunca metas redirecciones aquí; deja que el caller decida
  init.headers = headers;

  const res = await fetch(url, init);

  if (!res.ok) {
    // Armamos error sin navegar; evita loops
    const ct = res.headers.get("content-type") || "";
    let data: any = null;
    try { data = ct.includes("application/json") ? await res.json() : await res.text(); } catch {}
    const err: any = new Error((data && (data.detail || data.error)) || res.statusText || "HTTP error");
    err.status = res.status;
    err.data = data;
    err.url = url;
    throw err;
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  if (ct.startsWith("text/")) return (await res.text()) as unknown as T;
  return (await res.blob()) as unknown as T;
}

// Compat con código viejo
export const apiFetch = http;
