import React, { useEffect, useMemo, useRef, useState } from "react";
import { searchCatalogActors } from "../../lib/api.form";

type ActorTipo = "TRANSPORTISTA" | "PROVEEDOR" | "RECEPTOR";

export type ActorItem = {
  id: string;
  nombre: string;
  nit?: string | null;
};

type Props = {
  tipo: ActorTipo;
  defaultValue?: string;
  disabled?: boolean;
  onSelect: (actor: ActorItem) => void;
  placeholder?: string;
  className?: string;
};

function useDebounced<T>(value: T, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export default function ActorInput({
  tipo,
  defaultValue = "",
  disabled,
  onSelect,
  placeholder = "Escribe al menos 2 letras…",
  className = "",
}: Props) {
  const [query, setQuery] = useState(defaultValue);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<ActorItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const debounced = useDebounced(query, 300);
  const canSearch = useMemo(() => debounced.trim().length >= 2, [debounced]);

  useEffect(() => {
    setQuery(defaultValue || "");
  }, [defaultValue]);

  useEffect(() => {
    if (!open) return;
    if (!canSearch) {
      setItems([]);
      setError(null);
      return;
    }

    const controller = new AbortController();
    const params = new URLSearchParams({
      tipo,                  // ← el back espera 'tipo' exactamente así
      search: debounced,     // ← y el filtro es 'search', NO 'q' ni 'term'
      limit: "15",
    });

    setLoading(true);
    setError(null);

    setLoading(true);
    setError(null);

    searchCatalogActors({
      tipo,                   // "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR"
      search: debounced,      // texto que teclea el usuario (debounced)
      limit: 15,
      signal: controller.signal,
    })
      .then((data) => setItems(Array.isArray(data) ? data : []))
      .catch((e: any) => {
        if (e?.name !== "AbortError") setError("No se pudo buscar actores.");
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [open, canSearch, debounced, tipo]);

  const handlePick = (actor: ActorItem) => {
    setOpen(false);
    setQuery(actor.nombre);
    onSelect(actor);
  };

  return (
    <div className={`relative ${className}`}>
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          // retrasa el blur para permitir el click en la lista
          setTimeout(() => setOpen(false), 150);
        }}
        disabled={disabled}
        placeholder={placeholder}
        className="w-full rounded-md border px-3 py-2 outline-none focus:ring"
        autoComplete="off"
      />

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-white shadow-lg">
          {loading && (
            <div className="px-3 py-2 text-sm text-gray-500">Buscando…</div>
          )}

          {!loading && !canSearch && (
            <div className="px-3 py-2 text-sm text-gray-500">
              Escribe al menos 2 letras para buscar.
            </div>
          )}

          {!loading && canSearch && error && (
            <div className="px-3 py-2 text-sm text-red-600">{error}</div>
          )}

          {!loading && canSearch && !error && items.length === 0 && (
            <div className="px-3 py-2 text-sm text-gray-500">Sin resultados.</div>
          )}

          {!loading && !error && items.length > 0 && (
            <ul className="max-h-64 overflow-auto">
              {items.map((it) => (
                <li
                  key={it.id}
                  className="cursor-pointer px-3 py-2 hover:bg-gray-100"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => handlePick(it)}
                  title={it.nit ? `${it.nombre} — ${it.nit}` : it.nombre}
                >
                  <div className="text-sm font-medium">{it.nombre}</div>
                  {it.nit && (
                    <div className="text-xs text-gray-500">NIT: {it.nit}</div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
