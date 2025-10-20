import type { UUID } from "@/types/form";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "/api")
  .replace(/\/+$/, "") + "/";

// === Auth helpers compartidos (token en LS o cookie) ===
function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return decodeURIComponent(parts.pop()!.split(";").shift() || "");
  return null;
}
function getAuthToken(): string | null {
  if (typeof localStorage !== "undefined") {
    const a = localStorage.getItem("auth:access_token");
    if (a) return a;
    const b = localStorage.getItem("auth_token");
    if (b) return b;
  }
  return readCookie("auth_token");
}

// Usar las mismas credenciales que el resto de la aplicación
const authHeaders = (method: string, extra: Record<string, string> = {}) => {
  const h = new Headers(extra);
  if (!h.has("Accept")) h.set("Accept", "application/json");
  const tok = getAuthToken();
  if (tok && !h.has("Authorization")) h.set("Authorization", `Bearer ${tok}`);
  // nota: dejamos que quien llame ponga Content-Type si es JSON
  return { method, credentials: "include" as const, headers: h };
};

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit & { timeoutMs?: number } = {}
) {
  const { timeoutMs = 25000, ...rest } = init;
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), timeoutMs);
  try {
    return await fetch(input, { ...rest, signal: ac.signal });
  } finally {
    clearTimeout(t);
  }
}

async function parseOrThrow<T>(res: Response, fallback: string): Promise<T> {
  if (res.ok) return res.json();
  let msg = fallback;
  try {
    const txt = await res.text();
    try {
      const j = JSON.parse(txt);
      msg = (j?.detail || j?.error || j?.message || j?.mensaje || txt || fallback) as string;
    } catch {
      msg = txt || fallback;
    }
  } catch {}
  throw new Error(msg);
}

// ==== Tipos ligeros para el panel ====
export type SubmissionRow = {
  id: UUID;
  placa_vehiculo: string | null;
  regulador_id: UUID | null;
  fecha_cierre: string | null;
  muelle: string | null;
};

// Intenta extraer el muelle desde answers[] sin depender de cambios en el back.
// Busca primero por semantic_tag === "muelle" y si no, por coincidencia de texto "muelle".
function extraerMuelle(answers: any[] | undefined | null): string | null {
  if (!Array.isArray(answers)) return null;

  const norm = (s: string) =>
    (s || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();

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
      const choiceText =
        a?.answer_choice?.text ??
        a?.answer_choice?.label ??
        a?.choice?.text ??
        a?.choice_label ??
        null;

      const text = a?.answer_text ?? a?.text ?? null;
      const respuesta = (choiceText ?? text ?? "").toString().trim();
      return respuesta || null;
    }
  }
  return null;
}

// ==== Listado Fase 1 finalizados (pendientes de Fase 2) ====
export async function listarFase1Finalizados(params: {
  search?: string;
  page?: number;
  pageSize?: number;
}): Promise<{ results: SubmissionRow[]; count: number }> {
  const { search = "", page = 1, pageSize = 20 } = params;

  const url = new URL(`${API_BASE}submissions/`, window.location.origin);
  url.searchParams.set("tipo_fase", "entrada");
  url.searchParams.set("solo_finalizados", "1");
  url.searchParams.set("solo_pendientes_fase2", "1"); // filtro especial del back
  if (search.trim()) url.searchParams.set("placa_vehiculo", search.trim());

  const res = await fetchWithTimeout(url.toString(), authHeaders("GET"));
  const data = await parseOrThrow<any>(res, "No se pudo cargar el listado");
  const list = Array.isArray(data) ? data : data.results ?? [];
  const count = typeof data.count === "number" ? data.count : list.length;

  const mapped: SubmissionRow[] = list.map((s: any) => ({
    id: s.id,
    placa_vehiculo: s.placa_vehiculo ?? null,
    regulador_id: s.regulador_id ?? null,
    fecha_cierre: s.fecha_cierre ?? null,
    muelle: extraerMuelle(s.answers),
  }));

  const start = Math.max(0, (page - 1) * pageSize);
  const end = start + pageSize;

  return { results: mapped.slice(start, end), count };
}

// ==== Buscar Fase 2 por placa (borrador/no finalizada) ====
export async function buscarFase2PorPlaca(placa: string): Promise<SubmissionRow | null> {
  const url = new URL(`${API_BASE}submissions/`, window.location.origin);
  url.searchParams.set("tipo_fase", "salida");
  url.searchParams.set("incluir_borradores", "1"); // para traer no finalizadas
  url.searchParams.set("placa_vehiculo", placa);

  const res = await fetchWithTimeout(url.toString(), authHeaders("GET"));
  const data = await parseOrThrow<any>(res, "No se pudo buscar Fase 2");

  const list = Array.isArray(data) ? data : data.results ?? [];
  const draft = list.find((s: any) => s.finalizado === false) || null;

  return draft
    ? {
        id: draft.id,
        placa_vehiculo: draft.placa_vehiculo ?? null,
        regulador_id: draft.regulador_id ?? null,
        fecha_cierre: draft.fecha_cierre ?? null,
        muelle: extraerMuelle(draft.answers) ?? null, // en Fase 2 normalmente no aplica
      }
    : null;
}

// ==== Crear Fase 2 ====
export async function crearSubmissionFase2(payload: {
  questionnaire_id_fase2: UUID;
  placa_vehiculo: string;
  regulador_id?: UUID | null;
}): Promise<SubmissionRow> {
  const body = {
    questionnaire_id: payload.questionnaire_id_fase2,
    tipo_fase: "salida",
    placa_vehiculo: payload.placa_vehiculo,
    regulador_id: payload.regulador_id ?? null,
  };

  const res = await fetchWithTimeout(`${API_BASE}submissions/`, {
    ...authHeaders("POST", { "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  const data = await parseOrThrow<any>(res, "No se pudo crear la Fase 2");

  return {
    id: data.id,
    placa_vehiculo: data.placa_vehiculo ?? null,
    regulador_id: data.regulador_id ?? null,
    fecha_cierre: data.fecha_cierre ?? null,
    muelle: null, // Fase 2 recién creada no trae muelle
  };
}
