"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  listarFase1Finalizados,
  buscarFase2PorPlaca,
  crearSubmissionFase2,
  type SubmissionRow,
} from "@/lib/api.panel";

const CARD =
  "rounded-2xl border border-slate-200/70 dark:border-white/10 bg-white dark:bg-slate-900 shadow-sm";

const INPUT =
  "w-full md:w-[320px] px-4 py-2.5 rounded-xl border border-slate-300 dark:border-white/10 bg-white dark:bg-slate-900 text-sm outline-none focus:ring-2 focus:ring-sky-300/40 dark:focus:ring-sky-600/40";

const BTN =
  "inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-300 dark:border-white/15 hover:bg-slate-50 dark:hover:bg-white/5 transition disabled:opacity-50 disabled:cursor-not-allowed";

const BTN_PRIMARY =
  "inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-skyBlue text-white font-medium shadow hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed";

const Q_FASE2 = process.env.NEXT_PUBLIC_Q_FASE2_ID!;

/* ---------- utils ---------- */
function useDebounced<T>(value: T, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

function formatDateTime(value?: string | null) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("es-CO", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return new Date(value).toLocaleString();
  }
}

function Badge({
  children,
  tone = "slate",
}: {
  children: React.ReactNode;
  tone?: "amber" | "emerald" | "indigo" | "slate";
}) {
  const tones: Record<string, string> = {
    amber:
      "bg-amber-100 dark:bg-amber-400/10 text-amber-800 dark:text-amber-300 border border-amber-200/70 dark:border-amber-300/20",
    emerald:
      "bg-emerald-100 dark:bg-emerald-400/10 text-emerald-800 dark:text-emerald-300 border border-emerald-200/70 dark:border-emerald-300/20",
    indigo:
      "bg-indigo-100 dark:bg-indigo-400/10 text-indigo-800 dark:text-indigo-300 border border-indigo-200/70 dark:border-indigo-300/20",
    slate:
      "bg-slate-100 dark:bg-white/5 text-slate-800 dark:text-white/80 border border-slate-200/70 dark:border-white/10",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-sm font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

function Spinner({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
      <path className="opacity-75" d="M4 12a8 8 0 018-8v8z" fill="currentColor" />
    </svg>
  );
}

export default function PanelPage() {
  const router = useRouter();

  /* ---------- estado ---------- */
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounced(search, 300);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<SubmissionRow[]>([]);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);

  const [loadingFase2, setLoadingFase2] = useState<string | null>(null); // id para loading individual
  const [modal, setModal] = useState<{ row: SubmissionRow; fase2Id?: string } | null>(null);

  const modalRef = useRef<HTMLDivElement | null>(null);

  /* ---------- carga principal ---------- */
  const load = async () => {
    try {
      setError(null);
      setLoading(true);
      const res = await listarFase1Finalizados({ search: debouncedSearch, page });
      const list = Array.isArray(res) ? res : res.results ?? [];
      setRows(list);
      setCount(Array.isArray(res) ? list.length : res.count ?? list.length);
    } catch (e: any) {
      setError(e.message || "Error al cargar submissions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch, page]);

  /* ---------- fase 2 ---------- */
  const handleFase2 = async (row: SubmissionRow) => {
    const placa = (row.placa_vehiculo || "").trim().toUpperCase();
    if (!placa) return alert("Submission sin placa");
    setLoadingFase2(row.id);
    try {
      const existente = await buscarFase2PorPlaca(placa);
      if (existente?.id) {
        setModal({ row, fase2Id: existente.id });
      } else {
        const sub = await crearSubmissionFase2({
          questionnaire_id_fase2: Q_FASE2,
          placa_vehiculo: placa,
          regulador_id: row.regulador_id ?? row.id,
        });
        router.push(`formulario?questionnaire_id=${Q_FASE2}&submission_id=${sub.id}`);
      }
    } catch (e: any) {
      alert(e.message || "Error al crear Fase 2");
    } finally {
      setLoadingFase2(null);
    }
  };

  /* ---------- accesibilidad modal ---------- */
  useEffect(() => {
    if (!modal) return;
    const prev = document.activeElement as HTMLElement | null;
    const el = modalRef.current?.querySelector<HTMLElement>("[data-autofocus]");
    el?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setModal(null);
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      prev?.focus();
    };
  }, [modal]);

  /* ---------- memo ---------- */
  const totalPages = useMemo(() => Math.max(1, Math.ceil(count / 20)), [count]);

  /* ---------- UI ---------- */
  return (
    <main className="min-h-screen px-6 md:px-8 py-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <header className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Panel de control</h1>
            <p className="text-sm text-slate-600 dark:text-white/70 mt-1">
              Gestiona las entradas <strong>Fase 1 finalizadas</strong> y crea/continúa la <strong>Fase 2</strong>.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <label className="sr-only" htmlFor="searchPlate">Buscar por placa</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 opacity-60">🔎</span>
              <input
                id="searchPlate"
                type="search"
                placeholder="Buscar por placa (Ej: ABC123)"
                className={`${INPUT} pl-9`}
                value={search}
                onChange={(e) => {
                  const val = e.target.value.toUpperCase();
                  setSearch(val);
                  setPage(1);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    load();
                  }
                }}
                aria-label="Buscar por placa"
              />
            </div>
          </div>
        </header>

        {/* Estados */}
        {loading ? (
          <div aria-live="polite" className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className={`${CARD} p-5 md:p-6 animate-pulse`}>
                <div className="h-5 w-52 rounded bg-slate-200/70 dark:bg-white/10 mb-2" />
                <div className="h-4 w-72 rounded bg-slate-200/70 dark:bg-white/10" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className={`${CARD} p-6 text-center border-amber-300/70 dark:border-amber-300/30`}>
            <p className="text-amber-700 dark:text-amber-300 mb-3">{error}</p>
            <button className={BTN_PRIMARY} onClick={load}>Reintentar</button>
          </div>
        ) : rows.length === 0 ? (
          <div className={`${CARD} p-8 text-center text-slate-600 dark:text-white/70`}>
            No hay resultados para los filtros actuales.
          </div>
        ) : (
          <>
            <div className="mb-3 text-sm text-slate-600 dark:text-white/70">
              Mostrando <span className="font-medium">{rows.length}</span> de{" "}
              <span className="font-medium">{count}</span> resultados.
            </div>
            <ul className="grid gap-4">
              {rows.map((row) => {
                const placa = row.placa_vehiculo?.toUpperCase() || "SIN PLACA";
                const isWorking = loadingFase2 === row.id;
                return (
                  <li key={row.id} className={`${CARD} p-5 md:p-6`}>
                    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                      <div className="space-y-2 min-w-0">
                        <div className="flex flex-wrap gap-2">
                          <Badge tone="amber">🚗 {placa}</Badge>
                          <Badge tone="indigo">⚓ {row.muelle || "—"}</Badge>
                          <Badge tone="emerald">✅ Fase 1 finalizada</Badge>
                        </div>
                        <p className="text-sm text-slate-600 dark:text-white/70">
                          Cierre:&nbsp;<strong>{formatDateTime(row.fecha_cierre)}</strong>
                        </p>
                      </div>

                      <div className="shrink-0">
                        <button
                          onClick={() => handleFase2(row)}
                          className={BTN_PRIMARY}
                          disabled={isWorking}
                          title="Crear o continuar Fase 2"
                          aria-busy={isWorking}
                        >
                          {isWorking && <Spinner />}
                          Iniciar Fase 2
                        </button>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </>
        )}

        {/* Paginación simple */}
        {count > 0 && (
          <div className="flex justify-between items-center gap-2 mt-8 flex-wrap">
            <div className="text-sm text-slate-600 dark:text-white/70">
              Página <span className="font-medium">{page}</span> de{" "}
              <span className="font-medium">{totalPages}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={page === 1}
                onClick={() => {
                  window.scrollTo({ top: 0, behavior: "smooth" });
                  setPage((p) => Math.max(1, p - 1));
                }}
                className={BTN}
                aria-label="Página anterior"
              >
                ◀ Anterior
              </button>
              <button
                disabled={page === totalPages}
                onClick={() => {
                  window.scrollTo({ top: 0, behavior: "smooth" });
                  setPage((p) => Math.min(totalPages, p + 1));
                }}
                className={BTN}
                aria-label="Página siguiente"
              >
                Siguiente ▶
              </button>
            </div>
          </div>
        )}

        {/* Modal si ya existe Fase 2 */}
        {modal && (
          <div
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
            role="dialog"
            aria-modal="true"
            aria-label="Fase 2 existente"
            onClick={() => setModal(null)}
          >
            <div
              ref={modalRef}
              className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-white/10 shadow-2xl p-6"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-xl font-semibold mb-1">Ya existe Fase 2</h2>
              <p className="text-slate-600 dark:text-slate-200 mb-5">
                Ya hay una Fase 2 para la placa <strong>{modal.row.placa_vehiculo?.toUpperCase()}</strong>.
                ¿Deseas continuarla?
              </p>
              <div className="flex gap-3 justify-end">
                <button
                  className={BTN}
                  onClick={() => setModal(null)}
                >
                  Cancelar
                </button>
                <button
                  className={BTN_PRIMARY}
                  data-autofocus
                  onClick={() => {
                    router.push(
                      `formulario?questionnaire_id=${Q_FASE2}&submission_id=${modal.fase2Id}`
                    );
                  }}
                >
                  Ir a Fase 2
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

