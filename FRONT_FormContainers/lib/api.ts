/**
 * API principal del formulario (cualquier usuario autenticado).
 * Compatibilizado con los imports de useFormFlow:
 * - getPrimeraPregunta
 * - getQuestionById
 * - guardarYAvanzar
 * - verificarImagen
 * - finalizarSubmission
 * - createSubmission
 *
 * Extras por compatibilidad futura:
 * - getQuestionDetail (alias de getQuestionById)
 * - finalizeSubmission (alias de finalizarSubmission)
 */

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "/api/").replace(/\/?$/, "/");

/* ===================== Helpers de bajo nivel ===================== */

function buildUrl(endpoint: string): string {
  return `${API_URL}${endpoint.replace(/^\/+/, "")}`;
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

function qs(params?: Record<string, any>): string {
  if (!params) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    sp.append(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

function baseHeaders(isJson: boolean, extra?: HeadersInit): HeadersInit {
  const h: HeadersInit = isJson ? { "Content-Type": "application/json" } : {};
  return { ...h, ...(extra || {}) };
}

/* ===================== Cliente general ===================== */

export async function fetchApi<T = any>(
  endpoint: string,
  init: RequestInit & { expectBlob?: boolean; expectText?: boolean } = {}
): Promise<T> {
  const url = buildUrl(endpoint);
  const headers = new Headers(init.headers || {});
  const method = (init.method || "GET").toUpperCase();

  // Token DRF desde cookie (si lo emitió /api/login/)
  const token = getCookie("auth_token");
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Token ${token}`);
  }

  // CSRF para métodos no-GET (si estamos usando SessionAuth)
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = getCookie("csrftoken");
    if (csrf && !headers.has("X-CSRFToken")) {
      headers.set("X-CSRFToken", csrf);
    }
  }

  const res = await fetch(url, {
    ...init,
    headers,
    credentials: "include",
  });

  if (!res.ok) {
    const ctype = res.headers.get("content-type") || "";
    let data: any = null;
    try {
      if (ctype.includes("application/json")) data = await res.json();
      else data = await res.text();
    } catch {
      data = null;
    }
    const err: any = new Error((data && (data.detail || data.error)) || res.statusText);
    err.status = res.status;
    err.data = data;
    throw err;
  }

  if (init.expectBlob) return (await res.blob()) as unknown as T;
  if (init.expectText) return (await res.text()) as unknown as T;

  const ctype = res.headers.get("content-type") || "";
  if (ctype.includes("application/json")) return (await res.json()) as T;
  if (ctype.startsWith("text/")) return (await res.text()) as unknown as T;
  return (await res.blob()) as unknown as T;
}

async function postFormData<T = any>(endpoint: string, form: FormData): Promise<T> {
  // Importantísimo: NO setear Content-Type manualmente (boundary lo pone el browser)
  return fetchApi<T>(endpoint, { method: "POST", body: form });
}

/* ===================== Tipos mínimos (opcionales) ===================== */

export type UUID = string;

export type AdminChoice = { id: string; text: string; branch_to?: string | null };
export type AdminQuestion = {
  id: string;
  text: string;
  type: "text" | "number" | "date" | "file" | "choice";
  required: boolean;
  order: number;
  choices?: AdminChoice[] | null;
  semantic_tag?: string | null;
  file_mode?: string | null;
};
export type Submission = {
  id: UUID;
  questionnaire: UUID;
  tipo_fase: string;
  finalizado: boolean;
  fecha_creacion?: string;
  proveedor?: any;
  transportista?: any;
  receptor?: any;
};

/* ===================== Endpoints del flujo principal ===================== */

/** 1) Primera pregunta (opcionalmente por questionnaire_id). */
export async function getPrimeraPregunta(questionnaire_id?: string) {
  const q = questionnaire_id ? `?questionnaire_id=${encodeURIComponent(questionnaire_id)}` : "";
  return fetchApi<AdminQuestion>(`cuestionario/primera/${q}`);
}

/** 2) Detalle de pregunta por id — nombre que espera tu hook. */
export async function getQuestionById(id: string) {
  return fetchApi<AdminQuestion>(`questions/${id}/`);
}

/** Alias de compatibilidad (si en algún sitio usabas este nombre). */
export const getQuestionDetail = getQuestionById;

/** 3) Crear submission (inicio de fase). */
export async function createSubmission(payload: {
  questionnaire: string;
  tipo_fase: string;
  regulador_id?: string;
}) {
  // Normalizar el payload para que use questionnaire_id
  const normalizedPayload = {
    questionnaire_id: payload.questionnaire,
    tipo_fase: payload.tipo_fase,
    regulador_id: payload.regulador_id,
  };
  
  return fetchApi<Submission>("submissions/", {
    method: "POST",
    headers: baseHeaders(true),
    body: JSON.stringify(normalizedPayload),
  });
}

/** 4) Guardar y avanzar (admite hasta 2 archivos). */
export async function guardarYAvanzar(form: FormData) {
  return postFormData(`cuestionario/guardar_avanzar/`, form);
}

/** 5) Verificación OCR universal (placa/precinto/contenedor). */
export async function verificarImagen(data: { question_id: string; imagen: File | Blob; mode?: string }) {
  const form = new FormData();
  form.append("question_id", data.question_id);
  if (data.mode) form.append("mode", data.mode);
  form.append("imagen", data.imagen);
  return postFormData(`verificar/`, form);
}

/** 6) Finalizar submission — nombre que espera tu hook. */
export async function finalizarSubmission(id: string) {
  return fetchApi<{ mensaje: string; [k: string]: any }>(`submissions/${id}/finalize/`, {
    method: "POST",
  });
}

/** Alias en inglés por compatibilidad futura. */
export const finalizeSubmission = finalizarSubmission;

/** (Opcionales) utilidades extra que quizá uses en otras pantallas */
export async function listSubmissions(filters?: {
  incluir_borradores?: string | number | boolean;
  solo_finalizados?: string | number | boolean;
  tipo_fase?: string;
  proveedor_id?: string;
  transportista_id?: string;
  receptor_id?: string;
}) {
  return fetchApi<Submission[]>(`submissions/${qs(filters)}`);
}

export async function getSubmissionDetail(id: string) {
  return fetchApi<Submission>(`submissions/${id}/`);
}

export async function listQuestionnaires() {
  return fetchApi<Array<{ id: string; title: string; version: string; timezone: string }>>(
    "cuestionarios/"
  );
}

export function secureMediaUrl(filePath: string) {
  const safePath = encodeURI(filePath.replace(/^\/+/, ""));
  return buildUrl(`secure-media/${safePath}/`);
}
