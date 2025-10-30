import { apiFetch, buildApiUrl } from "@/lib/http";

/* =========================
 * Tipos auxiliares
 * ========================= */

export type FormActorTipo = "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR";

/* =========================
 * Endpoints del Formulario
 * ========================= */

export function createSubmission(payload: {
  questionnaire: string;
  tipo_fase?: "entrada" | "salida";
  regulador_id?: string | null;
  placa_vehiculo?: string | null;
}) {
  const body = {
    ...payload,
    questionnaire_id: payload.questionnaire,
  };
  return apiFetch("submissions/", {
    method: "POST",
    json: body,
  });
}

export function getPrimeraPregunta(questionnaire_id: string) {
  const params = new URLSearchParams({ questionnaire_id });
  const qs = params.toString();
  return apiFetch(`cuestionario/primera/${qs ? `?${qs}` : ""}`);
}

export function guardarYAvanzar(fd: FormData) {
  return apiFetch("cuestionario/guardar_avanzar/", {
    method: "POST",
    body: fd,
  });
}

export function getQuestionById(id: string) {
  return apiFetch(`questions/${id}/`);
}

export function verificarImagen(payload: {
  question_id: string;
  imagen: File;
  mode?: "text" | "document";
}) {
  const fd = new FormData();
  fd.set("question_id", payload.question_id);
  fd.set("imagen", payload.imagen);
  if (payload.mode) fd.set("mode", payload.mode);
  return apiFetch("verificar/", { method: "POST", body: fd });
}

export function finalizarSubmission(id: string) {
  return apiFetch(`submissions/${id}/finalize/`, { method: "POST" });
}

export function getSubmissionDetail(id: string) {
  return apiFetch(`submissions/${id}/`);
}

export function listQuestionnaires() {
  return apiFetch("cuestionarios/");
}

export function secureMediaUrl(filePath: string) {
  const safePath = encodeURI(filePath.replace(/^\/+/, ""));
  return buildApiUrl(`secure-media/${safePath}/`);
}

export async function searchCatalogActors(opts: {
  tipo: FormActorTipo;
  search: string;
  limit?: number;
  signal?: AbortSignal;
}) {
  const { tipo, search, limit = 15, signal } = opts;
  const params = new URLSearchParams({
    tipo,
    search,
    q: search,
    limit: String(limit),
  });
  const qs = params.toString();
  return apiFetch<Array<{ id: string; nombre: string; nit?: string | null }>>(
    `catalogos/actores/${qs ? `?${qs}` : ""}`,
    { signal }
  );
}

export const fetchFormApi = apiFetch;

export function getFaseIds() {
  return {
    FASE1: process.env.NEXT_PUBLIC_Q_FASE1_ID || "",
    FASE2: process.env.NEXT_PUBLIC_Q_FASE2_ID || "",
  };
}

