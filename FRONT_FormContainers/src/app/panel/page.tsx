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

  const handleFase2 = async (row: SubmissionRow) => {
    const placa = (row.placa_vehiculo || "").trim().toUpperCase();
    if (!placa) return alert("Submission sin placa");

    try {
      const existente = await buscarFase2PorPlaca(placa);
      const sub = existente?.id
        ? existente
        : await crearSubmissionFase2({
            questionnaire_id_fase2: Q_FASE2,
            placa_vehiculo: placa,
            regulador_id: row.regulador_id ?? row.id,
          });
      router.push(`formulario?questionnaire_id=${Q_FASE2}&submission_id=${sub.id}`);
    } catch (e: any) {
      alert(e.message || "Error al crear Fase 2");
    }
  };

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
                      className="px-4 py-2 rounded-lg bg-skyBlue text-white hover:bg-skyBlue/90 transition"
                    >
                      Iniciar Fase 2
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
