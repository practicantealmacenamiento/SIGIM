import { useRouter } from "next/navigation";

import type { HistorialRow } from "@/lib/api.historial";

import type { ViewMode } from "../state";
import { BTN, CARD, INPUT } from "../ui";
import { fmtDateTime, rowKey, statusVisual, ICONS } from "../utils";

type ResultsViewProps = {
  rows: HistorialRow[];
  loading: boolean;
  error: string | null;
  count: number;
  view: ViewMode;
  page: number;
  pageSize: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
  onRetry: () => void;
};

export function ResultsView({
  rows,
  loading,
  error,
  count,
  view,
  page,
  pageSize,
  totalPages,
  onPageChange,
  onPageSizeChange,
  onRetry,
}: ResultsViewProps) {
  const router = useRouter();

  if (loading) {
    return (
      <ul className="grid gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <li key={i} className={`${CARD} animate-pulse p-5 md:p-6`}>
            <div className="mb-3 h-5 w-48 rounded bg-slate-200/70 dark:bg-white/10" />
            <div className="mb-2 h-4 w-80 rounded bg-slate-200/70 dark:bg-white/10" />
            <div className="h-4 w-64 rounded bg-slate-200/70 dark:bg-white/10" />
          </li>
        ))}
      </ul>
    );
  }

  if (error) {
    return (
      <div className={`${CARD} p-8 text-center`}>
        <p className="mb-4 text-sm font-medium text-red-600 dark:text-red-400">{error}</p>
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
        >
          {ICONS.refresh} Reintentar
        </button>
      </div>
    );
  }

  if (count === 0) {
    return (
      <div className={`${CARD} p-12 text-center`}>
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300">
          {ICONS.empty}
        </div>
        <p className="text-base font-medium text-slate-700 dark:text-slate-200">
          No hay registros para los filtros seleccionados.
        </p>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Ajusta los criterios e intenta nuevamente.</p>
      </div>
    );
  }

  const renderTable = () => (
    <div className={`${CARD} overflow-hidden`}>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
          <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-600 dark:bg-slate-900/70 dark:text-slate-300">
            <tr>
              <th className="px-4 py-3 text-left font-semibold">Estado</th>
              <th className="px-4 py-3 text-left font-semibold">Placa</th>
              <th className="px-4 py-3 text-left font-semibold">Fase 1</th>
              <th className="px-4 py-3 text-left font-semibold">Fase 2</th>
              <th className="px-4 py-3 text-left font-semibold">Proveedor</th>
              <th className="px-4 py-3 text-left font-semibold">Transportista</th>
              <th className="px-4 py-3 text-left font-semibold">Actualizado</th>
              <th className="px-4 py-3 text-left font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-600 dark:divide-slate-800 dark:text-slate-300">
            {rows.map((row, idx) => {
              const vis = statusVisual(row.estado === "completo" ? "completo" : "pendiente");
              return (
                <tr key={rowKey(row, idx)} className="transition hover:bg-slate-50 dark:hover:bg-slate-900/70">
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${vis.badge}`}
                    >
                      <span className={`h-2.5 w-2.5 rounded-full ${vis.dot}`} />
                      {vis.label}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-100">{row.placa || "SIN PLACA"}</td>
                  <td className="px-4 py-3">{row.fase1_id || "-"}</td>
                  <td className="px-4 py-3">{row.fase2_id || "-"}</td>
                  <td className="px-4 py-3">
                    {row.proveedor?.nombre || row.proveedor?.documento || "-"}
                  </td>
                  <td className="px-4 py-3">
                    {row.transportista?.nombre || row.transportista?.documento || "-"}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">{fmtDateTime(row.ultima_fecha_cierre)}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        className={`${BTN} px-3 py-1 text-xs`}
                        disabled={!row.fase1_id}
                        onClick={() => row.fase1_id && router.push(`/historial/${row.fase1_id}`)}
                        title="Ver detalle de Fase 1"
                      >
                        Ver Fase 1
                      </button>
                      <button
                        className={`${BTN} px-3 py-1 text-xs`}
                        disabled={!row.fase2_id}
                        onClick={() => row.fase2_id && router.push(`/historial/${row.fase2_id}`)}
                        title="Ver detalle de Fase 2"
                      >
                        Ver Fase 2
                      </button>
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

  const renderCards = () => (
    <ul className="grid gap-4">
      {rows.map((row, idx) => {
        const fase1Id = row.fase1_id;
        const fase2Id = row.fase2_id;
        const state = row.estado === "completo" ? "completo" : "pendiente";
        const vis = statusVisual(state);

        return (
          <li key={rowKey(row, idx)} className={`${CARD} overflow-hidden transition hover:shadow-md`}>
            <div className="flex">
              <div className={`w-1.5 ${vis.bar}`} aria-hidden />
              <div className="flex-1 bg-white p-5 dark:bg-slate-900">
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-semibold ${vis.badge}`}
                      >
                        <span className={`h-2.5 w-2.5 rounded-full ${vis.dot}`} />
                        {vis.label}
                      </span>
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        Actualizado {fmtDateTime(row.ultima_fecha_cierre)}
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                        {ICONS.truck}
                      </span>
                      <div>
                        <div className="truncate text-lg font-semibold text-slate-900 dark:text-slate-100">
                          {row.placa || "SIN PLACA"}
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          Regulador #{row.regulador_id || "N/D"}
                        </p>
                      </div>
                    </div>

                    <div className="grid gap-2 text-sm text-slate-600 dark:text-slate-300">
                      <div>
                        Fase 1:{" "}
                        <span className="font-medium text-slate-800 dark:text-slate-100">{fase1Id || "No enlazada"}</span>
                      </div>
                      <div>
                        Fase 2:{" "}
                        <span className="font-medium text-slate-800 dark:text-slate-100">{fase2Id || "No enlazada"}</span>
                      </div>
                      {(row.proveedor || row.transportista) && (
                        <div className="flex flex-wrap gap-3 text-sm">
                          {row.proveedor && (
                            <span className="inline-flex items-center gap-1.5">
                              <span className="text-slate-500 dark:text-slate-300" aria-hidden>
                                {ICONS.provider}
                              </span>
                              <span className="font-medium text-slate-800 dark:text-slate-100">
                                {row.proveedor.nombre || row.proveedor.documento || row.proveedor.id}
                              </span>
                            </span>
                          )}
                          {row.transportista && (
                            <span className="inline-flex items-center gap-1.5">
                              <span className="text-slate-500 dark:text-slate-300" aria-hidden>
                                {ICONS.transport}
                              </span>
                              <span className="font-medium text-slate-800 dark:text-slate-100">
                                {row.transportista.nombre || row.transportista.documento || row.transportista.id}
                              </span>
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex shrink-0 flex-col items-stretch gap-2">
                    <button
                      className={`${BTN} justify-center`}
                      disabled={!fase1Id}
                      onClick={() => fase1Id && router.push(`/historial/${fase1Id}`)}
                      title="Ver detalle de Fase 1"
                    >
                      Ver Fase 1
                    </button>
                    <button
                      className={`${BTN} justify-center`}
                      disabled={!fase2Id}
                      onClick={() => fase2Id && router.push(`/historial/${fase2Id}`)}
                      title="Ver detalle de Fase 2"
                    >
                      Ver Fase 2
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );

  const content = view === "table" ? renderTable() : renderCards();

  return (
    <>
      {content}

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              window.scrollTo({ top: 0, behavior: "smooth" });
              onPageChange(Math.max(1, page - 1));
            }}
            className={`${BTN} gap-1`}
            disabled={page === 1}
            title="Pagina anterior"
          >
            {ICONS.chevronLeft} Anterior
          </button>
          <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
            Pagina {page} de {totalPages}
          </span>
          <button
            onClick={() => {
              window.scrollTo({ top: 0, behavior: "smooth" });
              onPageChange(Math.min(totalPages, page + 1));
            }}
            className={`${BTN} gap-1`}
            disabled={page >= totalPages}
            title="Pagina siguiente"
          >
            Siguiente {ICONS.chevronRight}
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <label className="text-sm" htmlFor="pageSizeSel">
            Tamano
          </label>
          <select
            id="pageSizeSel"
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className={`${INPUT} h-10 w-24`}
          >
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
          <span className="ml-2 text-sm text-slate-500 dark:text-slate-400">
            {count} resultado{count === 1 ? "" : "s"}
          </span>
        </div>
      </div>
    </>
  );
}
