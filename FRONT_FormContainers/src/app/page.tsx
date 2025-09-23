"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

/* ===== Tipos mínimos ===== */
type QuestionnaireItem = { id: string; title: string; version: string };
type HistItem = {
  regulador_id: string;
  placa_vehiculo?: string | null;
  contenedor?: string | null;
  ultima_fecha_cierre?: string | null;
};

type WhoAmI = {
  authenticated?: boolean;
  is_authenticated?: boolean;
  username?: string;
  is_staff?: boolean;
};

/* ===== Helpers ===== */
async function fetchJSON<T = any>(url: string): Promise<T> {
  // Asegurar que las URLs tengan barra final para evitar 301
  const normalizedUrl = url.includes('?') 
    ? url.replace(/([^?])(\?)/, '$1/$2')  // Agregar barra antes del query string
    : url.endsWith('/') ? url : url + '/';  // Agregar barra final si no la tiene
    
  const res = await fetch(normalizedUrl, {
    credentials: "include",
    cache: "no-store",
  });
  if (!res.ok) {
    // En home no rompemos: entregamos vacío si es 401/403
    if (res.status === 401 || res.status === 403) return [] as unknown as T;
    const text = await res.text().catch(() => `${res.status}`);
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

async function fetchWhoAmI(): Promise<{ ok: boolean; username: string; isStaff: boolean }> {
  // Probamos con slash y sin slash (según tu server logs ambos existen)
  const tryOne = async (u: string) => {
    try {
      const data = (await fetchJSON<WhoAmI>(u)) || {};
      const authed = Boolean(data.is_authenticated ?? data.authenticated ?? false);
      return {
        ok: authed,
        username: data.username || "",
        isStaff: Boolean(data.is_staff),
      };
    } catch {
      return { ok: false, username: "", isStaff: false };
    }
  };
  const a = await tryOne("/api/whoami/");
  if (a.ok) return a;
  const b = await tryOne("/api/whoami/");
  return b.ok ? b : { ok: false, username: "", isStaff: false };
}

/* ====== UI ====== */
export default function Home() {
  const [authed, setAuthed] = useState<null | boolean>(null);
  const [username, setUsername] = useState("");
  const [isStaff, setIsStaff] = useState(false);

  const [qus, setQus] = useState<QuestionnaireItem[] | null>(null);
  const [hist, setHist] = useState<HistItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // 1) Confirmar sesión primero
  useEffect(() => {
    let mounted = true;
    (async () => {
      const who = await fetchWhoAmI();
      if (!mounted) return;
      setAuthed(who.ok);
      setUsername(who.username || "");
      setIsStaff(who.isStaff || false);
    })();
    return () => { mounted = false; };
  }, []);

  // 2) Cargar datos solo si está autenticado
  useEffect(() => {
    if (authed !== true) {
      // si aún no sabemos, dejamos el loader; si no authed, no pedimos nada
      if (authed === false) {
        setLoading(false);
        setQus([]);
        setHist([]);
      }
      return;
    }
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const [qData, hData] = await Promise.all([
          fetchJSON<QuestionnaireItem[]>("/api/cuestionarios/"),
          fetchJSON<HistItem[]>("/api/historial/reguladores/?solo_completados=1"),
        ]);
        if (!mounted) return;
        setQus(qData ?? []);
        setHist((hData ?? []).slice(0, 5));
        setErr(null);
      } catch (e: any) {
        if (!mounted) return;
        setErr(typeof e?.message === "string" ? e.message : "Error cargando datos");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [authed]);

  const today = useMemo(() => new Date().toLocaleDateString(), []);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Hero */}
      <header className="mx-auto max-w-6xl px-6 pt-10">
        <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-800 p-6 md:p-8 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-300">{today}</p>
              <h1 className="mt-1 text-2xl md:text-3xl font-semibold text-slate-900 dark:text-white">
                Hola{username ? `, ${username}` : ""} 👋
              </h1>
              <p className="mt-2 text-slate-600 dark:text-slate-300">
                Accesos rápidos y último movimiento de tus formularios.
              </p>
            </div>

            <div className="flex gap-3">
              <Link
                href="/formulario"
                className="inline-flex items-center justify-center rounded-xl bg-sky-600 hover:bg-sky-700 text-white px-4 py-2.5 text-sm font-medium shadow"
              >
                Nuevo registro
              </Link>
              <Link
                href="/historial"
                className="inline-flex items-center justify-center rounded-xl border border-slate-200 dark:border-white/15 px-4 py-2.5 text-sm font-medium text-slate-700 dark:text-slate-100 hover:bg-slate-100/70 dark:hover:bg-white/5"
              >
                Ver historial
              </Link>
              {isStaff && (
                <Link
                  href="/admin"
                  className="inline-flex items-center justify-center rounded-xl border border-amber-300/50 bg-amber-50 dark:bg-amber-900/20 text-amber-900 dark:text-amber-200 px-4 py-2.5 text-sm font-semibold"
                >
                  Panel admin
                </Link>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-14">
        {/* Si no está logueado, mostramos home “ligero” sin redirecciones */}
        {authed === false && (
          <section className="mt-8 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-800 p-6">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">Bienvenido</h2>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              Inicia sesión para ver tus cuestionarios y movimientos recientes.
            </p>
            <div className="mt-4">
              <Link
                href="/login"
                className="inline-flex items-center justify-center rounded-xl bg-sky-600 hover:bg-sky-700 text-white px-4 py-2.5 text-sm font-medium shadow"
              >
                Iniciar sesión
              </Link>
            </div>
          </section>
        )}

        {/* Si está logueado, mostramos dashboard */}
        {authed === true && (
          <>
            {/* Error / aviso */}
            {err && (
              <div className="mt-6 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/40 dark:bg-rose-950/40 dark:text-rose-200 p-4">
                No pudimos cargar algunos datos. Puedes seguir usando los atajos de arriba.
              </div>
            )}

            {/* Tarjetas principales */}
            <section className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Cuestionarios */}
              <div className="md:col-span-2 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-800 shadow-sm">
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
                          className="group flex items-center justify-between rounded-xl border border-slate-200 dark:border-white/10 px-4 py-3 hover:bg-slate-50 dark:hover:bg-white/5"
                        >
                          <div>
                            <p className="font-medium text-slate-900 dark:text-white">
                              {q.title}
                            </p>
                            <p className="text-xs text-slate-500 dark:text-slate-300">
                              v{q.version}
                            </p>
                          </div>
                          <span className="text-sky-600 group-hover:translate-x-0.5 transition">
                            ➜
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Últimos movimientos */}
              <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-800 shadow-sm">
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
                          {h.ultima_fecha_cierre
                            ? new Date(h.ultima_fecha_cierre).toLocaleString()
                            : "-"}
                        </span>
                      </li>
                    ))}
                  </ul>

                  <div className="mt-4 text-right">
                    <Link
                      className="text-sm text-sky-600 hover:text-sky-700"
                      href="/historial"
                    >
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


