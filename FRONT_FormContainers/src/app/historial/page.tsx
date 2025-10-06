"use client";
import { useEffect, useMemo, useRef, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  fetchHistorialEnriched,
  exportHistorialCSV,
  type HistorialRow,
  type HistorialQuery,
} from "@/lib/api.historial";
import { listActors } from "@/lib/api.admin";

/* ——— UI tokens ——— */
const CARD =
  "rounded-2xl border border-slate-200/70 dark:border-white/10 bg-white dark:bg-slate-900 shadow-sm";
const INPUT =
  "rounded-xl border border-slate-300 dark:border-white/15 px-3 py-2 outline-none focus:ring-2 focus:ring-skyBlue/30 bg-white dark:bg-slate-900";
const BTN =
  "min-h-[40px] px-4 py-2 rounded-xl border border-slate-300 dark:border-white/20 hover:bg-slate-50 dark:hover:bg-white/5 transition disabled:opacity-50 disabled:cursor-not-allowed";

/* ——— helpers ——— */
const tz = "America/Bogota";
const fmtDateTime = (iso?: string | null) =>
  iso
    ? new Intl.DateTimeFormat("es-CO", { timeZone: tz, dateStyle: "medium", timeStyle: "short" }).format(new Date(iso))
    : "—";
const fmtShortDate = (iso?: string) => {
  if (!iso) return "";
  const d = new Date(iso);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
};

function statusVisual(state: "completo" | "pendiente") {
  if (state === "completo") {
    return {
      icon: "✅",
      label: "Completo",
      bar: "bg-emerald-500",
      badge: "bg-emerald-50 text-emerald-700 border-emerald-200/70 dark:bg-emerald-400/10 dark:text-emerald-300 dark:border-emerald-300/20",
      dot: "bg-emerald-500",
    };
  }
  return {
    icon: "⏳",
    label: "Pendiente",
    bar: "bg-amber-400",
    badge: "bg-amber-50 text-amber-800 border-amber-200/70 dark:bg-amber-400/10 dark:text-amber-300 dark:border-amber-300/20",
    dot: "bg-amber-400",
  };
}

/* ——— dedupe ——— */

function mergeActors(primary: HistorialRow, secondary?: HistorialRow): HistorialRow {
  if (!secondary) return primary;
  return {
    ...primary,
    proveedor: primary.proveedor ?? secondary.proveedor ?? null,
    transportista: primary.transportista ?? secondary.transportista ?? null,
  };
}

function pickBetter(a: HistorialRow, b: HistorialRow) {
  const score = (x: HistorialRow) => (x.fase1_id ? 1 : 0) + (x.fase2_id ? 1 : 0);
  const ts = (x: HistorialRow) =>
    new Date(x.ultima_fecha_cierre || x.fecha_salida || x.fecha_entrada || 0).getTime();

  // Elige la “mejor” por puntaje y luego por fecha
  const better = score(a) !== score(b) ? (score(a) > score(b) ? a : b) : (ts(a) >= ts(b) ? a : b);
  const other = better === a ? b : a;

  // Merge solo de actores para no perder proveedor/transportista
  return mergeActors(better, other);
}
function normalizeRows(input: HistorialRow[]): HistorialRow[] {
  const map = new Map<string, HistorialRow>();
  for (const r of input) {
    const k = r.regulador_id || `${r.fase1_id ?? ""}/${r.fase2_id ?? ""}/${r.placa ?? ""}`;
    const prev = map.get(k);
    map.set(k, prev ? pickBetter(prev, r) : r);
  }
  return Array.from(map.values());
}

/* ——— key única para React ——— */
function rowKey(r: HistorialRow, index?: number) {
  const baseKey = `${r.regulador_id ?? "reg"}::${r.fase1_id ?? "_"}::${r.fase2_id ?? "_"}::${r.placa ?? "_"}`;
  return index !== undefined ? `${baseKey}::${index}` : baseKey;
}

/* ——— tipos ——— */
type Estado = "todos" | "completo" | "pendiente";
type SortKey = HistorialQuery["sort"];
type SortDir = HistorialQuery["dir"];
type ActorTipo = "todos" | "proveedor" | "transportista";
type ActorOption = {
  id: string;
  nombre: string;
  documento: string;
  tipo: "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR" | string;
};
type ViewMode = "cards" | "table";

/* ——— utils URL ——— */
function setQuery(router: ReturnType<typeof useRouter>, params: URLSearchParams, kv: Record<string, any>) {
  const p = new URLSearchParams(params.toString());
  Object.entries(kv).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "" || v === "null") p.delete(k);
    else p.set(k, String(v));
  });
  router.replace(`?${p.toString()}`);
}

function HistorialContent() {
  const router = useRouter();
  const urlParams = useSearchParams();

  /* ——— Filtros ——— */
  const [desde, setDesde] = useState<string>(urlParams.get("desde") || "");
  const [hasta, setHasta] = useState<string>(urlParams.get("hasta") || "");
  const [estado, setEstado] = useState<Estado>((urlParams.get("estado") as Estado) || "completo");
  const [search, setSearch] = useState<string>(urlParams.get("q") || "");

  /* ——— Actor ——— */
  const [actorTipo, setActorTipo] = useState<ActorTipo>((urlParams.get("actor_tipo") as ActorTipo) || "todos");
  const [actorInput, setActorInput] = useState<string>(urlParams.get("actor_text") || "");
  const [actorSel, setActorSel] = useState<ActorOption | null>(() => {
    const id = urlParams.get("actor_id");
    const name = urlParams.get("actor_name");
    const tipo = urlParams.get("actor_tipo_api") || (actorTipo === "proveedor" ? "PROVEEDOR" : actorTipo === "transportista" ? "TRANSPORTISTA" : "");
    return id ? { id, nombre: name || id, documento: "", tipo } : null;
  });
  const [actorOpts, setActorOpts] = useState<ActorOption[]>([]);
  const [actorLoading, setActorLoading] = useState(false);
  const [actorPopoverOpen, setActorPopoverOpen] = useState(false);
  const actorInputRef = useRef<HTMLInputElement>(null);
  const actorRef = useRef<HTMLDivElement | null>(null);

  /* ——— Orden/paginación ——— */
  const [sort, setSort] = useState<SortKey>((urlParams.get("sort") as SortKey) || "reciente");
  const [dir, setDir] = useState<SortDir>((urlParams.get("dir") as SortDir) || "desc");
  const [page, setPage] = useState<number>(Number(urlParams.get("page") || 1));
  const [pageSize, setPageSize] = useState<number>(Number(urlParams.get("pageSize") || 20));

  /* ——— Vista ——— */
  const [view, setView] = useState<ViewMode>((urlParams.get("view") as ViewMode) || "cards");

  /* ——— Datos ——— */
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState<HistorialRow[]>([]);
  const [count, setCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  /* ——— Contadores globales ——— */
  const [countComp, setCountComp] = useState<number | null>(null);
  const [countPend, setCountPend] = useState<number | null>(null);

  /* ——— Menú y fecha ——— */
  const [menuOpen, setMenuOpen] = useState(false);
  const [dateOpen, setDateOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const dateRef = useRef<HTMLDivElement | null>(null);

  /* ——— Autorefresh ——— */
  const [autoRefresh, setAutoRefresh] = useState<boolean>(urlParams.get("auto") === "1");

  /* ——— Anti-race para load() ——— */
  const loadSeq = useRef(0);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      const t = e.target as Node;
      if (menuRef.current && !menuRef.current.contains(t)) setMenuOpen(false);
      if (dateRef.current && !dateRef.current.contains(t)) setDateOpen(false);
      if (actorRef.current && !actorRef.current.contains(t)) setActorPopoverOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  /* ——— Load principal ——— */
  async function load() {
    const mySeq = ++loadSeq.current;
    try {
      setError(null);
      setLoading(true);

      setQuery(router, urlParams, {
        desde, hasta, estado, q: search,
        actor_tipo: actorTipo,
        actor_text: actorSel ? "" : actorInput,
        actor_id: actorSel?.id,
        actor_name: actorSel?.nombre,
        actor_tipo_api: actorSel?.tipo,
        sort, dir, page, pageSize, view, auto: autoRefresh ? "1" : "",
      });

      const { results, count } = await fetchHistorialEnriched(
        { fecha_desde: desde || undefined, fecha_hasta: hasta || undefined, solo_completados: estado === "completo" },
        {
          search, estado, sort, dir, page, pageSize,
          actor_tipo: actorTipo === "todos" ? "todos" : actorTipo,
          actor_text: actorSel ? "" : actorInput,
          actor_id_exact: actorSel?.id ?? null,
        }
      );

      if (mySeq !== loadSeq.current) return;

      const normalized = normalizeRows(results);
      setRows(normalized);
      setCount(count);

      const [c1, c2] = await Promise.all([
        fetchHistorialEnriched(
          { fecha_desde: desde || undefined, fecha_hasta: hasta || undefined, solo_completados: true },
          { search, estado: "completo", sort: "reciente", dir: "desc", page: 1, pageSize: 1, actor_tipo: actorTipo === "todos" ? "todos" : actorTipo, actor_text: actorSel ? "" : actorInput, actor_id_exact: actorSel?.id ?? null }
        ),
        fetchHistorialEnriched(
          { fecha_desde: desde || undefined, fecha_hasta: hasta || undefined, solo_completados: false },
          { search, estado: "pendiente", sort: "reciente", dir: "desc", page: 1, pageSize: 1, actor_tipo: actorTipo === "todos" ? "todos" : actorTipo, actor_text: actorSel ? "" : actorInput, actor_id_exact: actorSel?.id ?? null }
        ),
      ]);

      if (mySeq !== loadSeq.current) return;
      setCountComp(c1.count);
      setCountPend(c2.count);
    } catch (e: any) {
      if (mySeq !== loadSeq.current) return;
      setError(e.message || "Error cargando historial");
    } finally {
      if (mySeq !== loadSeq.current) return;
      setLoading(false);
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [page, sort, dir, pageSize, view]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, desde, hasta, estado, search, actorTipo, actorInput, actorSel, sort, dir, page, pageSize]);

  /* ——— Autocomplete ——— */
  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    if (actorTipo === "todos" || !actorInput.trim() || actorSel) {
      setActorOpts([]); return () => controller.abort();
    }

    setActorLoading(true);
    const t = setTimeout(async () => {
      try {
        const tipoParam = actorTipo === "proveedor" ? "PROVEEDOR" : actorTipo === "transportista" ? "TRANSPORTISTA" : "";
        const list = await listActors({ tipo: tipoParam, search: actorInput.trim() });
        if (!active) return;
        setActorOpts((list || []).map((a: any) => ({ id: a.id, nombre: a.nombre, documento: a.documento, tipo: a.tipo })));
      } finally {
        if (active) setActorLoading(false);
      }
    }, 250);

    return () => { active = false; clearTimeout(t); controller.abort(); };
  }, [actorInput, actorTipo, actorSel]);

  /* ——— helpers UI ——— */
  function clearActorSelection() {
    setActorSel(null); setActorInput(""); setActorOpts([]); actorInputRef.current?.focus(); setPage(1);
  }
  function toggleSort(next: Exclude<SortKey, undefined>) {
    if (sort === next) setDir((d) => (d === "asc" ? "desc" : "asc")); else { setSort(next); setDir("asc"); }
    setPage(1);
  }
  async function exportCSVAll() {
    try {
      const { results: all } = await fetchHistorialEnriched(
        { fecha_desde: desde || undefined, fecha_hasta: hasta || undefined, solo_completados: estado === "completo" },
        { search, estado, sort, dir, page: 1, pageSize: Math.max(count, 1), actor_tipo: actorTipo === "todos" ? "todos" : actorTipo, actor_text: actorSel ? "" : actorInput, actor_id_exact: actorSel?.id ?? null }
      );
      exportHistorialCSV(normalizeRows(all), "historial.csv");
    } catch (e: any) { alert(e?.message || "No se pudo exportar"); }
  }
  function clearFilters() {
    setDesde(""); setHasta(""); setEstado("completo"); setSearch("");
    setActorTipo("todos"); setActorInput(""); setActorSel(null); setActorOpts([]);
    setSort("reciente"); setDir("desc"); setPage(1); load();
  }
  function applyPreset(p: "hoy" | "7" | "mes") {
    const now = new Date(); const pad = (n: number) => String(n).padStart(2, "0");
    const y = now.getFullYear(); const m = pad(now.getMonth() + 1); const d = pad(now.getDate());
    if (p === "hoy") { setDesde(`${y}-${m}-${d}`); setHasta(`${y}-${m}-${d}`); }
    if (p === "7") { const past = new Date(now); past.setDate(now.getDate() - 6);
      const y2 = past.getFullYear(), m2 = pad(past.getMonth() + 1), d2 = pad(past.getDate());
      setDesde(`${y2}-${m2}-${d2}`); setHasta(`${y}-${m}-${d}`); }
    if (p === "mes") { const first = new Date(y, now.getMonth(), 1), last = new Date(y, now.getMonth() + 1, 0);
      setDesde(`${first.getFullYear()}-${pad(first.getMonth() + 1)}-${pad(first.getDate())}`);
      setHasta(`${last.getFullYear()}-${pad(last.getMonth() + 1)}-${pad(last.getDate())}`); }
    setPage(1);
  }
  function copyLink() {
    const params: Record<string, string> = {
      desde, hasta, estado, q: search, actor_tipo: actorTipo,
      actor_text: actorSel ? "" : actorInput, actor_id: actorSel?.id || "", actor_name: actorSel?.nombre || "",
      actor_tipo_api: actorSel?.tipo || "", dir: dir || "", page: String(page), pageSize: String(pageSize), view, auto: autoRefresh ? "1" : "",
    };
    if (sort) params.sort = sort;
    const qs = new URLSearchParams(params);
    navigator.clipboard.writeText(`${location.pathname}?${qs.toString()}`).then(() => alert("Enlace copiado"));
  }

  /* ——— Tabla (vista alternativa, con iconos/colores) ——— */
  const Table = useMemo(() => {
    if (view !== "table") return null;
    return (
      <div className={`${CARD} overflow-hidden`}>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-white/70">
              <tr className="text-left">
                <th className="px-4 py-3 w-36">
                  <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("reciente")}>
                    ⏱ Reciente {sort === "reciente" ? (dir === "asc" ? "▲" : "▼") : ""}
                  </button>
                </th>
                <th className="px-4 py-3 w-28">
                  <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("placa")}>
                    🚗 Placa {sort === "placa" ? (dir === "asc" ? "▲" : "▼") : ""}
                  </button>
                </th>
                <th className="px-4 py-3">🏭 Proveedor</th>
                <th className="px-4 py-3">🚚 Transportista</th>
                <th className="px-4 py-3">📥 Fase 1</th>
                <th className="px-4 py-3">📤 Fase 2</th>
                <th className="px-4 py-3 w-32">Estado</th>
                <th className="px-4 py-3 w-40">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, idx) => {
                const f1 = r.fase1_id, f2 = r.fase2_id;
                const vis = statusVisual(r.estado === "completo" ? "completo" : "pendiente");
                return (
                  <tr key={rowKey(r, idx)} className="border-t border-slate-200/70 dark:border-white/10">
                    <td className="px-4 py-3 whitespace-nowrap">{fmtDateTime(r.ultima_fecha_cierre)}</td>
                    <td className="px-4 py-3 font-medium">{r.placa || "SIN PLACA"}</td>
                    <td className="px-4 py-3 truncate max-w-[220px]">{r.proveedor?.nombre || r.proveedor?.documento || "—"}</td>
                    <td className="px-4 py-3 truncate max-w-[220px]">{r.transportista?.nombre || r.transportista?.documento || "—"}</td>
                    <td className="px-4 py-3 truncate max-w-[240px]">{(r.cuestionario_fase1 || "—") + " · " + fmtDateTime(r.fecha_entrada)}</td>
                    <td className="px-4 py-3 truncate max-w-[240px]">{(r.cuestionario_fase2 || "—") + " · " + fmtDateTime(r.fecha_salida)}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-2 rounded-lg px-2 py-1 text-xs font-medium border ${vis.badge}`}>
                        <span className={`h-2.5 w-2.5 rounded-full ${vis.dot}`} />
                        {vis.icon} {vis.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button className={BTN} disabled={!f1} onClick={() => f1 && router.push(`/historial/${f1}`)}>🔎 Fase 1</button>
                        <button className={BTN} disabled={!f2} onClick={() => f2 && router.push(`/historial/${f2}`)}>🔎 Fase 2</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }, [view, rows, sort, dir, router]);

  /* ——— Render ——— */
  const totalPages = Math.max(1, Math.ceil(count / pageSize));

  return (
    <main className="min-h-[calc(100vh-80px)] px-6 md:px-8 py-6 md:py-8">
      <div className="mx-auto max-w-[1150px]">
        {/* Header limpio */}
        <div className="mb-4">
          <div className="flex items-end justify-between gap-4 flex-wrap">
            <div>
              <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">Historial</h1>
              <p className="mt-1 text-sm text-slate-600 dark:text-white/70">
                ✅ Completos: <span className="font-medium">{countComp ?? "—"}</span> ·
                {" "}⏳ Pendientes: <span className="font-medium">{countPend ?? "—"}</span> ·
                {" "}Mostrando: <span className="font-medium">{count}</span>
              </p>
            </div>
            <div className="flex items-center gap-2">
              <select value={view} onChange={(e) => setView(e.target.value as ViewMode)} className={INPUT} title="Vista">
                <option value="cards">Tarjetas</option>
                <option value="table">Tabla</option>
              </select>
              <select
                value={`${sort}:${dir}`}
                onChange={(e) => {
                  const [s, d] = e.target.value.split(":") as [SortKey, SortDir];
                  setSort(s); setDir(d); setPage(1);
                }}
                className={INPUT}
                title="Orden"
              >
                <option value="reciente:desc">⏱ Reciente ↓</option>
                <option value="reciente:asc">⏱ Reciente ↑</option>
                <option value="placa:asc">🚗 Placa ↑</option>
                <option value="placa:desc">🚗 Placa ↓</option>
              </select>
            </div>
          </div>

          {/* Filtros */}
          <div className={`${CARD} mt-3 p-3 md:p-4`}>
            <div className="grid md:grid-cols-4 gap-3">
              <div className="md:col-span-2">
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2">🔎</span>
                  <input
                    type="search"
                    placeholder="Buscar por placa…"
                    value={search}
                    onChange={(e) => { setPage(1); setSearch(e.target.value); }}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); setPage(1); load(); } }}
                    className="w-full rounded-xl border px-9 py-3 outline-none focus:ring-2 focus:ring-skyBlue/30 tracking-wide"
                  />
                </div>
              </div>

              {/* Rango de fechas */}
              <div className="relative" ref={dateRef}>
                <button className={BTN} onClick={() => setDateOpen((v) => !v)} title="Rango de fechas">
                  🗓 Rango{desde || hasta ? `: ${fmtShortDate(desde)} – ${fmtShortDate(hasta)}` : ""}
                </button>
                {dateOpen && (
                  <div className={`${CARD} absolute z-20 mt-2 w-[320px] p-3`}>
                    <div className="flex items-center gap-2">
                      <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className={INPUT} />
                      <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className={INPUT} />
                    </div>
                    <div className="mt-3 flex items-center gap-2">
                      <button className={BTN} onClick={() => applyPreset("hoy")}>Hoy</button>
                      <button className={BTN} onClick={() => applyPreset("7")}>Últimos 7</button>
                      <button className={BTN} onClick={() => applyPreset("mes")}>Este mes</button>
                      <button className={BTN} onClick={() => { setDesde(""); setHasta(""); }}>Limpiar</button>
                    </div>
                  </div>
                )}
              </div>

              {/* Estado */}
              <select
                value={estado}
                onChange={(e) => { setEstado(e.target.value as Estado); setPage(1); }}
                className={INPUT}
              >
                <option value="completo">✅ Completos</option>
                <option value="pendiente">⏳ Pendientes</option>
                <option value="todos">📁 Todos</option>
              </select>
            </div>

            {/* Filtro de Actor + Acciones */}
            <div className="mt-3 flex items-center gap-2 flex-wrap">
              <div className="relative" ref={actorRef}>
                <div className="flex items-center gap-2">
                  <select
                    value={actorTipo}
                    onChange={(e) => { setActorTipo(e.target.value as ActorTipo); setActorSel(null); setActorInput(""); setActorOpts([]); }}
                    className={INPUT}
                  >
                    <option value="todos">👥 Actor (todos)</option>
                    <option value="proveedor">🏭 Proveedor</option>
                    <option value="transportista">🚚 Transportista</option>
                  </select>
                  <input
                    ref={actorInputRef}
                    type="search"
                    placeholder={actorTipo === "proveedor" ? "🏭 Proveedor (nombre/doc)…" : actorTipo === "transportista" ? "🚚 Transportista (nombre/doc)…" : "Selecciona tipo…"}
                    value={actorSel ? (actorSel.nombre || actorSel.documento || actorSel.id) : actorInput}
                    onChange={(e) => { setPage(1); setActorSel(null); setActorInput(e.target.value); }}
                    disabled={actorTipo === "todos"}
                    className={`w-[260px] ${INPUT} ${actorTipo === "todos" ? "opacity-60 cursor-not-allowed" : ""}`}
                  />
                  <button className={BTN} onClick={() => setActorPopoverOpen((v) => !v)}>🔎 Buscar</button>
                  <button className={BTN} onClick={clearActorSelection}>🧹 Limpiar</button>
                </div>

                {actorPopoverOpen && actorTipo !== "todos" && !actorSel && (
                  <div className={`${CARD} absolute z-20 mt-2 w-[360px] p-2`}>
                    {actorLoading && <div className="px-3 py-2 text-sm text-slate-500">Buscando…</div>}
                    {!actorLoading && actorOpts.length === 0 && actorInput.trim() && (
                      <div className="px-3 py-2 text-sm text-slate-500">Sin resultados</div>
                    )}
                    {actorOpts.length > 0 && (
                      <ul className="max-h-64 overflow-auto">
                        {actorOpts.map((opt) => (
                          <li
                            key={opt.id}
                            className="px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-white/5 cursor-pointer rounded-lg"
                            onClick={() => { setActorSel(opt); setActorPopoverOpen(false); }}
                          >
                            <div className="font-medium">{opt.nombre || opt.documento || opt.id}</div>
                            <div className="text-xs text-slate-500">{opt.tipo} {opt.documento ? `• ${opt.documento}` : ""}</div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>

              <div className="ml-auto flex items-center gap-2">
                <button
                  className="min-h-[40px] px-4 py-2 rounded-xl bg-skyBlue text-white font-medium shadow hover:opacity-90 transition"
                  onClick={() => { setPage(1); load(); }}
                >
                  Aplicar
                </button>

                <div className="relative" ref={menuRef}>
                  <button className={BTN} onClick={() => setMenuOpen((v) => !v)} aria-haspopup="menu" aria-expanded={menuOpen}>
                    ⋯
                  </button>
                  {menuOpen && (
                    <div className={`${CARD} absolute right-0 mt-2 w-56 p-2 z-20`}>
                      <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5" onClick={exportCSVAll} disabled={count === 0 || loading}>⤓ Exportar CSV</button>
                      <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5" onClick={copyLink}>🔗 Copiar enlace</button>
                      <label className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 cursor-pointer">
                        <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
                        🔄 Autorefresh 30s
                      </label>
                      <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 text-red-600" onClick={clearFilters}>🧹 Limpiar filtros</button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Lista / estados */}
        {loading ? (
          <ul className="grid gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <li key={i} className={`${CARD} p-5 md:p-6 animate-pulse`}>
                <div className="h-5 w-48 rounded bg-slate-200/70 dark:bg-white/10 mb-3" />
                <div className="h-4 w-80 rounded bg-slate-200/70 dark:bg-white/10 mb-2" />
                <div className="h-4 w-64 rounded bg-slate-200/70 dark:bg-white/10" />
              </li>
            ))}
          </ul>
        ) : error ? (
          <div className={`${CARD} p-6 md:p-8 text-center`}>
            <p className="text-red-600 mb-3">{error}</p>
            <button onClick={load} className="px-4 py-2 rounded-xl bg-skyBlue text-white font-medium shadow hover:opacity-90 transition">Reintentar</button>
          </div>
        ) : count === 0 ? (
          <div className={`${CARD} p-10 text-center`}>
            <div className="text-3xl mb-1">🗂️</div>
            <p className="text-base md:text-lg text-slate-700 dark:text-white/80">No hay registros para los filtros seleccionados.</p>
          </div>
        ) : view === "table" ? (
          Table
        ) : (
          <ul className="grid gap-4">
            {rows.map((r, idx) => {
              const f1 = r.fase1_id, f2 = r.fase2_id;
              const state = r.estado === "completo" ? "completo" : "pendiente";
              const vis = statusVisual(state);
              return (
                <li key={rowKey(r, idx)} className={`${CARD} p-0 overflow-hidden transition hover:shadow-md`}>
                  <div className="flex">
                    {/* Barra de acento por estado */}
                    <div className={`w-1.5 ${vis.bar}`} />
                    {/* Contenido */}
                    <div className="flex-1 p-5 md:p-6">
                      <div className="flex items-start justify-between gap-4">
                        {/* Columna izquierda */}
                        <div className="min-w-0">
                          {/* Línea principal: estado + última actualización */}
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={`inline-flex items-center gap-2 text-xs font-medium px-2 py-1 rounded-lg border ${vis.badge}`}>
                              <span className={`h-2.5 w-2.5 rounded-full ${vis.dot}`} />
                              {vis.icon} {vis.label}
                            </span>
                            <span className="text-xs text-slate-500 dark:text-white/60">⏱ {fmtDateTime(r.ultima_fecha_cierre)}</span>
                          </div>

                          {/* Placa */}
                          <div className="mt-1.5 flex items-center gap-2">
                            <span className="text-xl md:text-2xl">🚗</span>
                            <div className="text-lg md:text-xl font-semibold tracking-wide">{r.placa || "SIN PLACA"}</div>
                          </div>

                          {/* Fases */}
                          <div className="mt-3 grid gap-1.5 text-sm md:text-base">
                            <div className="flex items-center gap-2 border-l-2 pl-3 border-sky-400">
                              <span className="text-sky-700 dark:text-sky-300">📥 Fase 1</span>
                              <span className="opacity-70">· {(r.cuestionario_fase1 || "—")} · {fmtDateTime(r.fecha_entrada)}</span>
                            </div>
                            <div className="flex items-center gap-2 border-l-2 pl-3 border-indigo-400">
                              <span className="text-indigo-700 dark:text-indigo-300">📤 Fase 2</span>
                              <span className="opacity-70">· {(r.cuestionario_fase2 || "—")} · {fmtDateTime(r.fecha_salida)}</span>
                            </div>
                          </div>

                          {/* Actores */}
                          <div className="mt-2 text-sm text-slate-600 dark:text-white/70 flex items-center gap-4 flex-wrap">
                            {r.proveedor && (
                              <span className="inline-flex items-center gap-1.5">
                                <span className="text-sky-600 dark:text-sky-300">🏭</span>
                                <span className="font-medium">{r.proveedor.nombre || r.proveedor.documento || r.proveedor.id}</span>
                              </span>
                            )}
                            {r.transportista && (
                              <span className="inline-flex items-center gap-1.5">
                                <span className="text-indigo-600 dark:text-indigo-300">🚚</span>
                                <span className="font-medium">{r.transportista.nombre || r.transportista.documento || r.transportista.id}</span>
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Acciones */}
                        <div className="flex flex-col items-end gap-2 shrink-0">
                          <button className={BTN} disabled={!f1} onClick={() => f1 && router.push(`/historial/${f1}`)}>🔎 Ver Fase 1</button>
                          <button className={BTN} disabled={!f2} onClick={() => f2 && router.push(`/historial/${f2}`)}>🔎 Ver Fase 2</button>
                        </div>
                      </div>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        {/* Paginación + tamaño */}
        {count > 0 && (
          <div className="mt-5 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <button onClick={() => { window.scrollTo({ top: 0, behavior: "smooth" }); setPage((p) => Math.max(1, p - 1)); }} className={BTN} disabled={page === 1}>← Anterior</button>
              <span className="text-sm text-slate-600 dark:text-white/70">Página {page} de {totalPages}</span>
              <button onClick={() => { window.scrollTo({ top: 0, behavior: "smooth" }); setPage((p) => Math.min(totalPages, p + 1)); }} className={BTN} disabled={page >= totalPages}>Siguiente →</button>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm">Tamaño:</span>
              <select value={pageSize} onChange={(e) => { setPage(1); setPageSize(Number(e.target.value)); }} className={INPUT}>
                <option value={20}>20</option><option value={50}>50</option><option value={100}>100</option>
              </select>
              <div className="text-sm text-slate-600 dark:text-white/70 ml-2">{count} resultado{count === 1 ? "" : "s"}</div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

export default function HistorialPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
          <main className="mx-auto max-w-7xl px-6 py-8">
            <div className="animate-pulse">
              <div className="h-8 bg-gray-200 rounded mb-6"></div>
              <div className="h-32 bg-gray-200 rounded mb-6"></div>
              <div className="space-y-4">
                <div className="h-24 bg-gray-200 rounded"></div>
                <div className="h-24 bg-gray-200 rounded"></div>
                <div className="h-24 bg-gray-200 rounded"></div>
              </div>
            </div>
          </main>
        </div>
      }
    >
      <HistorialContent />
    </Suspense>
  );
}
