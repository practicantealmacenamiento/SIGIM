// ==== Cookies helpers ====
export function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}
export function setCookie(name: string, value: string, days = 7) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; Expires=${expires}; SameSite=Lax`;
}
export function delCookie(name: string) {
  document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax`;
}
export const cookies = { get: getCookie, set: setCookie, del: delCookie };

// ==== URL builders ====
export const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL || "/api/").replace(/\/?$/, "/");
export const ADMIN_API_BASE =
  (process.env.NEXT_PUBLIC_ADMIN_API_URL || API_BASE).replace(/\/?$/, "/");

export function buildUrl(path: string, base: string = API_BASE) {
  const left = base.replace(/\/+$/, "");
  const p0 = String(path || "");
  const p = p0.replace(/^\/+/, "");
  // Forzamos barra final si no es archivo ni query
  const finalPath =
    /\?|(\.[a-z0-9]+)$/i.test(p) || p.endsWith("/") ? p : `${p}/`;
  return `${left}/${finalPath}`;
}

// ==== HTTP ====
type HttpOptions = RequestInit & {
  json?: unknown;          // atajo: cuerpo JSON
  authToken?: string | null; // opcional: Authorization: Token <...>
  useAdminBase?: boolean;  // opcional: usar base de admin
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
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  // CSRF (si usas SessionAuth)
  const method = (init.method || "GET").toUpperCase();
  const isWrite = !["GET", "HEAD", "OPTIONS"].includes(method);
  const csrf = getCookie("csrftoken");
  if (isWrite && csrf && !headers.has("X-CSRFToken")) {
    headers.set("X-CSRFToken", csrf);
  }

  // Authorization opcional (para admin)
  const tok = opts.authToken;
  if (tok && !headers.has("Authorization")) {
    headers.set("Authorization", `Token ${tok}`); // tu back también acepta Bearer, pero usamos Token
  }

  // Credenciales para enviar cookies de sesión
  const USE_CREDENTIALS =
    (process.env.NEXT_PUBLIC_USE_CREDENTIALS || "true").toLowerCase() === "true";
  init.credentials = USE_CREDENTIALS ? "include" : (init.credentials || "same-origin");
  init.headers = headers;

  const res = await fetch(url, init);

  if (!res.ok) {
    // Error informativo
    const ctype = res.headers.get("content-type") || "";
    let data: any = null;
    try {
      data = ctype.includes("application/json") ? await res.json() : await res.text();
    } catch { /* ignore */ }
    const detail =
      typeof data === "string" ? data : data?.detail || JSON.stringify(data || {});
    const err = Object.assign(new Error(detail || `HTTP ${res.status}`), {
      status: res.status,
      data,
      url,
    });
    throw err;
  }

  const ctype = res.headers.get("content-type") || "";
  if (ctype.includes("application/json")) return (await res.json()) as T;
  if (ctype.includes("text/")) return (await res.text()) as unknown as T;
  // blob u otros
  return (await res.blob()) as unknown as T;
}