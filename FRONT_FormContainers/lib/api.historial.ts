/* eslint-disable @typescript-eslint/no-explicit-any */
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

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
  questionnaire: UUID;
  questionnaire_title: string | null;
  tipo_fase: "entrada" | "salida";
  placa_vehiculo: string | null;
  regulador_id: UUID | null;
  finalizado: boolean;
  fecha_cierre: string | null;

  // Estos campos pueden NO venir en el historial y por eso los hidratamos:
  proveedor_id?: UUID | null;
  transportista_id?: UUID | null;
  receptor_id?: UUID | null;
  proveedor?: ActorLite | null;
  transportista?: ActorLite | null;
  receptor?: ActorLite | null;
};

export type HistorialItem = {
  regulador_id: UUID | null;           // a veces puede venir null si aún no existe el regulador
  placa_vehiculo: string | null;
  contenedor?: string | null;          // no se usa para filtrar en historial
  ultima_fecha_cierre: string | null;  // ISO
  fase1: SubmissionLite | null;
  fase2: SubmissionLite | null;
};

/* --------------------------- Utilidades fetch ---------------------------- */
// 🔑 Lee token desde LS o cookie; si no hay, igual mandamos cookies de sesión
const ADMIN_TOKEN_KEY = "admin_token";

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}
function getAuthToken(): string | null {
  try {
    if (typeof localStorage !== "undefined") {
      // usa la clave que ya manejas en otras libs si existe
      const t =
        localStorage.getItem(ADMIN_TOKEN_KEY) ||
        localStorage.getItem("AUTH_TOKEN") ||
        localStorage.getItem("auth_token");
      if (t) return t;
    }
  } catch {}
  return getCookie("auth_token");
}

function hdr(method: string, init: RequestInit = {}): RequestInit {
  const headers = new Headers(init.headers || {});
  const tok = getAuthToken();
  if (tok && !headers.has("Authorization")) headers.set("Authorization", `Token ${tok}`);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");

  return {
    ...init,
    method,
    headers,
    credentials: "include",   // 🔒 manda cookies (sessionid, csrftoken, etc.)
    cache: "no-store",
    redirect: "manual",       // evita caer en HTML si el back redirige
  };
}

async function parseOrThrow<T>(res: Response, fallback: string): Promise<T> {
  if (res.ok) return res.json();
  const txt = await res.text().catch(() => "");
  try {
    const j = JSON.parse(txt);
    throw new Error(j?.detail || j?.error || fallback);
  } catch {
    throw new Error(txt || fallback);
  }
}

/* ------------------------------ Endpoints ------------------------------- */
export async function fetchHistorial(params: {
  fecha_desde?: string;
  fecha_hasta?: string;
  solo_completados?: boolean; // por defecto true
}): Promise<HistorialItem[]> {
  const url = new URL(
    `${API_BASE}historial/reguladores/`,
    typeof window !== "undefined" ? window.location.origin : "http://localhost"
  );
  if (params.fecha_desde) url.searchParams.set("fecha_desde", params.fecha_desde);
  if (params.fecha_hasta) url.searchParams.set("fecha_hasta", params.fecha_hasta);
  if (params.solo_completados !== false) url.searchParams.set("solo_completados", "1");

  const res = await fetch(url.toString(), hdr("GET"));
  const data = await parseOrThrow<HistorialItem[]>(res, "No se pudo cargar el historial");
  const items = Array.isArray(data) ? data : [];

  // 🔒 Dedupe temprano por si el backend trae repetidos
  return dedupeHistorialItems(items);
}

/* --------- Detalle de submission (para hidratar actores y para UI) -------- */
export type AnswerDetail = {
  id: string;
  question: { id: string; text: string; type: string; semantic_tag?: string } | null;
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

export async function fetchSubmissionDetail(id: string): Promise<SubmissionDetail> {
  // 🔧 slash final para evitar 301/308 (pierden Authorization)
  const url = `${API_BASE}submissions/${id}/`;
  const res = await fetch(url, hdr("GET"));
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(txt || "No se pudo cargar la submission");
  }
  return res.json();
}

/* --------------------- Helpers de visualización/actor -------------------- */
export function displayPlacaFromItem(it: HistorialItem): string {
  return (
    (it.placa_vehiculo || it.fase1?.placa_vehiculo || it.fase2?.placa_vehiculo || "") as string
  ).toUpperCase();
}

// compat con el nombre previo
export const displayPlaca = displayPlacaFromItem;

export function getActor(
  it: HistorialItem,
  tipo: "proveedor" | "transportista" | "receptor"
): ActorLite | null {
  const f2 = it.fase2 as any;
  const f1 = it.fase1 as any;
  return (f2 && f2[tipo]) || (f1 && f1[tipo]) || null;
}

export function matchesActor(
  it: HistorialItem,
  actorId: UUID,
  tipo: "proveedor" | "transportista" | "receptor"
): boolean {
  const f1 = it.fase1 as any;
  const f2 = it.fase2 as any;
  const idKey = (tipo + "_id") as "proveedor_id" | "transportista_id" | "receptor_id";
  return Boolean(
    (f2 && f2[idKey] && String(f2[idKey]) === String(actorId)) ||
      (f1 && f1[idKey] && String(f1[idKey]) === String(actorId))
  );
}

export function displayActor(actor?: ActorLite | null): string {
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
    const chunk = await Promise.allSettled(slice.map((id) => fetchSubmissionDetail(id)));
    chunk.forEach((res, idx) => {
      const id = slice[idx];
      if (res.status === "fulfilled") detailCache.set(id, res.value);
    });
  }
  return detailCache;
}

/**
 * Recorre items y, si a alguna fase le faltan actores (ids u objetos),
 * trae el detalle y fusiona proveedor/transportista.
 */
export async function hydrateActors(
  items: HistorialItem[],
  opts?: { maxConcurrent?: number }
): Promise<HistorialItem[]> {
  // 1) recolectar ids que necesitan hidratarse
  const ids: string[] = [];
  for (const it of items) {
    for (const sub of [it.fase1 as any, it.fase2 as any]) {
      if (!sub?.id) continue;
      const hasProv = "proveedor" in sub || "proveedor_id" in sub;
      const hasTrans = "transportista" in sub || "transportista_id" in sub;
      if (!hasProv || !hasTrans) ids.push(sub.id);
    }
  }
  if (ids.length === 0) return items;

  // 2) fetch detalles y cache
  await fetchDetailsBatch(Array.from(new Set(ids)), opts?.maxConcurrent ?? 6);

  // 3) fusionar
  return items.map((it) => {
    const fase = (k: "fase1" | "fase2") => {
      const base = (it[k] || null) as any;
      if (!base?.id) return base;
      const det = detailCache.get(base.id);
      if (!det) return base;
      // copia superficial + merge de actores si faltan
      const merged: any = { ...base };
      if (!("proveedor_id" in merged) && (det.proveedor_id || det.proveedor?.id)) {
        merged.proveedor_id = det.proveedor_id ?? det.proveedor?.id ?? null;
      }
      if (!("proveedor" in merged) && det.proveedor) {
        merged.proveedor = det.proveedor as any;
      }
      if (!("transportista_id" in merged) && (det.transportista_id || det.transportista?.id)) {
        merged.transportista_id = det.transportista_id ?? det.transportista?.id ?? null;
      }
      if (!("transportista" in merged) && det.transportista) {
        merged.transportista = det.transportista as any;
      }
      return merged;
    };
    return { ...it, fase1: fase("fase1"), fase2: fase("fase2") };
  });
}

/* ---------------------- Enriquecimiento para la UI ---------------------- */
export type HistorialRow = {
  regulador_id: UUID | null;
  placa: string;

  contenedor: string | null; // compat (no filtra)
  muelle: string | null;     // no se usa en historial

  estado: "completo" | "pendiente";
  fase1_id: UUID | null;
  fase2_id: UUID | null;
  fecha_entrada: string | null;
  fecha_salida: string | null;
  ultima_fecha_cierre: string | null;

  tiempo_estadia_ms: number | null;
  tiempo_estadia_humano: string | null;

  cuestionario_fase1?: string | null;
  cuestionario_fase2?: string | null;

  proveedor?: ActorLite | null;
  transportista?: ActorLite | null;
};

function humanizeDuration(ms?: number | null) {
  if (!ms || ms < 0) return null;
  const m = Math.floor(ms / 60000);
  const d = Math.floor(m / (60 * 24));
  const h = Math.floor((m % (60 * 24)) / 60);
  const mm = m % 60;
  const parts = [];
  if (d) parts.push(`${d}d`);
  if (h) parts.push(`${h}h`);
  parts.push(`${mm}m`);
  return parts.join(" ");
}

export function enrichHistorial(items: HistorialItem[]): HistorialRow[] {
  return items
    .map((it) => {
      const f1 = it.fase1 as any;
      const f2 = it.fase2 as any;
      const fecha_entrada = f1?.fecha_cierre || null;
      const fecha_salida = f2?.fecha_cierre || null;
      const ms =
        fecha_entrada && fecha_salida
          ? Math.max(0, new Date(fecha_salida).getTime() - new Date(fecha_entrada).getTime())
          : null;

      const proveedor = (f2 && f2.proveedor) || (f1 && f1.proveedor) || null;
      const transportista = (f2 && f2.transportista) || (f1 && f1.transportista) || null;

      return {
        regulador_id: it.regulador_id ?? null,
        placa: displayPlacaFromItem(it),
        contenedor: it.contenedor ?? null,
        muelle: null,
        estado: it.fase1 && it.fase2 ? "completo" : "pendiente",
        fase1_id: f1?.id || null,
        fase2_id: f2?.id || null,
        fecha_entrada,
        fecha_salida,
        ultima_fecha_cierre: it.ultima_fecha_cierre || fecha_salida || fecha_entrada || null,
        tiempo_estadia_ms: ms,
        tiempo_estadia_humano: humanizeDuration(ms),
        cuestionario_fase1: f1?.questionnaire_title ?? null,
        cuestionario_fase2: f2?.questionnaire_title ?? null,
        proveedor,
        transportista,
      };
    })
    .sort((a, b) => {
      const ta = a.ultima_fecha_cierre ? Date.parse(a.ultima_fecha_cierre) : 0;
      const tb = b.ultima_fecha_cierre ? Date.parse(b.ultima_fecha_cierre) : 0;
      return tb - ta; // más reciente primero
    });
}

/* ---------------------- Deduplicación (core de fix) ---------------------- */
// Clave única robusta a ausencia de regulador_id
function makeItemKey(it: HistorialItem) {
  const f1 = it.fase1?.id ?? "_";
  const f2 = it.fase2?.id ?? "_";
  const reg = it.regulador_id ?? "_";
  const placa = (it.placa_vehiculo || it.fase1?.placa_vehiculo || it.fase2?.placa_vehiculo || "_").toUpperCase();
  return `${reg}::${f1}::${f2}::${placa}`;
}

// Preferir el que tenga más fases cerradas; si empata, el más reciente
function scoreItem(x: HistorialItem) {
  const n = (x.fase1 ? 1 : 0) + (x.fase2 ? 1 : 0);
  const t = Date.parse(x.ultima_fecha_cierre || x.fase2?.fecha_cierre || x.fase1?.fecha_cierre || "1970-01-01T00:00:00Z");
  return [n, t] as const;
}
function pickBetterItem(a: HistorialItem, b: HistorialItem) {
  const [na, ta] = scoreItem(a);
  const [nb, tb] = scoreItem(b);
  if (na !== nb) return na > nb ? a : b;
  return ta >= tb ? a : b;
}

export function dedupeHistorialItems(input: HistorialItem[]): HistorialItem[] {
  const map = new Map<string, HistorialItem>();
  for (const it of input) {
    const key =
      it.regulador_id ||
      makeItemKey(it); // si no hay regulador, usamos una clave compuesta
    const prev = map.get(key);
    map.set(key, prev ? pickBetterItem(prev, it) : it);
  }
  return Array.from(map.values());
}

// Dedup de filas enriquecidas (defensa extra por si algo se “coló”)
function makeRowKey(r: HistorialRow) {
  return `${r.regulador_id ?? "_"}::${r.fase1_id ?? "_"}::${r.fase2_id ?? "_"}::${r.placa ?? "_"}`;
}
function scoreRow(x: HistorialRow) {
  const n = (x.fase1_id ? 1 : 0) + (x.fase2_id ? 1 : 0);
  const t = Date.parse(x.ultima_fecha_cierre || "1970-01-01T00:00:00Z");
  return [n, t] as const;
}
function pickBetterRow(a: HistorialRow, b: HistorialRow) {
  const [na, ta] = scoreRow(a);
  const [nb, tb] = scoreRow(b);
  if (na !== nb) return na > nb ? a : b;
  return ta >= tb ? a : b;
}
export function dedupeRows(rows: HistorialRow[]): HistorialRow[] {
  const map = new Map<string, HistorialRow>();
  for (const r of rows) {
    const k = r.regulador_id || makeRowKey(r);
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
  actor_text?: string; // nombre/documento/id cuando no hay selección exacta
  actor_id_exact?: string | null; // si usas autocomplete y eliges uno
};

const norm = (s: string) =>
  (s || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

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

  const s = norm(search);
  const actxt = norm(actor_text);

  // (1) filtro
  let base = rows.filter((r) => {
    const okEstado = estado === "todos" ? true : r.estado === estado;
    const okSearch = !s ? true : norm(r.placa).includes(s);

    let okActor = true;
    if (actor_tipo !== "todos") {
      const a = (r as any)[actor_tipo] as ActorLite | null;
      okActor = !!a;
      if (okActor && actor_id_exact) {
        okActor = String(a?.id || "") === String(actor_id_exact);
      } else if (okActor && actxt) {
        const blob = `${a?.nombre || ""} ${a?.documento || ""} ${a?.id || ""}`;
        okActor = norm(blob).includes(actxt);
      }
    } else if (actxt) {
      const blob = `${r.proveedor?.nombre || ""} ${r.proveedor?.documento || ""} ${r.transportista?.nombre || ""} ${r.transportista?.documento || ""}`;
      okActor = norm(blob).includes(actxt);
    }

    return okEstado && okSearch && okActor;
  });

  // (2) orden
  const mult = dir === "asc" ? 1 : -1;
  base.sort((a, b) => {
    if (sort === "placa") return a.placa.localeCompare(b.placa) * mult;
    const ta = a.ultima_fecha_cierre ? Date.parse(a.ultima_fecha_cierre) : 0;
    const tb = b.ultima_fecha_cierre ? Date.parse(b.ultima_fecha_cierre) : 0;
    const recentCmp = tb - ta;
    return (sort === "antiguo" ? -recentCmp : recentCmp) * (dir === "asc" ? -1 : 1);
  });

  // (3) paginación
  const start = Math.max(0, (page - 1) * pageSize);
  const results = base.slice(start, start + pageSize);
  return { results, count: base.length };
}

/* ---------- Pipeline completo: trae → hidrata actores → enriquece → pagina ---------- */
export async function fetchHistorialEnriched(
  params: Parameters<typeof fetchHistorial>[0],
  query?: HistorialQuery,
  opts?: { hydrate?: boolean; maxConcurrent?: number }
): Promise<{ results: HistorialRow[]; count: number }> {
  // 1) traer y deduplicar items crudos
  const raw = await fetchHistorial(params); // ya viene dedupe de fetchHistorial
  // 2) hidratar actores si aplica
  const withActors =
    opts?.hydrate === false ? raw : await hydrateActors(raw, { maxConcurrent: opts?.maxConcurrent });
  // 3) enriquecer → filas UI
  const rowsEnriched = enrichHistorial(withActors);
  // 4) dedupe defensivo a nivel filas enriquecidas
  const rows = dedupeRows(rowsEnriched);
  // 5) filtros/orden/paginación (count es sobre la colección ya deduplicada)
  return filterSortPaginate(rows, query);
}

/* ------------------- Autocomplete remoto de actores (opcional) ------------------- */
export async function searchActors(
  params: { tipo: "proveedor" | "transportista" | "receptor"; q?: string }
): Promise<ActorLite[]> {
  const url = new URL(
    `${API_BASE}/actors/`,
    typeof window !== "undefined" ? window.location.origin : "http://localhost"
  );
  const tipoBack =
    params.tipo === "proveedor"
      ? "PROVEEDOR"
      : params.tipo === "transportista"
      ? "TRANSPORTISTA"
      : "RECEPTOR";
  url.searchParams.set("tipo", tipoBack);
  if (params.q && params.q.trim()) url.searchParams.set("search", params.q.trim());

  const res = await fetch(url.toString(), hdr("GET"));
  const data = await parseOrThrow<ActorLite[]>(res, "No se pudo buscar actores");
  return Array.isArray(data) ? data.slice(0, 50) : [];
}

/* ----------------------------- Exportación CSV ---------------------------- */
export function exportHistorialCSV(rows: HistorialRow[], filename = "historial.csv") {
  // Por si llaman con filas sin dedupe desde fuera
  const safeRows = dedupeRows(rows);

  const header = [
    "Regulador ID",
    "Placa",
    "Estado",
    "Fase1 ID",
    "Fase2 ID",
    "Fecha entrada",
    "Fecha salida",
    "Última fecha",
    "Tiempo estadía",
    "Cuestionario F1",
    "Cuestionario F2",
    "Proveedor (nombre)",
    "Proveedor (doc)",
    "Transportista (nombre)",
    "Transportista (doc)",
  ];
  const lines = [header.join(",")];
  for (const r of safeRows) {
    const row = [
      r.regulador_id ?? "",
      r.placa ?? "",
      r.estado ?? "",
      r.fase1_id ?? "",
      r.fase2_id ?? "",
      r.fecha_entrada ?? "",
      r.fecha_salida ?? "",
      r.ultima_fecha_cierre ?? "",
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
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}


