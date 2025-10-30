"use client";

import { useCallback, useEffect, useReducer, useRef, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import {
  fetchHistorialEnriched,
  exportHistorialCSV,
  type HistorialRow,
} from "@/lib/api.historial";

import { normalizeRows } from "./utils";
import { SHELL_PAGE, WRAPPER, SECTION_GAP } from "./ui";
import {
  DEFAULT_FILTERS,
  createFiltersFromParams,
  filtersEqual,
  filtersReducer,
  type HistorialFilters,
} from "./state";
import { HistorialHeader } from "./components/HistorialHeader";
import { FiltersPanel } from "./components/FiltersPanel";
import { ResultsView } from "./components/ResultsView";

function setQuery(router: ReturnType<typeof useRouter>, paramsString: string, kv: Record<string, any>) {
  const base = paramsString || "";
  const searchParams = new URLSearchParams(base);
  Object.entries(kv).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "" || value === "null") searchParams.delete(key);
    else searchParams.set(key, String(value));
  });
  const next = searchParams.toString();
  if (next === base) return;
  router.replace(`?${next}`);
}

function HistorialContent() {
  const router = useRouter();
  const urlParams = useSearchParams();
  const urlParamsStr = urlParams.toString();

  const [filters, dispatch] = useReducer(filtersReducer, urlParamsStr, createFiltersFromParams);
  const lastFiltersRef = useRef(filters);
  useEffect(() => {
    lastFiltersRef.current = filters;
  }, [filters]);
  useEffect(() => {
    const parsed = createFiltersFromParams(urlParamsStr);
    if (!filtersEqual(lastFiltersRef.current, parsed)) {
      dispatch({ type: "hydrate", payload: parsed });
    }
  }, [urlParamsStr]);

  const {
    desde,
    hasta,
    estado,
    search,
    actorTipo,
    actorInput,
    actorSel,
    sort,
    dir,
    page,
    pageSize,
    view,
    autoRefresh,
  } = filters;

  const updateFilters = useCallback(
    (patch: Partial<HistorialFilters>, resetPage = false) => {
      dispatch({ type: "merge", patch, resetPage });
    },
    []
  );
  const setPage = useCallback((next: number) => {
    dispatch({ type: "setPage", page: next });
  }, []);

  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState<HistorialRow[]>([]);
  const [count, setCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [countComp, setCountComp] = useState<number | null>(null);
  const [countPend, setCountPend] = useState<number | null>(null);

  const [reloadKey, setReloadKey] = useState(0);
  const triggerReload = useCallback(() => setReloadKey((k) => k + 1), []);

  const loadSeq = useRef(0);

  const load = useCallback(async () => {
    const mySeq = ++loadSeq.current;
    try {
      setError(null);
      setLoading(true);

      setQuery(router, urlParamsStr, {
        desde,
        hasta,
        estado,
        q: search,
        actor_tipo: actorTipo,
        actor_text: actorSel ? "" : actorInput,
        actor_id: actorSel?.id,
        actor_name: actorSel?.nombre,
        actor_tipo_api: actorSel?.tipo,
        sort,
        dir,
        page,
        pageSize,
        view,
        auto: autoRefresh ? "1" : "",
      });

      const { results, count: total } = await fetchHistorialEnriched(
        { fecha_desde: desde || undefined, fecha_hasta: hasta || undefined, solo_completados: estado === "completo" },
        {
          search,
          estado,
          sort,
          dir,
          page,
          pageSize,
          actor_tipo: actorTipo === "todos" ? "todos" : actorTipo,
          actor_text: actorSel ? "" : actorInput,
          actor_id_exact: actorSel?.id ?? null,
        }
      );

      if (mySeq !== loadSeq.current) return;

      setRows(normalizeRows(results));
      setCount(total);

      const [completed, pending] = await Promise.all([
        fetchHistorialEnriched(
          { fecha_desde: desde || undefined, fecha_hasta: hasta || undefined, solo_completados: true },
          {
            search,
            estado: "completo",
            sort: "reciente",
            dir: "desc",
            page: 1,
            pageSize: 1,
            actor_tipo: actorTipo === "todos" ? "todos" : actorTipo,
            actor_text: actorSel ? "" : actorInput,
            actor_id_exact: actorSel?.id ?? null,
          }
        ),
        fetchHistorialEnriched(
          { fecha_desde: desde || undefined, fecha_hasta: hasta || undefined, solo_completados: false },
          {
            search,
            estado: "pendiente",
            sort: "reciente",
            dir: "desc",
            page: 1,
            pageSize: 1,
            actor_tipo: actorTipo === "todos" ? "todos" : actorTipo,
            actor_text: actorSel ? "" : actorInput,
            actor_id_exact: actorSel?.id ?? null,
          }
        ),
      ]);

      if (mySeq !== loadSeq.current) return;
      setCountComp(completed.count);
      setCountPend(pending.count);
    } catch (e: any) {
      if (mySeq !== loadSeq.current) return;
      setError(e?.message || "Error cargando historial");
    } finally {
      if (mySeq !== loadSeq.current) return;
      setLoading(false);
    }
  }, [
    actorInput,
    actorSel,
    actorTipo,
    autoRefresh,
    desde,
    dir,
    estado,
    hasta,
    page,
    pageSize,
    router,
    search,
    sort,
    urlParamsStr,
    view,
  ]);

  useEffect(() => {
    load();
  }, [load, reloadKey]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => {
      load();
    }, 30000);
    return () => clearInterval(id);
  }, [autoRefresh, load]);

  const clearFilters = useCallback(() => {
    const changed = !filtersEqual(filters, DEFAULT_FILTERS);
    dispatch({ type: "reset" });
    if (!changed) {
      triggerReload();
    }
  }, [filters, triggerReload]);

  const exportCSVAll = useCallback(async () => {
    try {
      const { results: all } = await fetchHistorialEnriched(
        { fecha_desde: desde || undefined, fecha_hasta: hasta || undefined, solo_completados: estado === "completo" },
        {
          search,
          estado,
          sort,
          dir,
          page: 1,
          pageSize: Math.max(count, 1),
          actor_tipo: actorTipo === "todos" ? "todos" : actorTipo,
          actor_text: actorSel ? "" : actorInput,
          actor_id_exact: actorSel?.id ?? null,
        }
      );
      exportHistorialCSV(normalizeRows(all), "historial.csv");
    } catch (e: any) {
      alert(e?.message || "No se pudo exportar");
    }
  }, [actorInput, actorSel, actorTipo, count, desde, dir, estado, hasta, search, sort]);

  const copyLink = useCallback(() => {
    const params: Record<string, string> = {
      desde,
      hasta,
      estado,
      q: search,
      actor_tipo: actorTipo,
      actor_text: actorSel ? "" : actorInput,
      actor_id: actorSel?.id || "",
      actor_name: actorSel?.nombre || "",
      actor_tipo_api: actorSel?.tipo || "",
      dir: dir || "",
      page: String(page),
      pageSize: String(pageSize),
      view,
      auto: autoRefresh ? "1" : "",
    };
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value) query.set(key, value);
    });
    const url = `${window.location.origin}${window.location.pathname}?${query.toString()}`;
    navigator.clipboard.writeText(url).catch(() => {});
  }, [
    actorInput,
    actorSel,
    actorTipo,
    autoRefresh,
    desde,
    dir,
    estado,
    hasta,
    page,
    pageSize,
    search,
    view,
  ]);

  const totalPages = Math.max(1, Math.ceil(count / pageSize));

  return (
    <main className={SHELL_PAGE}>
      <div className={`${WRAPPER} ${SECTION_GAP}`}>
        <HistorialHeader
          count={count}
          countComp={countComp}
          countPend={countPend}
          filters={filters}
          updateFilters={updateFilters}
        />

        <FiltersPanel
          filters={filters}
          updateFilters={updateFilters}
          clearFilters={clearFilters}
          copyLink={copyLink}
          exportCSVAll={exportCSVAll}
          triggerReload={triggerReload}
          loading={loading}
          count={count}
        />

        <ResultsView
          rows={rows}
          loading={loading}
          error={error}
          count={count}
          view={view}
          page={page}
          pageSize={pageSize}
          totalPages={totalPages}
          onPageChange={(next) => setPage(Math.max(1, next))}
          onPageSizeChange={(size) => updateFilters({ pageSize: size }, true)}
          onRetry={load}
        />
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
