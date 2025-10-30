import type { HistorialFilters, SortDir, SortKey, ViewMode } from "../state";
import { INPUT } from "../ui";
type Props = {
  count: number;
  countComp: number | null;
  countPend: number | null;
  filters: HistorialFilters;
  updateFilters: (patch: Partial<HistorialFilters>, resetPage?: boolean) => void;
};

const SORT_OPTIONS: { label: string; value: `${SortKey}:${SortDir}` }[] = [
  { label: "Reciente (desc)", value: "reciente:desc" },
  { label: "Reciente (asc)", value: "reciente:asc" },
  { label: "Placa (asc)", value: "placa:asc" },
  { label: "Placa (desc)", value: "placa:desc" },
];

const VIEW_OPTIONS: { label: string; value: ViewMode }[] = [
  { label: "Tarjetas", value: "cards" },
  { label: "Tabla", value: "table" },
];

export function HistorialHeader({
  count: _count,
  countComp: _countComp,
  countPend: _countPend,
  filters,
  updateFilters,
}: Props) {
  return (
    <header className="space-y-5 md:space-y-4">
      <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 md:text-[28px] md:leading-8 dark:text-slate-50">
            Historial de formularios
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-600 dark:text-slate-300">
            Supervisa el avance de las inspecciones y controla la trazabilidad logistica con indicadores claros.
          </p>
        </div>

        <div className="w-full max-w-[280px] space-y-4">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-300">
              Vista
            </span>
            <div className="mt-1 inline-flex rounded-lg border border-slate-200 bg-white p-1 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              {VIEW_OPTIONS.map((option) => {
                const active = filters.view === option.value;
                return (
                  <button
                    key={option.value}
                    onClick={() => updateFilters({ view: option.value })}
                    className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
                      active
                        ? "bg-slate-900 text-white shadow-sm dark:bg-slate-100 dark:text-slate-900"
                        : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                    }`}
                    type="button"
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
          </div>

          <label className="block space-y-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-300">
              Ordenar por
            </span>
            <select
              id="orderSelect"
              value={`${filters.sort}:${filters.dir}`}
              onChange={(e) => {
                const [s, d] = e.target.value.split(":") as [SortKey, SortDir];
                updateFilters({ sort: s, dir: d }, true);
              }}
              className={`${INPUT} w-full`}
              title="Orden"
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
    </header>
  );
}
