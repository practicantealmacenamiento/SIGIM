// lib/http.ts

// ==== Cookies helpers ====
export function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}
export function setCookie(name: string, value: string, days = 7) {
  if (typeof document === "undefined") return;
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; Expires=${expires}; SameSite=Lax`;
}
export function delCookie(name: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax`;
}
export const cookies = { get: getCookie, set: setCookie, del: delCookie };

// ==== URL builders ====
export const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL || "/api/").replace(/\/?$/, "/");
export const ADMIN_API_BASE =
  (process.env.NEXT_PUBLIC_ADMIN_API_URL || API_BASE).replace(/\/?$/, "/");

export function buildUrl(path: string, base: string = API_BASE) {
  const left = (base || "").replace(/\/+$/, "");
  const p0 = String(path || "");
  const p = p0.replace(/^\/+/, "");
  // Mantén la barra final estilo Django salvo que haya query o parezca archivo
  const finalPath = /\?|(\.[a-z0-9]+)$/i.test(p) || p.endsWith("/") ? p : `${p}/`;
  return `${left}/${finalPath}`;
}

// ==== HTTP ====
type HttpOptions = RequestInit & {
  json?: unknown;            // atajo: cuerpo JSON
  authToken?: string | null; // opcional: Authorization: <scheme> <token>
  authScheme?: "Token" | "Bearer"; // opcional: por defecto "Token"
  useAdminBase?: boolean;    // opcional: usar base de admin
};

function isFormDataBody(b: unknown): b is FormData {
  // En entornos donde FormData no existe (SSR), evitar instanceof
  return typeof FormData !== "undefined" && b instanceof FormData;
}

async function readBodySafely<T>(res: Response): Promise<T> {
  // 204 No Content o sin body
  if (res.status === 204) return undefined as unknown as T;
  const ctype = (res.headers.get("content-type") || "").toLowerCase();

  if (ctype.includes("application/json")) {
    // Algunos backends devuelven vacío con JSON CT
    const text = await res.text();
    return (text ? JSON.parse(text) : null) as T;
  }
  if (ctype.includes("text/")) {
    return (await res.text()) as unknown as T;
  }
  // blob u otros
  return (await res.blob()) as unknown as T;
}

export async function http<T = any>(path: string, opts: HttpOptions = {}): Promise<T> {
  const base = opts.useAdminBase ? ADMIN_API_BASE : API_BASE;
  const url = buildUrl(path, base);

  const headers = new Headers(opts.headers || {});
  const init: RequestInit = { ...opts };

  // JSON helper (si pasas 'json', nosotros seteamos body y Content-Type)
  if (opts.json !== undefined) {
    if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    init.body = JSON.stringify(opts.json);
  }

  // Si hay body y NO es FormData, y no hay Content-Type aún, asumimos JSON
  if (init.body && !headers.has("Content-Type") && !isFormDataBody(init.body)) {
    headers.set("Content-Type", "application/json");
  }

  // CSRF (si usas SessionAuth)
  const method = (init.method || "GET").toUpperCase();
  const isWrite = !["GET", "HEAD", "OPTIONS"].includes(method);
  const csrf = getCookie("csrftoken");
  if (isWrite && csrf && !headers.has("X-CSRFToken")) {
    headers.set("X-CSRFToken", csrf);
  }

  // Authorization opcional (para admin o APIs privadas)
  const tok = opts.authToken;
  if (tok && !headers.has("Authorization")) {
    const scheme = opts.authScheme || "Token"; // default conservador
    headers.set("Authorization", `${scheme} ${tok}`);
  }

  // Credenciales para enviar cookies de sesión
  const USE_CREDENTIALS =
    (process.env.NEXT_PUBLIC_USE_CREDENTIALS || "true").toLowerCase() === "true";
  init.credentials = USE_CREDENTIALS ? "include" : (init.credentials || "same-origin");
  init.headers = headers;

  const res = await fetch(url, init);

  if (!res.ok) {
    // Error informativo
    let detail: any = null;
    try {
      const ctype = res.headers.get("content-type") || "";
      detail = ctype.includes("application/json") ? await res.json() : await res.text();
    } catch { /* ignore */ }

    const msg =
      typeof detail === "string"
        ? detail
        : detail?.detail || detail?.error || `HTTP ${res.status}`;

    const err = Object.assign(new Error(msg), {
      status: res.status,
      data: detail,
      url,
    });
    throw err;
  }

  return await readBodySafely<T>(res);
}
