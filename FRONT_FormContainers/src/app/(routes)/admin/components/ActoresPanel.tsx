import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  adminCreateActor,
  adminDeleteActor,
  adminListActors,
  adminUpdateActor,
  type Actor as AdminActor,
  type ActorTipo,
  type Paginated,
} from "@/lib/api.admin";

import { useDebounced } from "./hooks";
import { shell, SearchIcon, Section, SkeletonRows } from "./ui";
import type { ToastPush } from "./toasts";

type Props = {
  toast: ToastPush;
};

export function ActoresPanel({ toast }: Props) {
  const [query, setQuery] = useState("");
  const debouncedQ = useDebounced(query, 350);
  const [tipo, setTipo] = useState<ActorTipo | "">("");
  const [pageSize, setPageSize] = useState(25);
  const [page, setPage] = useState(1);
  const [refreshKey, setRefreshKey] = useState(0);

  const [display, setDisplay] = useState<AdminActor[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const [editing, setEditing] = useState<AdminActor | null>(null);
  const [creating, setCreating] = useState(false);

  const reqId = useRef(0);

  const searchRef = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (
        (e.key === "/" || e.key === "k") &&
        (e.ctrlKey || !e.metaKey) &&
        document.activeElement?.tagName !== "INPUT"
      ) {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    setPage(1);
  }, [debouncedQ, tipo, pageSize]);

  useEffect(() => {
    let cancelled = false;
    const myReq = ++reqId.current;

    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const res: Paginated<AdminActor> = await adminListActors({
          search: debouncedQ || undefined,
          tipo: (tipo || "") as any,
          page,
          page_size: pageSize,
        });

        const serverPaged =
          !!(res as any).next ||
          !!(res as any).prev ||
          (typeof res.count === "number" && res.count !== res.results.length);

        let rows: AdminActor[] = [];
        let total = 0;
        if (serverPaged) {
          rows = res.results ?? [];
          total = typeof res.count === "number" ? res.count : rows.length;
        } else {
          const all = res.results ?? [];
          total = all.length;
          const from = (page - 1) * pageSize;
          rows = all.slice(from, from + pageSize);
        }

        if (cancelled || myReq !== reqId.current) return;
        setDisplay(rows);
        setCount(total);
      } catch (e: any) {
        if (cancelled || myReq !== reqId.current) return;
        setErr(e?.message || "Error cargando actores");
        setDisplay([]);
        setCount(0);
      } finally {
        if (!cancelled && myReq === reqId.current) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [debouncedQ, tipo, page, pageSize, refreshKey]);

  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  const from = count === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(count, page * pageSize);

  const triggerReload = useCallback(() => {
    setRefreshKey((key) => key + 1);
  }, []);

  async function onDelete(id: string) {
    try {
      if (!confirm("¿Eliminar actor?")) return;
      await adminDeleteActor(id);
      toast("ok", "Actor eliminado");
      triggerReload();
    } catch (e: any) {
      toast("err", e?.message || "No se pudo eliminar");
    }
  }

  async function onEditSubmit(actor: AdminActor | Partial<AdminActor>) {
    if (!actor.id) return;
    try {
      await adminUpdateActor(actor.id, actor as AdminActor);
      toast("ok", "Actor actualizado");
      setEditing(null);
      triggerReload();
    } catch (e: any) {
      toast("err", e?.message || "No se pudo actualizar");
    }
  }

  async function onCreateSubmit(actor: Partial<AdminActor>) {
    try {
      await adminCreateActor(actor as any);
      toast("ok", "Actor creado");
      setCreating(false);
      setPage(1);
      triggerReload();
    } catch (e: any) {
      toast("err", e?.message || "No se pudo crear");
    }
  }

  return (
    <Section
      title="Actores"
      subtitle="Gestiona el catálogo de actores. Usa búsqueda y filtros para acotar resultados."
      actions={
        <div className="grid w-full grid-cols-2 md:grid-cols-6 gap-2">
          <div className="relative col-span-2 md:col-span-3">
            <SearchIcon />
            <input
              ref={searchRef}
              className={shell.input + " pl-9"}
              placeholder="Buscar por nombre/documento."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Buscar actores"
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 hidden md:block">
              <span className={shell.kbd}>Ctrl</span>
              <span className="mx-0.5">+</span>
              <span className={shell.kbd}>/</span>
            </div>
          </div>
          <select
            className={`${shell.select} col-span-1 md:col-span-2`}
            value={tipo}
            onChange={(e) => setTipo((e.target.value || "") as ActorTipo | "")}
            aria-label="Filtrar por tipo"
          >
            <option value="">Todos los tipos</option>
            <option value="PROVEEDOR">Proveedor</option>
            <option value="TRANSPORTISTA">Transportista</option>
            <option value="RECEPTOR">Receptor</option>
          </select>
          <select
            className={`${shell.select} col-span-1 md:col-span-1`}
            value={pageSize}
            onChange={(e) => setPageSize(Number(e.target.value))}
            aria-label="Elementos por página"
          >
            {[10, 25, 50, 100].map((n) => (
              <option key={n} value={n}>
                {n} / página
              </option>
            ))}
          </select>
          <button
            onClick={() => setCreating(true)}
            className={shell.btnPrimary + " col-span-2 md:col-span-1"}
          >
            Nuevo
          </button>
        </div>
      }
    >
      <div className={`${shell.card} overflow-hidden`}>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 px-4 py-3 border-b border-slate-100 dark:border-white/10">
          <div className="text-sm text-slate-600 dark:text-slate-300">
            {loading ? "Cargando." : `${from}-${to} de ${count}`}
          </div>
          <div className="flex items-center gap-2">
            <button
              className={shell.iconBtn}
              disabled={page <= 1 || loading}
              onClick={() => setPage(1)}
              title="Primera"
              aria-label="Primera página"
            >
              {"<<"}
            </button>
            <button
              className={shell.iconBtn}
              disabled={page <= 1 || loading}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              title="Anterior"
              aria-label="Página anterior"
            >
              {"<"}
            </button>
            <div className="flex items-center gap-2">
              <input
                className={`${shell.input} w-[74px] text-center`}
                type="number"
                min={1}
                max={totalPages}
                value={page}
                onChange={(e) => {
                  const v = Math.max(1, Math.min(totalPages, Number(e.target.value || 1)));
                  setPage(v);
                }}
                aria-label="Página"
              />
              <span className="text-sm text-slate-500 dark:text-slate-300">/ {totalPages}</span>
            </div>
            <button
              className={shell.iconBtn}
              disabled={page >= totalPages || loading}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              title="Siguiente"
              aria-label="Página siguiente"
            >
              {">"}
            </button>
            <button
              className={shell.iconBtn}
              disabled={page >= totalPages || loading}
              onClick={() => setPage(totalPages)}
              title="Última"
              aria-label="Última página"
            >
              {">>"}
            </button>
          </div>
        </div>

        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead className="sticky top-0 bg-white/90 dark:bg-slate-900/90 backdrop-blur">
              <tr className="border-b border-slate-100 dark:border-white/10">
                <th className={shell.th}>Nombre</th>
                <th className={shell.th}>Tipo</th>
                <th className={shell.th}>Documento</th>
                <th className={shell.th}>Estado</th>
                <th className={`${shell.th} w-[1%] whitespace-nowrap`}>Acciones</th>
              </tr>
            </thead>
            {loading ? (
              <SkeletonRows rows={8} />
            ) : display.length === 0 ? (
              <tbody>
                <tr>
                  <td colSpan={5} className={`${shell.td} text-center text-slate-500`}>
                    No hay actores.
                  </td>
                </tr>
              </tbody>
            ) : (
              <tbody>
                {display.map((a) => (
                  <tr
                    key={a.id}
                    className="border-b last:border-0 border-slate-100 dark:border-white/10"
                  >
                    <td className={shell.td}>{a.nombre}</td>
                    <td className={shell.td}>{a.tipo}</td>
                    <td className={shell.td}>{a.documento || "-"}</td>
                    <td className={shell.td}>
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs ${
                          a.activo
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200"
                            : "bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-slate-200"
                        }`}
                      >
                        {a.activo ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td className={shell.td}>
                      <div className="flex gap-2">
                        <button onClick={() => setEditing(a)} className={shell.btn}>
                          Editar
                        </button>
                        <button
                          onClick={() => onDelete(a.id)}
                          className={`${shell.btn} hover:bg-rose-50`}
                        >
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            )}
          </table>
        </div>
      </div>

      {editing && (
        <ActorModal
          actor={editing}
          onClose={() => setEditing(null)}
          onSubmit={onEditSubmit}
        />
      )}
      {creating && (
        <ActorModal
          actor={{ id: "", nombre: "", tipo: "PROVEEDOR", activo: true }}
          onClose={() => setCreating(false)}
          onSubmit={onCreateSubmit}
        />
      )}
    </Section>
  );
}

function ActorModal({
  actor,
  onClose,
  onSubmit,
}: {
  actor: Partial<AdminActor>;
  onClose: () => void;
  onSubmit: (actor: AdminActor | Partial<AdminActor>) => void;
}) {
  const [nombre, setNombre] = useState(actor.nombre ?? "");
  const [tipo, setTipo] = useState<ActorTipo>((actor.tipo as ActorTipo) || "PROVEEDOR");
  const [documento, setDocumento] = useState(actor.documento ?? "");
  const [activo, setActivo] = useState(actor.activo ?? true);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50"
      role="dialog"
      aria-modal="true"
      aria-label={actor.id ? "Editar actor" : "Nuevo actor"}
    >
      <div className="w-[380px] max-w-[92vw] p-7 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-white/10 shadow-2xl">
        <h3 className="text-lg font-semibold mb-4">
          {actor.id ? "Editar actor" : "Nuevo actor"}
        </h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({ ...actor, nombre, tipo, documento, activo });
          }}
          className="space-y-4"
        >
          <label className="block">
            <span className="text-sm">Nombre</span>
            <input
              className={shell.input}
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              required
            />
          </label>
          <label className="block">
            <span className="text-sm">Tipo</span>
            <select
              className={shell.select}
              value={tipo}
              onChange={(e) => setTipo(e.target.value as ActorTipo)}
            >
              <option value="PROVEEDOR">Proveedor</option>
              <option value="TRANSPORTISTA">Transportista</option>
              <option value="RECEPTOR">Receptor</option>
            </select>
          </label>
          <label className="block">
            <span className="text-sm">Documento</span>
            <input
              className={shell.input}
              value={documento}
              onChange={(e) => setDocumento(e.target.value)}
            />
          </label>
          <label className="inline-flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!activo}
              onChange={() => setActivo((v) => !v)}
            />
            Activo
          </label>
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" className={shell.btn} onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className={shell.btnPrimary}>
              Guardar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
