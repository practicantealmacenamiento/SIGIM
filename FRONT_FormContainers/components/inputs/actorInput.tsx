import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
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
  /** Modo selección múltiple: limpia input, mantiene abierto y refocus tras seleccionar */
  multiple?: boolean;
  /** Si true, Enter selecciona el primer resultado cuando hay lista */
  selectFirstOnEnter?: boolean;
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
  multiple = false,
  selectFirstOnEnter = true,
}: Props) {
  const [query, setQuery] = useState(defaultValue);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<ActorItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const debounced = useDebounced(query, 300);
  const canSearch = useMemo(() => debounced.trim().length >= 2, [debounced]);

  // Sincroniza el valor inicial si cambia el prop
  useEffect(() => {
    setQuery(defaultValue || "");
  }, [defaultValue]);

  // Buscar mientras esté abierto y haya 2+ letras
  useEffect(() => {
    if (!open) return;
    if (!canSearch) {
      setItems([]);
      setError(null);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    searchCatalogActors({
      tipo,
      search: debounced,
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

  const handlePick = useCallback((actor: ActorItem) => {
    onSelect(actor);
    if (multiple) {
      // Limpia, deja abierto y devuelve el foco para seguir agregando
      setQuery("");
      setOpen(true);
      requestAnimationFrame(() => inputRef.current?.focus());
    } else {
      setQuery(actor.nombre);
      setOpen(false);
    }
  }, [onSelect, multiple]);

  // Enter -> selecciona el primer resultado visible (opcional)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (selectFirstOnEnter && e.key === "Enter" && open && items.length > 0) {
      e.preventDefault();
      handlePick(items[0]);
    }
  };

  return (
    <div className={`relative ${className}`}>
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}  // permite click en la lista
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        className="w-full rounded-md border px-3 py-2 outline-none focus:ring"
        autoComplete="off"
      />

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-white shadow-lg overflow-hidden">
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
            <ul role="listbox" className="max-h-64 overflow-auto divide-y">
              {items.map((it) => (
                <li
                  key={it.id}
                  role="option"
                  className="cursor-pointer px-3 py-2 hover:bg-gray-50"
                  onMouseDown={(e) => e.preventDefault()} // evita blur
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
