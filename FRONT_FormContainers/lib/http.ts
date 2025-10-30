"use client";

/**
 * Capa HTTP compartida para el frontend.
 * - Resuelve una base de API tolerante a distintos despliegues.
 * - Adjunta automáticamente Authorization y CSRF.
 * - Ofrece manejo de timeouts y parsing uniforme de errores.
 */

/* =========================
 * Resolución de base API
 * ========================= */

const trimEndSlash = (s: string) => s.replace(/\/+$/, "");
const hasProto = (s: string) => /^https?:\/\//i.test(s);

function resolveApiBase(): string {
  const origin = trimEndSlash(process.env.NEXT_PUBLIC_BACKEND_ORIGIN || "");
  const prefix = trimEndSlash(process.env.NEXT_PUBLIC_API_PREFIX || "/api/v1");

  let envApiUrl = (process.env.NEXT_PUBLIC_API_URL || "").trim();
  if (envApiUrl) envApiUrl = trimEndSlash(envApiUrl);

  let base = "/api";

  if (envApiUrl) {
    if (hasProto(envApiUrl)) {
      if (/\/api$/i.test(envApiUrl) && prefix.toLowerCase() === "/api/v1") {
        base = envApiUrl.replace(/\/api$/i, "") + prefix;
      } else {
        base = envApiUrl;
      }
    } else {
      base = envApiUrl;
    }
  } else if (origin) {
    base = origin + (prefix.startsWith("/") ? "" : "/") + prefix;
  }

  return trimEndSlash(base);
}

function resolveAdminApiBase(apiBase: string): string {
  const raw = (process.env.NEXT_PUBLIC_ADMIN_API_URL || "").trim();
  if (!raw) return apiBase;
  if (hasProto(raw)) return trimEndSlash(raw);
  return trimEndSlash(raw);
}

export const API_BASE = resolveApiBase();
export const ADMIN_API_BASE = resolveAdminApiBase(API_BASE);

export function buildApiUrl(path: string, base: string = API_BASE) {
  const cleanBase = trimEndSlash(base || "");
  const cleanPath = String(path || "").replace(/^\/+/, "");
  if (!cleanPath) return `${cleanBase}/`;

  const needsTrailingSlash =
    !cleanPath.endsWith("/") &&
    !cleanPath.includes("?") &&
    !/\.[a-z0-9]+$/i.test(cleanPath);

  return `${cleanBase}/${cleanPath}${needsTrailingSlash ? "/" : ""}`;
}

/* =========================
 * Auth helpers
 * ========================= */

const DEFAULT_TOKEN_KEY =
  process.env.NEXT_PUBLIC_AUTH_TOKEN_KEY || "auth:access_token";
const LEGACY_TOKEN_KEYS = [DEFAULT_TOKEN_KEY, "auth_token"];

export function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2)
    return decodeURIComponent(parts.pop()!.split(";").shift() || "");
  return null;
}

function readLocalStorage(key: string): string | null {
  try {
    if (typeof localStorage === "undefined") return null;
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function getAuthToken(): string | undefined {
  for (const key of LEGACY_TOKEN_KEYS) {
    const value = readLocalStorage(key);
    if (value) return value;
  }
  const cookieToken = readCookie("auth_token");
  return cookieToken || undefined;
}

/* =========================
 * Fetch helpers
 * ========================= */

function isFormData(body: unknown): body is FormData {
  return typeof FormData !== "undefined" && body instanceof FormData;
}

export async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: (RequestInit & { timeoutMs?: number }) = {}
): Promise<Response> {
  const { timeoutMs, signal, ...rest } = init;
  if (!timeoutMs) {
    return fetch(input, { ...rest, signal });
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const cleanup = () => clearTimeout(timer);

  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  try {
    return await fetch(input, { ...rest, signal: controller.signal });
  } finally {
    cleanup();
  }
}

function pickErrorMessage(data: any): string | null {
  if (!data) return null;
  if (typeof data === "string") return data;
  const first = (...xs: any[]) =>
    xs.find((v) => typeof v === "string" && v.trim());
  const direct = first(data.detail, data.error, data.message, data.mensaje);
  if (direct) return direct;

  if (Array.isArray(data.non_field_errors) && data.non_field_errors[0])
    return String(data.non_field_errors[0]);
  if (Array.isArray(data.answer) && data.answer[0])
    return String(data.answer[0]);

  for (const key of Object.keys(data)) {
    const value = data[key];
    if (typeof value === "string" && value.trim()) return value;
    if (Array.isArray(value) && typeof value[0] === "string" && value[0].trim())
      return value[0];
  }
  return null;
}

async function parseErrorResponse(res: Response) {
  const text = await res.text().catch(() => "");
  if (!text) {
    return {
      message: res.statusText || `HTTP ${res.status}`,
      data: null,
    };
  }

  try {
    const data = JSON.parse(text);
    const message =
      pickErrorMessage(data) || res.statusText || `HTTP ${res.status}`;
    return { message, data };
  } catch {
    return { message: text, data: null };
  }
}

/* =========================
 * apiFetch principal
 * ========================= */

export type ApiFetchOptions = RequestInit & {
  json?: unknown;
  skipAuth?: boolean;
  expectBlob?: boolean;
  expectText?: boolean;
  baseUrl?: string;
  timeoutMs?: number;
};

export async function apiFetch<T = any>(
  endpoint: string,
  options: ApiFetchOptions = {}
): Promise<T> {
  const {
    json,
    skipAuth = false,
    expectBlob = false,
    expectText = false,
    baseUrl,
    timeoutMs,
    headers,
    ...rest
  } = options;

  const url = hasProto(endpoint)
    ? endpoint
    : buildApiUrl(endpoint, baseUrl ?? API_BASE);

  const method = (rest.method || "GET").toUpperCase();
  const finalHeaders = new Headers(headers || {});

  if (!finalHeaders.has("Accept") && !expectBlob) {
    finalHeaders.set("Accept", "application/json");
  }

  const init: RequestInit = { ...rest };

  if (json !== undefined) {
    init.body = JSON.stringify(json);
    if (!finalHeaders.has("Content-Type")) {
      finalHeaders.set("Content-Type", "application/json");
    }
  }

  if (
    init.body &&
    !isFormData(init.body) &&
    !finalHeaders.has("Content-Type")
  ) {
    if (typeof init.body === "string") {
      finalHeaders.set("Content-Type", "application/json");
    }
  }

  const isUnsafe = !["GET", "HEAD", "OPTIONS"].includes(method);
  if (isUnsafe && !finalHeaders.has("X-CSRFToken")) {
    const csrf = readCookie("csrftoken");
    if (csrf) finalHeaders.set("X-CSRFToken", csrf);
  }

  if (!skipAuth && !finalHeaders.has("Authorization")) {
    const token = getAuthToken();
    if (token) finalHeaders.set("Authorization", `Bearer ${token}`);
  }

  const credentials = init.credentials ?? "include";

  const response = await fetchWithTimeout(url, {
    ...init,
    headers: finalHeaders,
    credentials,
    timeoutMs,
  });

  if (!response.ok) {
    const { message, data } = await parseErrorResponse(response);
    const error = Object.assign(new Error(message), {
      status: response.status,
      data,
      url,
    });
    throw error;
  }

  if (expectBlob) return (await response.blob()) as any;
  if (expectText) return (await response.text()) as any;

  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }
  return (null as unknown) as T;
}

export const http = apiFetch;

