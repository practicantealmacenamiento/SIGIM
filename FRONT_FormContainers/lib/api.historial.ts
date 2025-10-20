const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "/api")
  .replace(/\/+$/, ""); // sin barra final

export type UUID = string;

/* ----------------------------- Tipos backend ----------------------------- */
export type ActorTipo = "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR";
export type ActorLite = {
  id: UUID;
  tipo: ActorTipo;
  nombre: string;
  documento?: string | null;
  activo?: boolean;
};

export type SubmissionLite = {
  id: UUID;
  questionnaire: string;
  questionnaire_title: string | null;
  tipo_fase: "entrada" | "salida";
  placa_vehiculo: string | null;
  regulador_id: string | null;
  finalizado: boolean;
  fecha_cierre: string | null;
  answers?: AnswerDetail[];

  proveedor_id?: string | null;
  proveedor?: { id?: string; nombre?: string; documento?: string } | null;
  transportista_id?: string | null;
  transportista?: { id?: string; nombre?: string; documento?: string } | null;
  receptor_id?: string | null;
  receptor?: { id?: string; nombre?: string; documento?: string } | null;
};

export type HistorialItem = {
  regulador_id: UUID | null;
  placa_vehiculo: string | null;
  contenedor?: string | null;
  ultima_fecha_cierre: string | null; // ISO
  fase1: SubmissionLite | null;
  fase2: SubmissionLite | null;
};

/* --------------------------- Utilidades fetch ---------------------------- */

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2)
    return decodeURIComponent(parts.pop()!.split(";").shift() || "");
  return null;
}

function getAuthToken(): string | null {
  // Preferimos la clave de admin; caemos a la histórica
  if (typeof localStorage !== "undefined") {
    const a = localStorage.getItem("auth:access_token");
    if (a) return a;
    const b = localStorage.getItem("auth_token");
    if (b) return b;
  }
  return readCookie("auth_token");
}

function hdr(method: string, extra?: HeadersInit) {
  const h = new Headers(extra || {});
  if (!h.has("Accept")) h.set("Accept", "application/json");
  const tok = getAuthToken();
  if (tok && !h.has("Authorization")) h.set("Authorization", `Bearer ${tok}`);
  return { method, credentials: "include" as const, headers: h };
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

  for (const k of Object.keys(data)) {
    const v = data[k];
    if (typeof v === "string" && v.trim()) return v;
    if (Array.isArray(v) && typeof v[0] === "string" && v[0].trim())
      return v[0];
  }
  return null;
}

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
  if (res.ok) {
    const ct = res.headers.get("Content-Type") || "";
    if (ct.includes("application/json")) return res.json();
    const txt = await res.text().catch(() => "");
    return (txt ? (JSON.parse(txt) as T) : (null as any)) as T;
  }
  const txt = await res.text().catch(() => "");
  try {
    const j = txt ? JSON.parse(txt) : null;
    const msg = pickErrorMessage(j) || res.statusText || fallback;
    throw new Error(msg);
  } catch {
    throw new Error(txt || res.statusText || fallback);
  }
}

/* ------------------------------ Endpoints ------------------------------- */
export async function fetchHistorial(params: {
  fecha_desde?: string;
  fecha_hasta?: string;
  solo_completados?: boolean; // por defecto true
}): Promise<HistorialItem[]> {
  const url = new URL(
    `${API_BASE}/historial/reguladores/`,
    typeof window !== "undefined"
      ? window.location.origin
      : "http://localhost"
  );
  if (params.fecha_desde) url.searchParams.set("fecha_desde", params.fecha_desde);
  if (params.fecha_hasta) url.searchParams.set("fecha_hasta", params.fecha_hasta);
  if (params.solo_completados !== false)
    url.searchParams.set("solo_completados", "1");

  const res = await fetchWithTimeout(url.toString(), hdr("GET"));
  const data = await parseOrThrow<any>(res, "No se pudo cargar el historial");

  // ✅ Soporta ambos formatos: array directo o paginado { results, count }
  const list = Array.isArray(data) ? data : data?.results ?? [];

  // 🔒 Dedupe temprano por si el backend trae repetidos
  return dedupeHistorialItems(list as HistorialItem[]);
}

/* --------- Detalle de submission (para hidratar actores y para UI) -------- */
export type AnswerDetail = {
  id: string;
  question: {
    id: string;
    text: string;
    type: string;
    semantic_tag?: string;
  } | null;
  answer_text: string | null;
  answer_choice: { id: string; text: string } | null;
  answer_file: string | null;
  timestamp: string;
};

export type SubmissionDetail = {
  id: string;
  questionnaire: string;
  questionnaire_title: string | null;
  tipo_fase: "entrada" | "salida";
  placa_vehiculo: string | null;
  regulador_id: string | null;
  finalizado: boolean;
  fecha_cierre: string | null;
  answers: AnswerDetail[];

  proveedor_id?: string | null;
  proveedor?: { id?: string; nombre?: string; documento?: string } | null;
  transportista_id?: string | null;
  transportista?: { id?: string; nombre?: string; documento?: string } | null;
  receptor_id?: string | null;
  receptor?: { id?: string; nombre?: string; documento?: string } | null;
};

export async function fetchSubmissionDetail(
  id: string
): Promise<SubmissionDetail> {
  const res = await fetchWithTimeout(
    `${API_BASE}/submissions/${id}/`,
    hdr("GET")
  );
  return await parseOrThrow<SubmissionDetail>(
    res,
    "No se pudo cargar la submission"
  );
}

/* --------------------- Helpers de visualización/actor -------------------- */
export function displayPlacaFromItem(it: HistorialItem): string {
  return (
    (it.placa_vehiculo ||
      it.fase1?.placa_vehiculo ||
      it.fase2?.placa_vehiculo ||
      "") as string
  ).toUpperCase();
}

export function getActor(
  sub: SubmissionLite | null | undefined,
  tipo: "proveedor" | "transportista" | "receptor"
): ActorLite | null {
  if (!sub) return null;
  if (tipo === "proveedor") {
    return sub.proveedor_id || sub.proveedor
      ? {
          id: String(sub.proveedor_id || sub.proveedor?.id || ""),
          tipo: "PROVEEDOR",
          nombre: sub.proveedor?.nombre || "",
          documento: sub.proveedor?.documento ?? null,
        }
      : null;
  }
  if (tipo === "transportista") {
    return sub.transportista_id || sub.transportista
      ? {
          id: String(sub.transportista_id || sub.transportista?.id || ""),
          tipo: "TRANSPORTISTA",
          nombre: sub.transportista?.nombre || "",
          documento: sub.transportista?.documento ?? null,
        }
      : null;
  }
  // receptor
  return sub.receptor_id || sub.receptor
    ? {
        id: String(sub.receptor_id || sub.receptor?.id || ""),
        tipo: "RECEPTOR",
        nombre: sub.receptor?.nombre || "",
        documento: sub.receptor?.documento ?? null,
      }
    : null;
}

const norm = (s: string) =>
  (s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

export function matchesActor(actor: ActorLite | null, text: string): boolean {
  if (!actor) return false;
  const n = norm(actor.nombre || "");
  const d = norm(actor.documento || "");
  const t = norm(text || "");
  return !!t && (n.includes(t) || d.includes(t));
}

export function displayActor(actor: ActorLite | null): string {
  if (!actor) return "";
  const base = actor.nombre?.trim() || "";
  const doc = (actor.documento || "").trim();
  return doc ? `${base} · ${doc}` : base;
}

/* -------------------- Hidratación de actores en batch -------------------- */
// Cache simple en memoria para evitar refetch del mismo id
const detailCache = new Map<string, SubmissionDetail>();

async function fetchDetailsBatch(ids: string[], maxConcurrent = 6) {
  const need = ids.filter((id) => !detailCache.has(id));
  for (let i = 0; i < need.length; i += maxConcurrent) {
    const slice = need.slice(i, i + maxConcurrent);
    const chunk = await Promise.allSettled(
      slice.map((id) => fetchSubmissionDetail(id))
    );
    for (let j = 0; j < slice.length; j++) {
      const k = slice[j];
      const r = chunk[j];
      if (r.status === "fulfilled") {
        detailCache.set(k, r.value);
      }
    }
  }
}

export async function hydrateActors(
  items: HistorialItem[],
  opts?: { maxConcurrent?: number }
) {
  // 1) recolectar ids que necesitan hidratarse
  const ids = new Set<string>();
  for (const it of items) {
    if (it.fase1?.id) ids.add(it.fase1.id);
    if (it.fase2?.id) ids.add(it.fase2.id);
  }
  // 2) fetch en batch
  await fetchDetailsBatch(
    Array.from(ids),
    Math.max(2, opts?.maxConcurrent ?? 6)
  );
  // 3) merge de actores en items
  return items.map((it) => {
    const merged: HistorialItem = JSON.parse(JSON.stringify(it));
    if (it.fase1?.id) {
      const det = detailCache.get(it.fase1.id);
      if (det) {
        if (
          !("proveedor_id" in merged) &&
          (det.proveedor_id || det.proveedor?.id)
        ) {
          (merged as any).proveedor_id =
            det.proveedor_id || det.proveedor?.id || null;
          (merged as any).proveedor = det.proveedor || null;
        }
        if (
          !("transportista_id" in merged) &&
          (det.transportista_id || det.transportista?.id)
        ) {
          (merged as any).transportista_id =
            det.transportista_id || det.transportista?.id || null;
          (merged as any).transportista = det.transportista || null;
        }
      }
    }
    if (it.fase2?.id) {
      const det = detailCache.get(it.fase2.id);
      if (det) {
        if (
          !("proveedor_id" in merged) &&
          (det.proveedor_id || det.proveedor?.id)
        ) {
          (merged as any).proveedor_id =
            det.proveedor_id || det.proveedor?.id || null;
          (merged as any).proveedor = det.proveedor || null;
        }
        if (
          !("transportista_id" in merged) &&
          (det.transportista_id || det.transportista?.id)
        ) {
          (merged as any).transportista_id =
            det.transportista_id || det.transportista?.id || null;
          (merged as any).transportista = det.transportista || null;
        }
      }
    }
    return merged;
  });
}

/* ------------------------- Enriquecimiento de filas ---------------------- */
function humanizeMinutes(m: number | null): string {
  if (!m && m !== 0) return "";
  const d = Math.floor(m / (60 * 24));
  const h = Math.floor((m % (60 * 24)) / 60);
  const mm = m % 60;
  const parts: string[] = [];
  if (d) parts.push(`${d}d`);
  if (h) parts.push(`${h}h`);
  parts.push(`${mm}m`);
  return parts.join(" ");
}

export type HistorialRow = {
  regulador_id: string | null;
  placa: string;
  contenedor: string | null;
  muelle: string | null;
  estado: "completo" | "pendiente";
  fase1_id: string | null;
  fase2_id: string | null;
  fecha_entrada: string | null;
  fecha_salida: string | null;
  ultima_fecha_cierre: string | null;
  tiempo_estadia_min: number | null;
  tiempo_estadia_humano: string | null;
  proveedor: { id?: string; nombre?: string; documento?: string } | null;
  transportista: { id?: string; nombre?: string; documento?: string } | null;
  cuestionario_fase1?: string | null;
  cuestionario_fase2?: string | null;
};

export function enrichHistorial(items: HistorialItem[]): HistorialRow[] {
  return items
    .map((it) => {
      const f1 = it.fase1 as any;
      const f2 = it.fase2 as any;
      const fecha_entrada = f1?.fecha_cierre || null;
      const fecha_salida = f2?.fecha_cierre || null;
      const ms =
        fecha_entrada && fecha_salida
          ? Math.max(
              0,
              new Date(fecha_salida).getTime() -
                new Date(fecha_entrada).getTime()
            )
          : null;

      const proveedor = (f2 && f2.proveedor) || (f1 && f1.proveedor) || null;
      const transportista =
        (f2 && f2.transportista) || (f1 && f1.transportista) || null;

      return {
        regulador_id: it.regulador_id ?? null,
        placa: displayPlacaFromItem(it),
        contenedor: it.contenedor ?? null,
        muelle: null,
        estado: ((it.fase1 && it.fase2) ? "completo" : "pendiente") as
          | "completo"
          | "pendiente",
        fase1_id: f1?.id || null,
        fase2_id: f2?.id || null,
        fecha_entrada,
        fecha_salida,
        ultima_fecha_cierre:
          it.ultima_fecha_cierre || fecha_salida || fecha_entrada || null,
        tiempo_estadia_min: ms != null ? Math.round(ms / 60000) : null,
        tiempo_estadia_humano:
          ms != null ? humanizeMinutes(Math.round(ms / 60000)) : null,
        proveedor: proveedor || null,
        transportista: transportista || null,
        cuestionario_fase1: f1?.questionnaire_title || null,
        cuestionario_fase2: f2?.questionnaire_title || null,
      } as HistorialRow;
    })
    .filter(Boolean);
}

/* --------------------------- Dedupe defensivo ---------------------------- */
function keyForItem(it: HistorialItem): string {
  const placa = (displayPlacaFromItem(it) || "").toUpperCase();
  const f1 = it.fase1?.id || "";
  const f2 = it.fase2?.id || "";
  const ult = it.ultima_fecha_cierre || "";
  return `${placa}::${f1}::${f2}::${ult}`;
}
export function dedupeHistorialItems(items: HistorialItem[]): HistorialItem[] {
  const seen = new Set<string>();
  const out: HistorialItem[] = [];
  for (const it of items) {
    const k = keyForItem(it);
    if (!seen.has(k)) {
      seen.add(k);
      out.push(it);
    }
  }
  return out;
}

function pickBetterRow(a: HistorialRow, b: HistorialRow): HistorialRow {
  // Preferimos la que tenga más info (fase2_id, proveedor, transportista, etc.)
  const score = (r: HistorialRow) =>
    (r.fase2_id ? 2 : 0) +
    (r.proveedor?.id ? 1 : 0) +
    (r.transportista?.id ? 1 : 0) +
    (r.tiempo_estadia_min ? 1 : 0);
  return score(b) > score(a) ? b : a;
}
export function dedupeRows(rows: HistorialRow[]): HistorialRow[] {
  const map = new Map<string, HistorialRow>();
  for (const r of rows) {
    const k = `${(r.placa || "").toUpperCase()}::${r.fase1_id || ""}::${r.fase2_id || ""}::${r.ultima_fecha_cierre || ""}`;
    const prev = map.get(k);
    map.set(k, prev ? pickBetterRow(prev, r) : r);
  }
  return Array.from(map.values());
}

/* ---------------- Búsqueda / orden / paginación (placa + actor) ---------------- */
export type HistorialQuery = {
  search?: string; // SOLO placa
  estado?: "completo" | "pendiente" | "todos";
  sort?: "reciente" | "antiguo" | "placa";
  dir?: "asc" | "desc";
  page?: number;
  pageSize?: number;
  actor_tipo?: "proveedor" | "transportista" | "todos";
  actor_text?: string; // nombre/documento
  actor_id_exact?: string | null; // si usas autocomplete y eliges uno
};

export function filterSortPaginate(rows: HistorialRow[], q: HistorialQuery = {}) {
  const {
    search = "",
    estado = "todos",
    sort = "reciente",
    dir = "desc",
    page = 1,
    pageSize = 20,
    actor_tipo = "todos",
    actor_text = "",
    actor_id_exact = null,
  } = q;

  let out = [...rows];

  // 1) Filtro por estado
  if (estado !== "todos") {
    out = out.filter((r) => r.estado === estado);
  }

  // 2) Filtro por placa (search)
  const s = norm(search);
  if (s) {
    out = out.filter((r) => norm(r.placa).includes(s));
  }

  // 3) Filtros por actor
  if (actor_tipo !== "todos" || actor_text || actor_id_exact) {
    out = out.filter((r) => {
      const actor =
        actor_tipo === "proveedor"
          ? r.proveedor
          : actor_tipo === "transportista"
          ? r.transportista
          : null;

      if (actor_id_exact) {
        return (actor?.id || "") === actor_id_exact;
      }
      if (actor_text) {
        const nn = norm(actor?.nombre || "");
        const nd = norm(actor?.documento || "");
        const tt = norm(actor_text);
        return !!tt && (nn.includes(tt) || nd.includes(tt));
      }
      // si no hay criterios, no filtramos
      return true;
    });
  }

  // 4) Orden
  out.sort((a, b) => {
    if (sort === "placa") {
      const A = (a.placa || "").toUpperCase();
      const B = (b.placa || "").toUpperCase();
      const cmp = A.localeCompare(B);
      return dir === "asc" ? cmp : -cmp;
    }
    // reciente/antiguo usa ultima_fecha_cierre (fallback a fecha_salida/entrada)
    const fa =
      a.ultima_fecha_cierre ||
      a.fecha_salida ||
      a.fecha_entrada ||
      "1900-01-01T00:00:00Z";
    const fb =
      b.ultima_fecha_cierre ||
      b.fecha_salida ||
      b.fecha_entrada ||
      "1900-01-01T00:00:00Z";
    const cmp = new Date(fa).getTime() - new Date(fb).getTime();
    return sort === "antiguo"
      ? dir === "asc"
        ? cmp
        : -cmp
      : dir === "asc"
      ? -cmp
      : cmp;
  });

  // 5) Paginación
  const count = out.length;
  const start = Math.max(0, (page - 1) * pageSize);
  const end = Math.min(out.length, start + pageSize);
  return { results: out.slice(start, end), count };
}

/* --------------- Pipeline: fetch + hydrate + enrich + filtros -------------- */
export async function fetchHistorialEnriched(
  params: Parameters<typeof fetchHistorial>[0],
  query?: HistorialQuery,
  opts?: { hydrate?: boolean; maxConcurrent?: number }
): Promise<{ results: HistorialRow[]; count: number }> {
  // 1) traer y deduplicar items crudos
  const raw = await fetchHistorial(params); // ya viene dedupe de fetchHistorial
  // 2) hidratar actores si aplica
  const withActors =
    opts?.hydrate === false
      ? raw
      : await hydrateActors(raw, { maxConcurrent: opts?.maxConcurrent });
  // 3) enriquecer → filas UI
  const rowsEnriched = enrichHistorial(withActors);
  // 4) dedupe defensivo a nivel filas enriquecidas
  const rows = dedupeRows(rowsEnriched);
  // 5) filtros/orden/paginación (count es sobre la colección ya deduplicada)
  return filterSortPaginate(rows, query);
}

/* ------------------------------ Búsqueda actores -------------------------- */
export async function searchActors(
  params: { tipo: "proveedor" | "transportista" | "receptor"; q?: string }
): Promise<ActorLite[]> {
  const url = new URL(
    `${API_BASE}/catalogos/actores/`,
    typeof window !== "undefined"
      ? window.location.origin
      : "http://localhost"
  );
  const tipoBack =
    params.tipo === "proveedor"
      ? "PROVEEDOR"
      : params.tipo === "transportista"
      ? "TRANSPORTISTA"
      : "RECEPTOR";
  url.searchParams.set("tipo", tipoBack);
  if (params.q && params.q.trim())
    url.searchParams.set("search", params.q.trim());

  const res = await fetchWithTimeout(url.toString(), hdr("GET"));
  const data = await parseOrThrow<any>(res, "No se pudo buscar actores");

  // ✅ Soporta ambos formatos
  const list = Array.isArray(data) ? data : data?.results ?? [];
  return (list as ActorLite[]).slice(0, 50);
}

/* ----------------------------- Exportación CSV ---------------------------- */
export function exportHistorialCSV(
  rows: HistorialRow[],
  filename = "historial.csv"
) {
  // Por si llaman con filas sin dedupe desde fuera
  const safeRows = dedupeRows(rows);

  const headers = [
    "Regulador ID",
    "Placa",
    "Contenedor",
    "Muelle",
    "Estado",
    "Fase 1 ID",
    "Fase 2 ID",
    "Fecha entrada",
    "Fecha salida",
    "Última fecha cierre",
    "Tiempo estadía (min)",
    "Tiempo estadía (humano)",
    "Cuestionario Fase 1",
    "Cuestionario Fase 2",
    "Proveedor",
    "Doc. Proveedor",
    "Transportista",
    "Doc. Transportista",
  ];

  const lines: string[] = [];
  lines.push(headers.join(","));

  for (const r of safeRows) {
    const row = [
      r.regulador_id ?? "",
      r.placa ?? "",
      r.contenedor ?? "",
      r.muelle ?? "",
      r.estado,
      r.fase1_id ?? "",
      r.fase2_id ?? "",
      r.fecha_entrada ?? "",
      r.fecha_salida ?? "",
      r.ultima_fecha_cierre ?? "",
      r.tiempo_estadia_min ?? "",
      r.tiempo_estadia_humano ?? "",
      (r as any).cuestionario_fase_1 || r.cuestionario_fase1 || "",
      (r as any).cuestionario_fase_2 || r.cuestionario_fase2 || "",
      r.proveedor?.nombre ?? "",
      r.proveedor?.documento ?? "",
      r.transportista?.nombre ?? "",
      r.transportista?.documento ?? "",
    ];
    lines.push(
      row
        .map((cell) => {
          const s = String(cell ?? "");
          return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
        })
        .join(",")
    );
  }
  const blob = new Blob([lines.join("\n")], {
    type: "text/csv;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
