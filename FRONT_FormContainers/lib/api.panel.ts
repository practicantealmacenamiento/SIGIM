/* eslint-disable @typescript-eslint/no-explicit-any */
import type { UUID } from "@/types/form";

// ======================
// Base URL
// ======================
const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "/api/").replace(/\/?$/, "/");

// ======================
// Cookies + Token helpers
// ======================
function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

/** Lee SIEMPRE el token de usuario (no API key global) */
function getAdminToken(): string | null {
  try {
    if (typeof window !== "undefined") {
      const ls =
        localStorage.getItem("admin_token") ||
        localStorage.getItem("AUTH_TOKEN") ||
        localStorage.getItem("auth_token");
      if (ls) return ls;
    }
  } catch {}
  return getCookie("auth_token");
}

/** Envoltura que añade Authorization (Token ...) para TODOS los métodos */
function withAuth(init?: RequestInit): RequestInit {
  const headers = new Headers(init?.headers || {});
  const token = getAdminToken();
  if (token && !headers.has("Authorization")) headers.set("Authorization", `Token ${token}`);

  const method = (init?.method || "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = getCookie("csrftoken");
    if (csrf && !headers.has("X-CSRFToken")) headers.set("X-CSRFToken", csrf);
    if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  }

  if (!headers.has("Accept")) headers.set("Accept", "application/json");

  return { ...init, headers, credentials: "include", cache: "no-store", redirect: "manual" };
}

async function parseOrThrow<T>(res: Response, fallback: string): Promise<T> {
  if (!res.ok) {
    const ct = res.headers.get("content-type") || "";
    let data: any = null;
    try { data = ct.includes("application/json") ? await res.json() : await res.text(); } catch {}
    const msg = (data && (data.detail || data.error)) || res.statusText || fallback;
    const err: any = new Error(msg);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  if (ct.startsWith("text/")) return (await res.text()) as unknown as T;
  return (await res.blob()) as unknown as T;
}

// ======================
// Tipos del Panel
// ======================
export type SubmissionRow = {
  id: UUID;
  placa_vehiculo: string | null;
  regulador_id: UUID | null;
  fecha_cierre: string | null;
  muelle: string | null;
};

// ===== Helpers locales para extraer "muelle" desde answers =====
const norm = (s: string) =>
  (s || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

function extraerMuelle(answers: any[] | undefined | null): string | null {
  if (!Array.isArray(answers) || !answers.length) return null;

  const ts = (a: any) => {
    const t =
      Date.parse(a?.timestamp ?? "") ||
      Date.parse(a?.created_at ?? "") ||
      Date.parse(a?.updated_at ?? "");
    return Number.isFinite(t) ? t : 0;
  };

  const ordenadas = [...answers].sort((a, b) => ts(b) - ts(a));
  for (const a of ordenadas) {
    const q = a?.question || a?.question_data || {};
    const tag = String(q?.semantic_tag ?? "").toLowerCase().trim();
    const qtext = norm(String(q?.text ?? q?.label ?? ""));
    const contieneMuelle = tag === "muelle" || qtext.includes("muelle");
    if (contieneMuelle) {
      const choiceText = (a?.answer_choice?.text || a?.answer_choice_text || "").toString().trim();
      const text = (a?.answer_text || "").toString().trim();
      const val = choiceText || text;
      if (val) return val;
    }
  }
  return null;
}

// ======================
// Endpoints usados por el Panel
// ======================

/**
 * Lista Fase 1 finalizados que aún no tienen Fase 2 final (pendientes de salida).
 * Usa /api/submissions/ con filtros del backend.
 */
export async function listarFase1Finalizados(params: {
  search?: string;
  page?: number;      // reservado si luego paginas en back
  pageSize?: number;  // reservado si luego paginas en back
}): Promise<{ results: SubmissionRow[]; count: number }> {
  const { search = "" } = params;
  const url = new URL(`${API_BASE}submissions/`, typeof window !== "undefined" ? window.location.origin : "http://localhost");
  url.searchParams.set("tipo_fase", "entrada");
  url.searchParams.set("solo_finalizados", "1");
  url.searchParams.set("solo_pendientes_fase2", "1"); // usa la anotación del repo
  if (search.trim()) url.searchParams.set("placa_vehiculo", search.trim());

  const res = await fetch(url.toString(), withAuth({ method: "GET" }));
  const list = await parseOrThrow<any[]>(res, "No se pudieron listar Fase 1");

  const mapped: SubmissionRow[] = list.map((s: any) => ({
    id: s.id,
    placa_vehiculo: s.placa_vehiculo ?? null,
    regulador_id: s.regulador_id ?? null,
    fecha_cierre: s.fecha_cierre ?? null,
    muelle: extraerMuelle(s.answers) ?? null,
  }));
  return { results: mapped, count: mapped.length };
}

/**
 * Busca un borrador de Fase 2 por placa.
 * Consulta /api/submissions/?tipo_fase=salida&placa_vehiculo=...&incluir_borradores=1
 */
export async function buscarFase2PorPlaca(placa: string): Promise<SubmissionRow | null> {
  const url = new URL(`${API_BASE}submissions/`, typeof window !== "undefined" ? window.location.origin : "http://localhost");
  url.searchParams.set("tipo_fase", "salida");
  url.searchParams.set("incluir_borradores", "1");
  url.searchParams.set("placa_vehiculo", placa);

  const res = await fetch(url.toString(), withAuth({ method: "GET" }));
  const list = await parseOrThrow<any[]>(res, "No se pudo buscar Fase 2");
  const draft = list.find((s: any) => s.finalizado === false) || null;

  return draft
    ? {
        id: draft.id,
        placa_vehiculo: draft.placa_vehiculo ?? null,
        regulador_id: draft.regulador_id ?? null,
        fecha_cierre: draft.fecha_cierre ?? null,
        muelle: extraerMuelle(draft.answers) ?? null,
      }
    : null;
}

/**
 * Crea una Fase 2 (salida) enlazada a la Fase 1 (regulador_id).
 * POST /api/submissions
 */
export async function crearSubmissionFase2(payload: {
  questionnaire_id_fase2: UUID;
  placa_vehiculo: string;
  regulador_id?: UUID | null;
}): Promise<SubmissionRow> {
  const body = {
    questionnaire: payload.questionnaire_id_fase2,
    tipo_fase: "salida",
    placa_vehiculo: payload.placa_vehiculo,
    regulador_id: payload.regulador_id ?? null,
  };

  const res = await fetch(`${API_BASE}submissions/`, withAuth({
    method: "POST",
    body: JSON.stringify(body),
  }));
  const data = await parseOrThrow<any>(res, "No se pudo crear la Fase 2");

  return {
    id: data.id,
    placa_vehiculo: data.placa_vehiculo ?? null,
    regulador_id: data.regulador_id ?? null,
    fecha_cierre: data.fecha_cierre ?? null,
    muelle: null,
  };
}
