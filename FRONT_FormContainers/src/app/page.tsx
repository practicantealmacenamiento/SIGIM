"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  installGlobalAuthFetch,
  isAuthenticated,
  fetchWhoAmI,
  listQuestionnaires,
} from "@/lib/api.admin";

/* ========= Tipos ========= */
type QuestionnaireItem = { id: string; title: string; version: string };
type HistItem = {
  regulador_id: string;
  placa_vehiculo?: string | null;
  contenedor?: string | null;
  ultima_fecha_cierre?: string | null;
};

/* ========= Config mínima (igual que el cliente API) ========= */
const DEFAULT_API_PORT = 8000;
const API_BASE =
  (typeof window !== "undefined" &&
    (process.env.NEXT_PUBLIC_API_URL || "").toString().replace(/\/$/, "")) ||
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:${DEFAULT_API_PORT}`
    : `http://127.0.0.1:${DEFAULT_API_PORT}`);
const API_V1 = (process.env.NEXT_PUBLIC_AUTH_PREFIX || "/api/v1").replace(/\/$/, "");

/* ========= Helpers ========= */
async function fetchJSON<T = any>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    if (res.status === 401 || res.status === 403) {
      // en home no rompemos si no hay sesión
      return [] as unknown as T;
    }
    const msg = await res.text().catch(() => `${res.status}`);
    throw new Error(msg || `HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

function fmtDateTimeTz(iso?: string | null, tz = "America/Bogota") {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("es-CO", { timeZone: tz, dateStyle: "medium", timeStyle: "short" }).format(new Date(iso));
  } catch {
    return new Date(iso).toLocaleString();
  }
}

async function fetchRecent(): Promise<HistItem[]> {
  // Usamos el mismo esquema que la app: base del backend + /api/v1/…
  const url = `${API_BASE}${API_V1}/historial/reguladores/?solo_completados=1`;
  try {
    const data = await fetchJSON<HistItem[]>(url);
    // Ordenamos por ultima fecha si el backend no lo hace
    const arr = Array.isArray(data) ? data : [];
    return arr
      .slice()
      .sort(
        (a, b) =>
          Date.parse(b.ultima_fecha_cierre || "0") - Date.parse(a.ultima_fecha_cierre || "0")
      );
  } catch {
    return [];
  }
}

/* ========= UI ========= */
const CARD =
  "rounded-2xl border border-slate-200/70 dark:border-white/10 bg-white dark:bg-slate-800 shadow-sm";
const BTN =
  "inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-sky-300/40 dark:focus:ring-sky-600/40";
const BTN_PRIMARY =
  `${BTN} bg-sky-600 hover:bg-sky-700 text-white shadow`;
const BTN_SOFT =
  `${BTN} border border-slate-200 dark:border-white/15 text-slate-700 dark:text-slate-100 hover:bg-slate-100/70 dark:hover:bg-white/5`;

export default function Home() {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [username, setUsername] = useState("");
  const [isStaff, setIsStaff] = useState(false);

  const [qus, setQus] = useState<QuestionnaireItem[] | null>(null);
  const [hist, setHist] = useState<HistItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // 1) Bootstrap auth de cliente y whoami
  useEffect(() => {
    installGlobalAuthFetch(); // añade Authorization: Bearer <token> globalmente
    (async () => {
      if (!isAuthenticated()) {
        setAuthed(false);
        setUsername("");
        setIsStaff(false);
        return;
      }
      try {
        const me = await fetchWhoAmI();
        setAuthed(true);
        setUsername(me.username || "");
        setIsStaff(!!me.is_staff);
      } catch {
        setAuthed(false);
        setUsername("");
        setIsStaff(false);
      }
    })();
  }, []);

  // 2) Cargar info solo si hay sesión
  useEffect(() => {
    if (authed !== true) {
      if (authed === false) {
        setLoading(false);
        setQus([]);
        setHist([]);
      }
      return;
    }

    let mounted = true;
    (async () => {
      setLoading(true);
      try {
        // listQuestionnaires ya soporta /management y cae a /cuestionarios
        const [qs, last] = await Promise.all([listQuestionnaires(), fetchRecent()]);
        if (!mounted) return;

        // Para el home solo necesitamos id/title/version
        setQus((qs || []).map((q) => ({ id: q.id, title: q.title, version: q.version })));
        setHist((last || []).slice(0, 5));
        setErr(null);
      } catch (e: any) {
        if (!mounted) return;
        setErr(typeof e?.message === "string" ? e.message : "No se pudo cargar la información");
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => {
      mounted = false;
    };
  }, [authed]);

  const today = useMemo(() => {
    try {
      return new Intl.DateTimeFormat("es-CO", { dateStyle: "full" }).format(new Date());
    } catch {
      return new Date().toLocaleDateString();
    }
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Hero */}
      <header className="mx-auto max-w-6xl px-6 pt-10">
        <div className={`${CARD} p-6 md:p-8`}>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-300" aria-live="polite">{today}</p>
              <h1 className="mt-1 text-2xl md:text-3xl font-semibold text-slate-900 dark:text-white">
                Hola{username ? `, ${username}` : ""} 👋
              </h1>
              <p className="mt-2 text-slate-600 dark:text-slate-300">
                Accesos rápidos y tu actividad reciente.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link href="/formulario" className={BTN_PRIMARY}>
                Nuevo registro
              </Link>
              <Link href="/historial" className={BTN_SOFT}>
                Ver historial
              </Link>
              {isStaff && (
                <Link
                  href="/admin"
                  className={`${BTN} border border-amber-300/50 bg-amber-50 dark:bg-amber-900/20 text-amber-900 dark:text-amber-200 font-semibold hover:bg-amber-100/80 dark:hover:bg-amber-900/30`}
                >
                  Panel admin
                </Link>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-14">
        {/* Home ligero (no logueado) */}
        {authed === false && (
          <section className={`mt-8 ${CARD} p-6`} aria-live="polite">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">Bienvenido</h2>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              Inicia sesión para ver tus cuestionarios y movimientos recientes.
            </p>
            <div className="mt-4">
              <Link href="/login" className={BTN_PRIMARY}>
                Iniciar sesión
              </Link>
            </div>
          </section>
        )}

        {/* Dashboard (logueado) */}
        {authed === true && (
          <>
            {err && (
              <div
                className="mt-6 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/40 dark:bg-rose-950/40 dark:text-rose-200 p-4"
                role="status"
                aria-live="polite"
              >
                No pudimos cargar algunos datos. Puedes seguir usando los atajos de arriba.
              </div>
            )}

            <section className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Cuestionarios */}
              <div className={`md:col-span-2 ${CARD}`}>
                <div className="px-5 py-4 border-b border-slate-100 dark:border-white/10">
                  <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                    Cuestionarios disponibles
                  </h2>
                  <p className="text-sm text-slate-500 dark:text-slate-300">
                    Elige con cuál quieres comenzar.
                  </p>
                </div>
                <div className="p-5">
                  {loading && (
                    <div className="animate-pulse space-y-3">
                      <div className="h-10 rounded-lg bg-slate-100 dark:bg-white/5" />
                      <div className="h-10 rounded-lg bg-slate-100 dark:bg-white/5" />
                      <div className="h-10 rounded-lg bg-slate-100 dark:bg-white/5" />
                    </div>
                  )}

                  {!loading && (qus?.length ?? 0) === 0 && (
                    <p className="text-sm text-slate-500 dark:text-slate-300">
                      No hay cuestionarios disponibles en este momento.
                    </p>
                  )}

                  <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {(qus ?? []).map((q) => (
                      <li key={q.id}>
                        <Link
                          href={`/formulario?questionnaire_id=${q.id}`}
                          className="group flex items-center justify-between rounded-xl border border-slate-200 dark:border-white/10 px-4 py-3 hover:bg-slate-50 dark:hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-sky-300/40 dark:focus:ring-sky-600/40"
                          title={`Abrir ${q.title}`}
                        >
                          <div className="min-w-0">
                            <p className="font-medium text-slate-900 dark:text-white truncate">
                              {q.title}
                            </p>
                            <p className="text-xs text-slate-500 dark:text-slate-300">
                              v{q.version}
                            </p>
                          </div>
                          <span
                            className="text-sky-600 transition-transform group-hover:translate-x-0.5"
                            aria-hidden="true"
                          >
                            ➜
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Últimos movimientos */}
              <div className={`${CARD}`}>
                <div className="px-5 py-4 border-b border-slate-100 dark:border-white/10">
                  <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                    Últimos movimientos
                  </h2>
                  <p className="text-sm text-slate-500 dark:text-slate-300">
                    Fases finalizadas recientemente.
                  </p>
                </div>
                <div className="p-5">
                  {loading && (
                    <div className="space-y-3 animate-pulse">
                      <div className="h-8 rounded-lg bg-slate-100 dark:bg-white/5" />
                      <div className="h-8 rounded-lg bg-slate-100 dark:bg-white/5" />
                      <div className="h-8 rounded-lg bg-slate-100 dark:bg-white/5" />
                    </div>
                  )}

                  {!loading && (hist?.length ?? 0) === 0 && (
                    <p className="text-sm text-slate-500 dark:text-slate-300">
                      Aún no hay registros finalizados.
                    </p>
                  )}

                  <ul className="space-y-3">
                    {(hist ?? []).map((h) => (
                      <li
                        key={h.regulador_id}
                        className="flex items-center justify-between rounded-xl border border-slate-200 dark:border-white/10 px-3 py-2"
                      >
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                            Regulador: {h.regulador_id}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-300">
                            {h.placa_vehiculo ? `Placa: ${h.placa_vehiculo}` : "Sin placa"}{" "}
                            {h.contenedor ? `· Contenedor: ${h.contenedor}` : ""}
                          </p>
                        </div>
                        <span className="text-xs text-slate-500 dark:text-slate-300">
                          {fmtDateTimeTz(h.ultima_fecha_cierre)}
                        </span>
                      </li>
                    ))}
                  </ul>

                  <div className="mt-4 text-right">
                    <Link className="text-sm text-sky-600 hover:text-sky-700" href="/historial">
                      Ver todo el historial →
                    </Link>
                  </div>
                </div>
              </div>
            </section>

            {/* Bloque admin opcional */}
            {isStaff && (
              <section className="mt-8 rounded-2xl border border-emerald-300/40 bg-emerald-50 dark:bg-emerald-900/20 dark:border-emerald-900/40 p-5">
                <h3 className="text-sm font-semibold text-emerald-800 dark:text-emerald-200 mb-2">
                  Herramientas de administración
                </h3>
                <div className="flex flex-wrap gap-3">
                  <Link
                    href="/admin"
                    className="rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-white/5"
                  >
                    Gestor de cuestionarios
                  </Link>
                  <Link
                    href="/admin#actores"
                    className="rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-white/5"
                  >
                    Catálogo de actores
                  </Link>
                  <Link
                    href="/admin#usuarios"
                    className="rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-white/5"
                  >
                    Usuarios
                  </Link>
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
