/**
 * API del módulo Formulario — alineada a backend con prefijo versionado.
 * - Lee configuración desde env:
 *   - NEXT_PUBLIC_BACKEND_ORIGIN (p.ej. http://172.24.66.23:8000)
 *   - NEXT_PUBLIC_API_PREFIX    (por defecto /api/v1)
 *   - NEXT_PUBLIC_API_URL       (opcional; puede ser /api, /api/v1 o absoluta)
 * - Autenticación:
 *   - Authorization: Bearer <token>  (token en localStorage("auth_token") o cookie "auth_token")
 *   - credentials: "include" + X-CSRFToken (para sesión/CSRF si aplica)
 * - Endpoints usados por el flujo: createSubmission, getPrimeraPregunta, guardarYAvanzar,
 *   verificarImagen, finalizarSubmission, getQuestionById, getSubmissionDetail, listQuestionnaires,
 *   secureMediaUrl, searchActors.
 */

/* =========================
 * Config base (sin sorpresas)
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
  if (parts.length === 2) return decodeURIComponent(parts.pop()!.split(";").shift() || "");
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

export async function fetchApi<T = any>(endpoint: string, init: FetchOpts = {}): Promise<T> {
  const url = buildUrl(endpoint);
  const headers = new Headers(init.headers || {});
  const method = (init.method || "GET").toUpperCase();

  // Auth: Bearer por defecto (el backend acepta Bearer o Token)
  const token = getToken();
  if (token && !init.skipAuth && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // CSRF en métodos no seguros
  const isUnsafe = !["GET", "HEAD", "OPTIONS"].includes(method);
  if (isUnsafe) {
    const csrftoken = readCookie("csrftoken");
    if (csrftoken) headers.set("X-CSRFToken", csrftoken);
    if (!(init.body instanceof FormData)) {
      headers.set("Content-Type", headers.get("Content-Type") || "application/json");
    }
  }

  const res = await fetch(url, { ...init, headers, credentials: "include" });

  if (!res.ok) {
    const txt = await res.text();
    try {
      const data = JSON.parse(txt);
      throw Object.assign(new Error(data.detail || data.error || res.statusText), { status: res.status, data });
    } catch {
      throw Object.assign(new Error(txt || res.statusText), { status: res.status });
    }
  }

  if (init.expectBlob) return (await res.blob()) as any;
  if (init.expectText) return (await res.text()) as any;

  const ct = res.headers.get("Content-Type") || "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  // sin contenido
  return (null as unknown) as T;
}

/* =========================
 * Endpoints del Formulario
 * ========================= */

// Crea una submission (payload flexible)
export function createSubmission(payload: { questionnaire: string; tipo_fase?: "entrada" | "salida"; regulador_id?: string | null; placa_vehiculo?: string | null }) {
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
export function verificarImagen(payload: { question_id: string; imagen: File; mode?: "text" | "document" }) {
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

/* =========================
 * Formularios tabulares
 * ========================= */

export type GridColumn = {
  question_id: string;
  header: string;
  column: string;
  order: number;
  width?: number | null;
  semantic_tag?: string | null;
  ui_hint?: string | null;
};

export type GridDefinition = {
  questionnaire_id: string;
  title: string;
  version: string;
  timezone: string;
  columns: GridColumn[];
};

export type TableRowValue = {
  answer_text?: string | null;
  answer_choice_id?: string | null;
  answer_file_path?: string | null;
  actor_id?: string | null;
  actor_name?: string | null;
  actor_document?: string | null;
};

export type TableRowRecord = {
  submission_id: string;
  row_index: number;
  values: Record<string, TableRowValue>;
};

export type TableRowCellsPayload = {
  question_id: string;
  answer_text?: string | null;
  answer_choice_id?: string | null;
  actor_id?: string | null;
  file?: File | Blob | null;
};

type TableRowFormPayload = {
  submissionId: string;
  rowIndex?: number | null;
  cells: TableRowCellsPayload[];
};

export type ActorLite = {
  id: string;
  nombre: string;
  documento?: string | null;
};

function buildTableRowFormData(payload: TableRowFormPayload): FormData {
  const fd = new FormData();
  if (payload.rowIndex) {
    fd.set("row_index", String(payload.rowIndex));
  }

  payload.cells.forEach((cell, index) => {
    fd.set(`cells[${index}][question_id]`, cell.question_id);

    if (cell.actor_id) {
      fd.set(`cells[${index}][actor_id]`, cell.actor_id);
    }

    if (cell.answer_text !== undefined && cell.answer_text !== null) {
      fd.set(`cells[${index}][answer_text]`, cell.answer_text);
    }

    if (cell.answer_choice_id) {
      fd.set(`cells[${index}][answer_choice_id]`, cell.answer_choice_id);
    }

    if (cell.file) {
      fd.set(`cells[${index}][file]`, cell.file);
    }
  });

  return fd;
}

export function getQuestionnaireGrid(questionnaireId: string): Promise<GridDefinition> {
  return fetchApi(`cuestionarios/${questionnaireId}/grid/`);
}

export function listSubmissionTableRows(submissionId: string): Promise<{ submission_id: string; rows: TableRowRecord[] }> {
  return fetchApi(`submissions/${submissionId}/table-rows/`);
}

export function createTableRow(payload: TableRowFormPayload): Promise<TableRowRecord> {
  const fd = buildTableRowFormData(payload);
  return fetchApi(`submissions/${payload.submissionId}/table-rows/`, {
    method: "POST",
    body: fd,
  });
}

export function updateTableRow(payload: TableRowFormPayload & { rowIndex: number }): Promise<TableRowRecord> {
  const fd = buildTableRowFormData(payload);
  return fetchApi(`submissions/${payload.submissionId}/table-rows/${payload.rowIndex}/`, {
    method: "PUT",
    body: fd,
  });
}

export function deleteTableRow(submissionId: string, rowIndex: number): Promise<null> {
  return fetchApi(`submissions/${submissionId}/table-rows/${rowIndex}/`, {
    method: "DELETE",
  });
}

export async function fetchCatalogActors(params: {
  tipo: "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR";
  search?: string;
  limit?: number;
  signal?: AbortSignal;
}): Promise<ActorLite[]> {
  const qs = new URLSearchParams();
  qs.set("tipo", params.tipo);
  if (params.search && params.search.trim()) {
    qs.set("search", params.search.trim());
  }
  if (params.limit) {
    qs.set("limit", String(params.limit));
  }

  const endpoint = qs.toString() ? `catalogos/actores/?${qs.toString()}` : "catalogos/actores/";
  const data = await fetchApi<any>(endpoint, { signal: params.signal });
  const rawList = Array.isArray(data) ? data : data?.results ?? [];

  return rawList
    .map((actor: any) => {
      const id = actor?.id ?? actor?.uuid ?? actor?.pk ?? actor?.ID;
      if (!id) return null;
      const nombre =
        actor?.nombre ??
        actor?.razon_social ??
        actor?.razonSocial ??
        actor?.name ??
        actor?.display_name ??
        "";
      const documento =
        actor?.documento ??
        actor?.nit ??
        actor?.identificacion ??
        actor?.document ??
        actor?.numero_documento ??
        null;
      return {
        id: String(id),
        nombre: String(nombre || ""),
        documento: documento ? String(documento) : null,
      } as ActorLite;
    })
    .filter((item: ActorLite | null): item is ActorLite => Boolean(item?.id));
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

  const list = await fetchCatalogActors({ tipo, search, limit, signal });
  return list.map((actor) => ({
    id: actor.id,
    nombre: actor.nombre,
    nit: actor.documento ?? null,
  }));
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
