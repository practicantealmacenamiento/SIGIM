/* eslint-disable jsx-a11y/role-has-required-aria-props */
import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { searchCatalogActors } from "../../lib/api.form";

/**
 * Tipos de actor compatibles con el catálogo.
 */
type ActorTipo = "TRANSPORTISTA" | "PROVEEDOR" | "RECEPTOR";

/**
 * Estructura mínima de un actor devuelto por el backend.
 */
export type ActorItem = {
  id: string;
  nombre: string;
  nit?: string | null;
};

/**
 * Props del componente:
 * - `multiple`: si es true, deja el popover abierto para seleccionar varios.
 * - `selectFirstOnEnter`: al presionar Enter, toma el primer resultado (si hay).
 */
type Props = {
  tipo: ActorTipo;
  defaultValue?: string;
  disabled?: boolean;
  onSelect: (actor: ActorItem) => void;
  placeholder?: string;
  className?: string;
  multiple?: boolean;
  selectFirstOnEnter?: boolean;
};

/* =========================================================
   Hook: useDebounced — Devuelve un valor con retardo controlado
   ========================================================= */
function useDebounced<T>(value: T, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

/* =========================================================
   Componente: ActorInput
   - Autocomplete para actores del catálogo (proveedor/transportista/receptor)
   - Búsqueda remota con debounce y cancelación por AbortController
   - Accesibilidad ARIA básica (listbox/option)
   ========================================================= */
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
  // Estado del buscador
  const [query, setQuery] = useState(defaultValue);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<ActorItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Refs
  const inputRef = useRef<HTMLInputElement | null>(null);
  const popoverRef = useRef<HTMLDivElement | null>(null);

  // Valor "debounced" para no disparar búsquedas por cada tecla
  const debounced = useDebounced(query, 300);
  const canSearch = useMemo(() => debounced.trim().length >= 2, [debounced]);

  // Sincronizar defaultValue si cambia externamente
  useEffect(() => {
    setQuery(defaultValue || "");
  }, [defaultValue]);

  // Búsqueda remota mientras el popover esté abierto y haya 2+ letras
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

  // Selección de un item de la lista
  const handlePick = useCallback(
    (actor: ActorItem) => {
      onSelect(actor);
      if (multiple) {
        // Limpia, mantiene abierto y devuelve el foco para seguir agregando
        setQuery("");
        setOpen(true);
        requestAnimationFrame(() => inputRef.current?.focus());
      } else {
        setQuery(actor.nombre);
        setOpen(false);
      }
    },
    [onSelect, multiple]
  );

  // Enter => selecciona el primer resultado (opcional)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (selectFirstOnEnter && e.key === "Enter" && open && items.length > 0) {
      e.preventDefault();
      handlePick(items[0]);
    }
    if (e.key === "Escape" && open) {
      e.preventDefault();
      setOpen(false);
    }
  };

  // Cierre por click fuera (más robusto que blur sobre el input)
  useEffect(() => {
    if (!open) return;
    const onDocClick = (ev: MouseEvent) => {
      const t = ev.target as Node;
      if (inputRef.current?.contains(t)) return;
      if (popoverRef.current?.contains(t)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  // ID base para relacionar input y listbox
  const listboxId = useMemo(() => `actor-listbox-${tipo.toLowerCase()}`, [tipo]);

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
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        autoComplete="off"
        aria-expanded={open}
        aria-controls={open ? listboxId : undefined}
        role="combobox"
        className="w-full rounded-md border px-3 py-2 outline-none focus:ring ring-sky-300/60 bg-white dark:bg-slate-900"
      />

      {open && (
        <div
          ref={popoverRef}
          className="absolute z-50 mt-1 w-full rounded-md border bg-white dark:bg-slate-900 dark:border-white/10 shadow-lg overflow-hidden"
        >
          {loading && (
            <div className="px-3 py-2 text-sm text-gray-500 dark:text-slate-400">
              Buscando…
            </div>
          )}

          {!loading && !canSearch && (
            <div className="px-3 py-2 text-sm text-gray-500 dark:text-slate-400">
              Escribe al menos 2 letras para buscar.
            </div>
          )}

          {!loading && canSearch && error && (
            <div className="px-3 py-2 text-sm text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          {!loading && canSearch && !error && items.length === 0 && (
            <div className="px-3 py-2 text-sm text-gray-500 dark:text-slate-400">
              Sin resultados.
            </div>
          )}

          {!loading && !error && items.length > 0 && (
            <ul
              id={listboxId}
              role="listbox"
              className="max-h-64 overflow-auto divide-y divide-slate-100 dark:divide-white/10"
            >
              {items.map((it) => (
                <li
                  key={it.id}
                  role="option"
                  className="cursor-pointer px-3 py-2 hover:bg-gray-50 dark:hover:bg-white/5"
                  onMouseDown={(e) => e.preventDefault()} // evita blur del input
                  onClick={() => handlePick(it)}
                  title={it.nit ? `${it.nombre} — ${it.nit}` : it.nombre}
                >
                  <div className="text-sm font-medium text-slate-800 dark:text-slate-100">
                    {it.nombre}
                  </div>
                  {it.nit && (
                    <div className="text-xs text-gray-500 dark:text-slate-400">
                      NIT: {it.nit}
                    </div>
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

