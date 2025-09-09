"use client";
import React from "react";

type Actor = { id: string; nombre: string; documento?: string | null };

type Props = {
  tipo: "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR";
  defaultValue?: string;
  disabled?: boolean;
  onSelect: (actor: Actor) => void;
  /** Base de la API; si no se pasa, usa NEXT_PUBLIC_API_BASE o relativo */
  apiBase?: string;
  /** Si usas JWT, pásalo aquí; si usas sesión/cookies, no es necesario */
  authToken?: string;
  /** Milisegundos de debounce */
  delay?: number;
};

export default function ActorInput({
  tipo,
  defaultValue = "",
  disabled,
  onSelect,
  apiBase,
  authToken,
  delay = 280,
}: Props) {
  const [q, setQ] = React.useState(defaultValue);
  const [open, setOpen] = React.useState(false);
  const [items, setItems] = React.useState<Actor[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const abortRef = React.useRef<AbortController | null>(null);
  const timer = React.useRef<number | null>(null);

  // Construye URL (intenta /api/... y si 404 prueba /app/api/...)
  const base =
    apiBase ??
    (typeof process !== "undefined" ? process.env.NEXT_PUBLIC_API_BASE : "") ??
    "";

  async function fetchActors(url: string, ac: AbortController) {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (authToken) headers.Authorization = `Bearer ${authToken}`;

    return fetch(url, {
      method: "GET",
      signal: ac.signal,
      headers,
      credentials: authToken ? "omit" : "include",
    });
  }

  function buildUrl(prefix: string, value: string) {
    const u = new URL(
      `${prefix.replace(/\/$/, "")}/catalogos/actores/`,
      typeof window !== "undefined" ? window.location.origin : "http://localhost",
    );
    u.searchParams.set("tipo", tipo);
    u.searchParams.set("search", value);
    const final =
      base && /^https?:\/\//.test(base)
        ? new URL(u.pathname + u.search, base).toString()
        : u.pathname + u.search;
    return final;
  }

  async function search(v: string) {
    if (abortRef.current) abortRef.current.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setError(null);

    try {
      // 1) /api/...
      let url = buildUrl("/api", v);
      let res = await fetchActors(url, ac);

      // 2) fallback /app/api/...
      if (res.status === 404) {
        url = buildUrl("/app/api", v);
        res = await fetchActors(url, ac);
      }

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status} ${text || ""}`.trim());
      }

      const data = (await res.json()) as Actor[];
      setItems(data.slice(0, 12));
      setOpen(data.length > 0);
    } catch (e: any) {
      if (e?.name === "AbortError") return;
      setItems([]);
      setOpen(false);
      setError(e?.message || "Error al cargar actores");
      if (process.env.NODE_ENV !== "production") console.warn("[ActorInput]", e);
    } finally {
      setLoading(false);
    }
  }

  function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    const v = e.target.value;
    setQ(v);
    setError(null);
    if (timer.current) window.clearTimeout(timer.current);
    if (!v || v.trim().length < 2) {
      setItems([]);
      setOpen(false);
      return;
    }
    timer.current = window.setTimeout(() => search(v.trim()), delay) as unknown as number;
  }

  function onFocus() {
    if (items.length > 0) setOpen(true);
    else if (q.trim().length >= 2) search(q.trim());
  }

  function pick(a: Actor) {
    setQ(a.nombre);
    setOpen(false);
    onSelect(a);
  }

  return (
    <div className="relative">
      <input
        className={[
          "w-full rounded-lg border px-3 py-2 outline-none",
          "bg-white text-slate-900 placeholder-slate-400",
          "dark:bg-slate-900 dark:text-slate-100 dark:placeholder-slate-500",
          "border-slate-300 focus:ring-2 focus:ring-sky-400/30 focus:border-sky-400/40",
          "dark:border-white/10 dark:focus:ring-sky-400/30 dark:focus:border-sky-400/40",
          disabled ? "opacity-60 cursor-not-allowed" : "",
        ].join(" ")}
        value={q}
        onChange={onChange}
        onFocus={onFocus}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        placeholder={`Buscar ${tipo.toLowerCase()}…`}
        disabled={disabled}
        autoComplete="off"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-haspopup="listbox"
      />
      {loading && (
        <div className="absolute right-2 top-2 text-xs select-none dark:text-slate-300">…</div>
      )}

      {!loading && error && (
        <div className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</div>
      )}

      {open && !disabled && (
        <ul
          role="listbox"
          className={[
            "absolute z-50 w-full mt-1 max-h-64 overflow-auto rounded-xl border shadow-lg",
            "bg-white text-slate-900 border-slate-200",
            "dark:bg-slate-900 dark:text-slate-100 dark:border-white/10",
          ].join(" ")}
        >
          {items.length === 0 && (
            <li className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400 select-none">
              Sin resultados
            </li>
          )}
          {items.map((it) => (
            <li
              key={it.id}
              role="option"
              className={[
                "px-3 py-2 cursor-pointer text-sm",
                "text-slate-800 hover:bg-slate-100",
                "dark:text-slate-100 dark:hover:bg-slate-700/60",
              ].join(" ")}
              onMouseDown={() => pick(it)}
              title={it.documento || ""}
            >
              {it.nombre}
              {it.documento ? ` — ${it.documento}` : ""}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
