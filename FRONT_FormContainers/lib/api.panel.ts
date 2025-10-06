import type { UUID } from "@/types/form";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "/api/").replace(/\/?$/, "/");

// Usar las mismas credenciales que el resto de la aplicación
const authHeaders = (method: string, extra: Record<string, string> = {}) => {
  return { ...extra };
};

async function parseOrThrow<T>(res: Response, fallback: string): Promise<T> {
  if (res.ok) return res.json();
  let msg = fallback;
  try {
    const txt = await res.text();
    try {
      const j = JSON.parse(txt);
      msg = (j?.detail || j?.error || txt || fallback) as string;
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
  muelle: string | null; // <-- nuevo
};

// ==== Helpers (solo front) ====
// Normaliza texto para búsqueda flexible (sin tildes y en minúsculas)
const norm = (s: string) =>
  (s || "")
    .normalize("NFD")
    // Evita dependencia de \p{Diacritic} en navegadores viejos
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

// Intenta extraer el muelle desde answers[] sin depender de cambios en el back.
// Busca primero por semantic_tag === "muelle" (si algún día lo agregas) y si no,
// por coincidencia de texto "muelle" en la pregunta.
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

    // 👇 Aquí está el cambio importante
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
  url.searchParams.set("solo_pendientes_fase2", "1"); // 👈 usa el filtro especial del back
  if (search.trim()) url.searchParams.set("placa_vehiculo", search.trim());

  const res = await fetch(url.toString(), { credentials: "include", headers: authHeaders("GET") });
  const data = await parseOrThrow<any>(res, "No se pudo cargar el listado");
  const list = Array.isArray(data) ? data : data.results ?? [];
  const count = typeof data.count === "number" ? data.count : list.length;

  // Mapeo mínimo + paginación en cliente (si no hay paginación backend)
  const mapped: SubmissionRow[] = list.map((s: any) => ({
    id: s.id,
    placa_vehiculo: s.placa_vehiculo ?? null,
    regulador_id: s.regulador_id ?? null,
    fecha_cierre: s.fecha_cierre ?? null,
    muelle: extraerMuelle(s.answers),
  }));

  const start = (page - 1) * pageSize;
  const end = start + pageSize;

  return { results: mapped.slice(start, end), count };
}

// ==== Buscar Fase 2 por placa (borrador/no finalizada)====
export async function buscarFase2PorPlaca(placa: string): Promise<SubmissionRow | null> {
  const url = new URL(`${API_BASE}submissions/`, window.location.origin);
  url.searchParams.set("tipo_fase", "salida");
  url.searchParams.set("incluir_borradores", "1"); // para traer no finalizadas
  url.searchParams.set("placa_vehiculo", placa);

  const res = await fetch(url.toString(), { credentials: "include", headers: authHeaders("GET") });
  const data = await parseOrThrow<any>(res, "No se pudo buscar Fase 2");

  // Soporta ambos: array plano o paginado (results)
  const list = Array.isArray(data) ? data : data.results ?? [];

  // Quédate con la más reciente NO finalizada
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

  const res = await fetch(`${API_BASE}submissions/`, {
    method: "POST",
    credentials: "include",
    headers: authHeaders("POST", { "Content-Type": "application/json" }),
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

