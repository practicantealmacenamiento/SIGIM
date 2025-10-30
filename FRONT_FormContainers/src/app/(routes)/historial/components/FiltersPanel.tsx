import { useEffect, useMemo, useRef, useState } from "react";

import { listActors } from "@/lib/api.admin";

import type { ActorOption, ActorTipo, Estado, HistorialFilters } from "../state";
import { CARD, BTN, INPUT } from "../ui";
import { fmtShortDate, ICONS } from "../utils";

type FiltersPanelProps = {
  filters: HistorialFilters;
  updateFilters: (patch: Partial<HistorialFilters>, resetPage?: boolean) => void;
  clearFilters: () => void;
  copyLink: () => void;
  exportCSVAll: () => Promise<void>;
  triggerReload: () => void;
  loading: boolean;
  count: number;
};

const STATE_SEGMENTS: { label: string; value: Estado }[] = [
  { label: "Completos", value: "completo" },
  { label: "Pendientes", value: "pendiente" },
  { label: "Todos", value: "todos" },
];

const DATE_PRESETS = [
  { key: "hoy" as const, label: "Hoy" },
  { key: "7" as const, label: "Ultimos 7 dias" },
  { key: "mes" as const, label: "Este mes" },
];

const ACTOR_LABELS: Record<ActorTipo, string> = {
  todos: "Todos",
  proveedor: "Proveedor",
  transportista: "Transportista",
};

export function FiltersPanel({
  filters,
  updateFilters,
  clearFilters,
  copyLink,
  exportCSVAll,
  triggerReload,
  loading,
  count,
}: FiltersPanelProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [dateOpen, setDateOpen] = useState(false);
  const [actorPopoverOpen, setActorPopoverOpen] = useState(false);
  const [actorOpts, setActorOpts] = useState<ActorOption[]>([]);
  const [actorLoading, setActorLoading] = useState(false);
  const [searchDraft, setSearchDraft] = useState(filters.search);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const actorInputRef = useRef<HTMLInputElement>(null);
  const actorBoxRef = useRef<HTMLDivElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const dateBoxRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => setSearchDraft(filters.search), [filters.search]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      const target = e.target as Node;
      if (menuRef.current && !menuRef.current.contains(target)) setMenuOpen(false);
      if (dateBoxRef.current && !dateBoxRef.current.contains(target)) setDateOpen(false);
      if (actorBoxRef.current && !actorBoxRef.current.contains(target)) setActorPopoverOpen(false);
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setMenuOpen(false);
        setDateOpen(false);
        setActorPopoverOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onEsc);
    };
  }, []);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    if (filters.actorTipo === "todos" || !filters.actorInput.trim() || filters.actorSel) {
      setActorOpts([]);
      return () => controller.abort();
    }

    setActorLoading(true);
    const timer = setTimeout(async () => {
      try {
        const tipoParam =
          filters.actorTipo === "proveedor"
            ? "PROVEEDOR"
            : filters.actorTipo === "transportista"
            ? "TRANSPORTISTA"
            : "";
        const list = await listActors({ tipo: tipoParam, search: filters.actorInput.trim() });
        if (!active) return;
        setActorOpts(
          (list || []).map((a: any) => ({
            id: a.id,
            nombre: a.nombre,
            documento: a.documento,
            tipo: a.tipo,
          }))
        );
      } finally {
        if (active) setActorLoading(false);
      }
    }, 250);

    return () => {
      active = false;
      clearTimeout(timer);
      controller.abort();
    };
  }, [filters.actorInput, filters.actorTipo, filters.actorSel]);

  const actorPlaceholder = useMemo(() => {
    if (filters.actorTipo === "proveedor") return "Buscar proveedor (nombre o documento)";
    if (filters.actorTipo === "transportista") return "Buscar transportista (nombre o documento)";
    return "Selecciona un tipo de actor";
  }, [filters.actorTipo]);

  const clearActorSelection = () => {
    updateFilters({ actorSel: null, actorInput: "" }, true);
    setActorOpts([]);
    setActorPopoverOpen(false);
    actorInputRef.current?.focus();
  };

  const applyPreset = (preset: "hoy" | "7" | "mes") => {
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, "0");
    const year = now.getFullYear();
    const month = pad(now.getMonth() + 1);
    const day = pad(now.getDate());
    if (preset === "hoy") {
      const date = `${year}-${month}-${day}`;
      updateFilters({ desde: date, hasta: date }, true);
      return;
    }
    if (preset === "7") {
      const past = new Date(now);
      past.setDate(now.getDate() - 6);
      const start = `${past.getFullYear()}-${pad(past.getMonth() + 1)}-${pad(past.getDate())}`;
      updateFilters({ desde: start, hasta: `${year}-${month}-${day}` }, true);
      return;
    }
    const first = new Date(year, now.getMonth(), 1);
    const last = new Date(year, now.getMonth() + 1, 0);
    updateFilters(
      {
        desde: `${first.getFullYear()}-${pad(first.getMonth() + 1)}-${pad(first.getDate())}`,
        hasta: `${last.getFullYear()}-${pad(last.getMonth() + 1)}-${pad(last.getDate())}`,
      },
      true
    );
  };

  const commitSearch = (value: string) => {
    const trimmed = value.trim();
    const changed = trimmed !== filters.search;
    updateFilters({ search: trimmed }, true);
    if (!changed) {
      triggerReload();
    }
  };

  const onActorPick = (opt: ActorOption) => {
    updateFilters(
      {
        actorSel: opt,
        actorInput: opt.nombre || opt.documento || opt.id,
      },
      true
    );
    setActorOpts([]);
    setActorPopoverOpen(false);
  };

  const activeFiltersCount = useMemo(() => {
    let total = 0;
    if (filters.search.trim()) total += 1;
    if (filters.desde || filters.hasta) total += 1;
    if (filters.estado !== "completo") total += 1;
    if (filters.actorTipo !== "todos" || filters.actorSel) total += 1;
    if (filters.actorInput.trim() && !filters.actorSel) total += 1;
    if (filters.autoRefresh) total += 1;
    if (!(filters.sort === "reciente" && filters.dir === "desc")) total += 1;
    if (filters.view !== "cards") total += 1;
    if (filters.pageSize !== 20) total += 1;
    return total;
  }, [filters]);

  const hasRange = Boolean(filters.desde || filters.hasta);
  const advancedLabel = advancedOpen ? "Ocultar filtros" : "Mas filtros";

  return (
    <section className={`${CARD} mt-4 space-y-4 p-4 md:p-5`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-50">Panel de filtros</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Define un rango de fechas y despliega los filtros avanzados cuando sean necesarios.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {activeFiltersCount > 0 && (
            <span className="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-medium text-sky-700 dark:border-sky-900/40 dark:bg-sky-900/40 dark:text-sky-200">
              {ICONS.filter} {activeFiltersCount} activo{activeFiltersCount === 1 ? "" : "s"}
            </span>
          )}
          <button
            onClick={clearFilters}
            className="text-xs font-medium text-slate-500 transition hover:text-slate-700 dark:text-slate-300 dark:hover:text-white"
            type="button"
          >
            {ICONS.clear} Limpiar todo
          </button>
          <button
            onClick={() => setAdvancedOpen((v) => !v)}
            className={`${BTN} gap-1 py-1.5`}
            type="button"
            aria-expanded={advancedOpen}
          >
            {advancedOpen ? ICONS.minus : ICONS.plus} {advancedLabel}
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="relative flex flex-wrap items-center gap-2" ref={dateBoxRef}>
          {DATE_PRESETS.map((preset) => (
            <button
              key={preset.key}
              type="button"
              onClick={() => applyPreset(preset.key)}
              className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 transition hover:border-slate-300 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:border-slate-600 dark:hover:bg-slate-800"
            >
              {preset.label}
            </button>
          ))}
          <button
            className={`${BTN} gap-1 py-1.5`}
            onClick={() => setDateOpen((v) => !v)}
            title="Rango de fechas"
            aria-haspopup="dialog"
            aria-expanded={dateOpen}
            aria-controls="date-popover"
            type="button"
          >
            {ICONS.calendar}{" "}
            {hasRange ? `${fmtShortDate(filters.desde)} - ${fmtShortDate(filters.hasta)}` : "Seleccionar fechas"}
          </button>
          {dateOpen && (
            <div
              id="date-popover"
              className="absolute z-40 mt-2 w-[320px] rounded-xl border border-slate-200 bg-white p-4 shadow-lg dark:border-slate-700 dark:bg-slate-900"
            >
              <div className="flex items-center gap-2">
                <label className="sr-only" htmlFor="desde">
                  Desde
                </label>
                <input
                  id="desde"
                  type="date"
                  value={filters.desde}
                  onChange={(e) => updateFilters({ desde: e.target.value }, true)}
                  className={`${INPUT} w-full`}
                />
                <label className="sr-only" htmlFor="hasta">
                  Hasta
                </label>
                <input
                  id="hasta"
                  type="date"
                  value={filters.hasta}
                  onChange={(e) => updateFilters({ hasta: e.target.value }, true)}
                  className={`${INPUT} w-full`}
                />
              </div>
            </div>
          )}
          {hasRange && (
            <button
              type="button"
              onClick={() => updateFilters({ desde: "", hasta: "" }, true)}
              className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              {ICONS.clear} Limpiar rango
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-1.5 text-sm font-semibold text-white transition hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
            onClick={() => {
              updateFilters({ page: 1 });
              triggerReload();
            }}
            title="Aplicar filtros"
            type="button"
          >
            Aplicar filtros
          </button>

          <div className="relative" ref={menuRef}>
            <button
              className={`${BTN} flex items-center gap-2 py-1.5`}
              onClick={() => setMenuOpen((v) => !v)}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              aria-controls="more-menu"
              title="Acciones adicionales"
              type="button"
            >
              {ICONS.menu} Acciones
            </button>
            {menuOpen && (
              <div
                id="more-menu"
                className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-200 bg-white p-2 shadow-lg dark:border-slate-700 dark:bg-slate-900"
              >
                <button
                  className="w-full rounded-lg px-3 py-1.5 text-left text-sm transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-slate-800"
                  onClick={exportCSVAll}
                  disabled={count === 0 || loading}
                  type="button"
                >
                  {ICONS.download} Exportar CSV
                </button>
                <button
                  className="w-full rounded-lg px-3 py-1.5 text-left text-sm transition hover:bg-slate-100 dark:hover:bg-slate-800"
                  onClick={copyLink}
                  type="button"
                >
                  {ICONS.link} Copiar enlace
                </button>
                <label className="flex cursor-pointer items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition hover:bg-slate-100 dark:hover:bg-slate-800">
                  <input
                    type="checkbox"
                    checked={filters.autoRefresh}
                    onChange={(e) => updateFilters({ autoRefresh: e.target.checked })}
                    className="h-4 w-4 accent-sky-600"
                  />
                  {ICONS.refresh} Autorefresh 30s
                </label>
                <button
                  className="w-full rounded-lg px-3 py-1.5 text-left text-sm font-medium text-red-600 transition hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                  onClick={() => {
                    clearFilters();
                    setActorPopoverOpen(false);
                    setMenuOpen(false);
                  }}
                  type="button"
                >
                  {ICONS.clear} Limpiar filtros
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {advancedOpen && (
        <div className="grid gap-4 md:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
          <div className="space-y-4">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                commitSearch(searchDraft);
              }}
              className="space-y-2"
            >
              <div className="relative">
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2">{ICONS.search}</span>
                <input
                  type="search"
                  placeholder="Buscar por placa, referencia o ID de fase..."
                  value={searchDraft}
                  onChange={(e) => setSearchDraft(e.target.value)}
                  className={`${INPUT} w-full pl-10 py-2.5`}
                  aria-label="Buscar por placa"
                />
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="submit"
                  className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-sky-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500"
                  title="Aplicar busqueda"
                >
                  {ICONS.search} Buscar
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSearchDraft("");
                    commitSearch("");
                  }}
                  className={`${BTN} py-1.5`}
                  title="Limpiar busqueda"
                >
                  {ICONS.clear} Reiniciar
                </button>
              </div>
            </form>

            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-300">
                Estado
              </span>
              <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 text-xs font-semibold shadow-sm dark:border-slate-700 dark:bg-slate-900">
                {STATE_SEGMENTS.map((segment) => {
                  const active = filters.estado === segment.value;
                  return (
                    <button
                      key={segment.value}
                      onClick={() => updateFilters({ estado: segment.value }, true)}
                      className={`rounded-md px-4 py-1.5 transition ${
                        active
                          ? "bg-slate-900 text-white shadow-sm dark:bg-slate-100 dark:text-slate-900"
                          : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                      }`}
                      type="button"
                    >
                      {segment.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="relative space-y-3" ref={actorBoxRef}>
            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-300">
                Tipo de actor
              </span>
              <div className="inline-flex rounded-full border border-slate-200 bg-white p-1 text-xs font-medium shadow-sm dark:border-slate-700 dark:bg-slate-900">
                {(["todos", "proveedor", "transportista"] as ActorTipo[]).map((tipo) => {
                  const active = filters.actorTipo === tipo;
                  return (
                    <button
                      key={tipo}
                      onClick={() => updateFilters({ actorTipo: tipo, actorSel: null, actorInput: "" }, true)}
                      className={`rounded-full px-3 py-1 transition ${
                        active
                          ? "bg-sky-600 text-white shadow-sm"
                          : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                      }`}
                      type="button"
                    >
                      {ACTOR_LABELS[tipo]}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-300">
                Buscar actor
              </span>
              <input
                ref={actorInputRef}
                type="search"
                placeholder={actorPlaceholder}
                value={
                  filters.actorSel
                    ? filters.actorSel.nombre || filters.actorSel.documento || filters.actorSel.id
                    : filters.actorInput
                }
                onChange={(e) => {
                  updateFilters(
                    {
                      actorSel: null,
                      actorInput: e.target.value,
                    },
                    true
                  );
                  setActorOpts([]);
                  setActorPopoverOpen(true);
                }}
                disabled={filters.actorTipo === "todos"}
                className={`${INPUT} w-full ${filters.actorTipo === "todos" ? "cursor-not-allowed opacity-60" : ""}`}
                aria-label="Buscar actor"
              />
              {filters.actorSel && (
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  Seleccionado:{" "}
                  <span className="font-medium">
                    {filters.actorSel.nombre || filters.actorSel.documento || filters.actorSel.id}
                  </span>
                </div>
              )}
              <div className="flex items-center gap-2">
                <button
                  className={`${BTN} flex items-center gap-2 py-1.5`}
                  onClick={() => setActorPopoverOpen((v) => !v)}
                  aria-haspopup="listbox"
                  aria-expanded={actorPopoverOpen}
                  aria-controls="actor-popover"
                  title="Buscar actor"
                  disabled={filters.actorTipo === "todos"}
                  type="button"
                >
                  {ICONS.search} Buscar
                </button>
                <button
                  className={`${BTN} flex items-center gap-2 py-1.5`}
                  onClick={clearActorSelection}
                  title="Limpiar actor"
                  type="button"
                >
                  {ICONS.clear} Limpiar
                </button>
              </div>

              {actorPopoverOpen && filters.actorTipo !== "todos" && (
                <div
                  id="actor-popover"
                  className="absolute z-40 mt-2 w-[320px] max-h-[260px] overflow-auto rounded-xl border border-slate-200 bg-white p-2 shadow-lg dark:border-slate-700 dark:bg-slate-900"
                >
                  {actorLoading && <div className="px-3 py-2 text-sm text-slate-500">Buscando...</div>}
                  {!actorLoading && actorOpts.length === 0 && filters.actorInput.trim() && (
                    <div className="px-3 py-2 text-sm text-slate-500">Sin resultados</div>
                  )}
                  {actorOpts.length > 0 &&
                    actorOpts.map((opt) => (
                      <button
                        type="button"
                        key={opt.id}
                        onClick={() => onActorPick(opt)}
                        className="w-full rounded-lg px-3 py-1.5 text-left text-sm transition hover:bg-slate-100 dark:hover:bg-slate-800"
                      >
                        <div className="font-medium">{opt.nombre || opt.documento || opt.id}</div>
                        <div className="text-xs text-slate-500">
                          {opt.tipo}
                          {opt.documento ? ` - ${opt.documento}` : ""}
                        </div>
                      </button>
                    ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
