"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  listarFase1Finalizados,
  buscarFase2PorPlaca,
  crearSubmissionFase2,
  type SubmissionRow,
} from "@/lib/api.panel";

const CARD =
  "rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 shadow-sm";

const Q_FASE2 = process.env.NEXT_PUBLIC_Q_FASE2_ID!;

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

function Badge({ children, tone = "slate" }: { children: React.ReactNode; tone?: "amber" | "emerald" | "indigo" | "slate" }) {
  const tones: Record<string, string> = {
    amber: "bg-amber-100 dark:bg-amber-400/15 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-300/20",
    emerald: "bg-emerald-100 dark:bg-emerald-400/10 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-300/20",
    indigo: "bg-indigo-100 dark:bg-indigo-400/10 text-indigo-800 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-300/20",
    slate: "bg-slate-100 dark:bg-white/5 text-slate-800 dark:text-white/80 border border-slate-200 dark:border-white/10",
  };
  return <span className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-sm font-medium ${tones[tone]}`}>{children}</span>;
}

export default function PanelPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<SubmissionRow[]>([]);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [loadingFase2, setLoadingFase2] = useState<string | null>(null); // id para loading individual
  const [modal, setModal] = useState<{ row: SubmissionRow; fase2Id?: string } | null>(null);

  // Carga submissions Fase 1 finalizados
  const load = async () => {
    try {
      setError(null);
      setLoading(true);
      const res = await listarFase1Finalizados({ search, page });
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
  }, [search, page]);

  // Iniciar Fase 2 (o ir a la existente)
  const handleFase2 = async (row: SubmissionRow) => {
    const placa = (row.placa_vehiculo || "").trim().toUpperCase();
    if (!placa) return alert("Submission sin placa");
    setLoadingFase2(row.id);
    try {
      const existente = await buscarFase2PorPlaca(placa);
      if (existente?.id) {
        // Si ya existe Fase 2, muestra modal para ir o solo redirecciona
        setModal({ row, fase2Id: existente.id });
        // Si prefieres, redirecciona sin preguntar:
        // router.push(`formulario?questionnaire_id=${Q_FASE2}&submission_id=${existente.id}`);
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

  // UI paginación simple
  const totalPages = Math.ceil(count / 20);

  return (
    <main className="min-h-screen px-6 md:px-8 py-8">
      <div className="max-w-6xl mx-auto">
        <header className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
          <h1 className="text-3xl font-bold">Panel de control</h1>
          <input
            type="search"
            placeholder="Buscar por placa (Ej: ABC123)"
            className="w-full md:w-[300px] px-4 py-2 rounded-lg border border-slate-300 dark:border-white/10 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-white"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value.toUpperCase());
              setPage(1);
            }}
          />
        </header>

        {loading ? (
          <p className="text-slate-600 dark:text-white/70">Cargando...</p>
        ) : error ? (
          <div className="p-6 text-center border rounded-xl border-red-300 dark:border-red-500 bg-red-50 dark:bg-red-950/20 text-red-700 dark:text-red-300">
            {error}
          </div>
        ) : rows.length === 0 ? (
          <div className="p-6 text-center border rounded-xl border-slate-300 dark:border-white/10 bg-white dark:bg-slate-900 text-slate-600 dark:text-white/70">
            No hay resultados.
          </div>
        ) : (
          <ul className="grid gap-5">
            {rows.map((row) => (
              <li key={row.id} className={`${CARD} p-5 md:p-6`}>
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                  <div className="space-y-2">
                    <div className="flex flex-wrap gap-2">
                      <Badge tone="amber">🚗 {row.placa_vehiculo?.toUpperCase() || "Sin placa"}</Badge>
                      <Badge tone="indigo">⚓ {row.muelle || "—"}</Badge>
                      <Badge tone="emerald">Fase 1 finalizada</Badge>
                    </div>
                    <p className="text-sm text-slate-600 dark:text-white/70">
                      Cierre: <strong>{formatDateTime(row.fecha_cierre)}</strong>
                    </p>
                  </div>

                  <div>
                    <button
                      onClick={() => handleFase2(row)}
                      className="px-4 py-2 rounded-lg bg-skyBlue text-white hover:bg-skyBlue/90 transition flex items-center gap-2"
                      disabled={!!loadingFase2}
                    >
                      {loadingFase2 === row.id && (
                        <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
                        </svg>
                      )}
                      Iniciar Fase 2
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}

        {/* Paginación simple */}
        {totalPages > 1 && (
          <div className="flex justify-center gap-2 mt-8">
            <button
              disabled={page === 1}
              onClick={() => setPage(p => Math.max(1, p - 1))}
              className="px-3 py-2 rounded-lg border bg-white dark:bg-slate-900"
            >
              ◀ Anterior
            </button>
            <span className="px-4 py-2 text-slate-700 dark:text-white">{page} / {totalPages}</span>
            <button
              disabled={page === totalPages}
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              className="px-3 py-2 rounded-lg border bg-white dark:bg-slate-900"
            >
              Siguiente ▶
            </button>
          </div>
        )}

        {/* Modal si ya existe Fase 2 */}
        {modal && (
          <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center">
            <div className="bg-white dark:bg-slate-900 p-8 rounded-2xl shadow-xl max-w-md w-full">
              <h2 className="text-2xl font-bold mb-2">Ya existe Fase 2 para esta placa</h2>
              <p className="mb-5 text-slate-600 dark:text-slate-200">
                ¿Quieres continuar con la Fase 2 ya creada?
              </p>
              <div className="flex gap-4 justify-center">
                <button
                  className="px-4 py-2 rounded-lg bg-skyBlue text-white font-medium"
                  onClick={() => {
                    router.push(`formulario?questionnaire_id=${Q_FASE2}&submission_id=${modal.fase2Id}`);
                  }}
                >
                  Ir a Fase 2
                </button>
                <button
                  className="px-4 py-2 rounded-lg bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-white"
                  onClick={() => setModal(null)}
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
