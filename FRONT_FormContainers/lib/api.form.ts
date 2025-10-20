/**
 * API del módulo Formulario — alineada a backend con prefijo versionado.
 * Lee configuración desde env:
 *  - NEXT_PUBLIC_BACKEND_ORIGIN  (p.ej. http://172.24.66.23:8000)
 *  - NEXT_PUBLIC_API_PREFIX      (por defecto /api/v1)
 *  - NEXT_PUBLIC_API_URL         (opcional; puede ser /api, /api/v1 o absoluta)
 *
 * Autenticación:
 *  - Authorization: Bearer <token>  (token en localStorage("auth_token") o cookie "auth_token")
 *  - credentials: "include" + X-CSRFToken (para sesión/CSRF si aplica)
 *
 * Endpoints: createSubmission, getPrimeraPregunta, guardarYAvanzar, verificarImagen,
 * finalizarSubmission, getQuestionById, getSubmissionDetail, listQuestionnaires,
 * secureMediaUrl, searchCatalogActors, getFaseIds.
 */

/* =========================
 * Config base de API
 * ========================= */

const trimEndSlash = (s: string) => s.replace(/\/+$/, "");
const hasProto = (s: string) => /^https?:\/\//i.test(s);

// 1) Lee envs y normaliza
const ORIGIN = trimEndSlash(process.env.NEXT_PUBLIC_BACKEND_ORIGIN || "");
const PREFIX = trimEndSlash(process.env.NEXT_PUBLIC_API_PREFIX || "/api/v1");

// Si defines NEXT_PUBLIC_API_URL:
//  - Puede ser relativo "/api" (proxy de Next) o "/api/v1"
//  - O absoluto "http://host:port/api" o ".../api/v1"
let envApiUrl = (process.env.NEXT_PUBLIC_API_URL || "").trim();
if (envApiUrl) envApiUrl = trimEndSlash(envApiUrl);

// 2) Determina la BASE con tolerancia:
let BASE = "/api"; // fallback a proxy
if (envApiUrl) {
  if (hasProto(envApiUrl)) {
    // Absoluto
    if (/\/api$/i.test(envApiUrl) && PREFIX.toLowerCase() === "/api/v1") {
      // Corrige "/api" -> "/api/v1" para backend real
      BASE = envApiUrl.replace(/\/api$/i, "") + PREFIX;
    } else {
      BASE = envApiUrl;
    }
  } else {
    // Relativo (/api o /api/v1) → válido con rewrites de Next
    BASE = envApiUrl;
  }
} else if (ORIGIN) {
  BASE = ORIGIN + (PREFIX.startsWith("/") ? "" : "/") + PREFIX;
}
// Normaliza BASE sin barra final
BASE = trimEndSlash(BASE);

// 3) Helper para construir URLs limpias
function buildUrl(endpoint: string): string {
  const clean = endpoint.replace(/^\/+/, "");
  return `${BASE}/${clean}`;
}

// (Útil para debug/health checks en UI si lo necesitas)
export const API_BASE = BASE;

/* =========================
 * Utilidades de auth/CSRF
 * ========================= */

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2)
    return decodeURIComponent(parts.pop()!.split(";").shift() || "");
  return null;
}

function getToken(): string | null {
  if (typeof window !== "undefined") {
    const ls = window.localStorage.getItem("auth_token");
    if (ls) return ls;
  }
  // compatibilidad si alguna vez guardaste token en cookie
  return readCookie("auth_token");
}

/* =========================
 * Fetch wrapper (genérico)
 * ========================= */

type FetchOpts = RequestInit & {
  expectBlob?: boolean;
  expectText?: boolean;
  skipAuth?: boolean;
};

function pickErrorMessage(data: any): string | null {
  if (!data) return null;
  if (typeof data === "string") return data;
  const first = (...xs: any[]) =>
    xs.find((v) => typeof v === "string" && v.trim());
  const direct = first(data.detail, data.error, data.message, data.mensaje);
  if (direct) return direct;

  // Arrays comunes de DRF
  if (Array.isArray(data.non_field_errors) && data.non_field_errors[0])
    return String(data.non_field_errors[0]);
  if (Array.isArray(data.answer) && data.answer[0]) return String(data.answer[0]);

  // Busca el primer string útil en claves
  for (const k of Object.keys(data)) {
    const v = data[k];
    if (typeof v === "string" && v.trim()) return v;
    if (Array.isArray(v) && typeof v[0] === "string" && v[0].trim()) return v[0];
  }
  return null;
}

export async function fetchApi<T = any>(
  endpoint: string,
  init: FetchOpts = {}
): Promise<T> {
  const url = buildUrl(endpoint);
  const method = (init.method || "GET").toUpperCase();

  // Mezcla headers sin perder los existentes
  const headers = new Headers(init.headers || {});
  if (!headers.has("Accept")) headers.set("Accept", "application/json");

  // Auth: Bearer por defecto (el backend acepta Bearer o Token)
  const token = getToken();
  if (token && !init.skipAuth && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // CSRF en métodos no seguros
  const isUnsafe = !["GET", "HEAD", "OPTIONS"].includes(method);
  if (isUnsafe) {
    const csrftoken = readCookie("csrftoken");
    if (csrftoken && !headers.has("X-CSRFToken"))
      headers.set("X-CSRFToken", csrftoken);
    // Sólo seteamos Content-Type si NO es FormData y el caller no lo fijó
    const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
    if (!isFormData && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
  }

  const res = await fetch(url, {
    ...init,
    headers,
    // Mantiene include por defecto (sesión/CSRF), pero respeta si el caller pasó otra cosa
    credentials: init.credentials ?? "include",
  });

  if (!res.ok) {
    // Intenta normalizar mensaje de error
    const text = await res.text().catch(() => "");
    try {
      const data = text ? JSON.parse(text) : null;
      const msg = pickErrorMessage(data) || res.statusText || "Error de solicitud";
      throw Object.assign(new Error(msg), { status: res.status, data });
    } catch {
      const msg = text || res.statusText || "Error de solicitud";
      throw Object.assign(new Error(msg), { status: res.status });
    }
  }

  if (init.expectBlob) return (await res.blob()) as any;
  if (init.expectText) return (await res.text()) as any;

  const ct = res.headers.get("Content-Type") || "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  // sin contenido o no-JSON
  return (null as unknown) as T;
}

/* =========================
 * Endpoints del Formulario
 * ========================= */

// Crea una submission (payload flexible)
export function createSubmission(payload: {
  questionnaire: string;
  tipo_fase?: "entrada" | "salida";
  regulador_id?: string | null;
  placa_vehiculo?: string | null;
}) {
  const body = {
    ...payload,
    questionnaire_id: payload.questionnaire, // compat con back si espera *_id
  };
  return fetchApi("submissions/", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Primera pregunta del cuestionario activo
export function getPrimeraPregunta(questionnaire_id: string) {
  const qs = new URLSearchParams({ questionnaire_id });
  return fetchApi(`cuestionario/primera/?${qs.toString()}`);
}

// Guardar y avanzar (FormData con campos: submission_id, question_id, value|choice_id|numero|actor_id, archivo(s)?)
export function guardarYAvanzar(fd: FormData) {
  return fetchApi("cuestionario/guardar_avanzar/", {
    method: "POST",
    body: fd,
  });
}

// Detalle de pregunta por id
export function getQuestionById(id: string) {
  return fetchApi(`questions/${id}/`);
}
export const getQuestionDetail = getQuestionById;

// Verificación OCR (imagen + question_id)
export function verificarImagen(payload: {
  question_id: string;
  imagen: File;
  mode?: "text" | "document";
}) {
  const fd = new FormData();
  fd.set("question_id", payload.question_id);
  fd.set("imagen", payload.imagen);
  if (payload.mode) fd.set("mode", payload.mode);
  return fetchApi("verificar/", { method: "POST", body: fd });
}

// Finalizar submission
export function finalizarSubmission(id: string) {
  return fetchApi(`submissions/${id}/finalize/`, { method: "POST" });
}
export const finalizeSubmission = finalizarSubmission;

// Detalle de submission (enriquecido si usas el endpoint /enriched/)
export function getSubmissionDetail(id: string) {
  return fetchApi(`submissions/${id}/`);
}

// Lista de cuestionarios (selector)
export function listQuestionnaires() {
  return fetchApi("cuestionarios/");
}

// URL pública para media protegida (a través del proxy si usas rewrite)
export function secureMediaUrl(filePath: string) {
  const safePath = encodeURI(filePath.replace(/^\/+/, ""));
  return buildUrl(`secure-media/${safePath}/`);
}

// --- Catálogos: Actores (FORM) ---
export type FormActorTipo = "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR";

export async function searchCatalogActors(opts: {
  tipo: FormActorTipo;
  search: string;
  limit?: number;
  signal?: AbortSignal;
}) {
  const { tipo, search, limit = 15, signal } = opts;

  // Enviamos ambos params por compatibilidad (search y q)
  const params = new URLSearchParams({
    tipo,
    search, // ← si la vista usa SearchFilter
    q: search, // ← si la vista lee 'q'
    limit: String(limit),
  });

  // OJO: este endpoint es el del módulo Form, NO el de admin.
  return fetchApi(`catalogos/actores/?${params.toString()}`, {
    method: "GET",
    signal,
  }) as Promise<Array<{ id: string; nombre: string; nit?: string | null }>>;
}

// Alias opcional para evitar confusiones en devtools
export const fetchFormApi = fetchApi;

/* =========================
 * (Opcional) Helpers de fase
 * ========================= */

export function getFaseIds() {
  return {
    FASE1: process.env.NEXT_PUBLIC_Q_FASE1_ID || "",
    FASE2: process.env.NEXT_PUBLIC_Q_FASE2_ID || "",
  };
}
