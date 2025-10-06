"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  // Auth
  isAuthenticated,
  clearAuthToken,
  // Formularios
  listQuestionnaires,
  getQuestionnaire,
  upsertQuestionnaire,
  duplicateQuestionnaire,
  deleteQuestionnaire,
  // Actores (con paginación)
  adminListActors,
  adminCreateActor,
  adminUpdateActor,
  adminDeleteActor,
  // Usuarios
  listAdminUsers,
  upsertAdminUser,
  deleteAdminUser,
  // Tipos
  type AdminQuestionnaire,
  type Actor as AdminActor,
  type ActorTipo,
  type AdminUser,
  type Paginated,
} from "@/lib/api.admin";

/* ===================== Tokens de estilo ===================== */
const shell = {
  page: "min-h-[calc(100vh-80px)] w-full bg-gradient-to-b from-slate-50 to-white dark:from-[#0b1220] dark:to-[#0b1220]",
  container: "mx-auto max-w-[1200px] px-6 md:px-8 py-8",
  card: "rounded-2xl border border-slate-200/70 dark:border-white/10 bg-white/90 dark:bg-slate-900/90 shadow-lg backdrop-blur supports-[backdrop-filter]:bg-white/60 supports-[backdrop-filter]:dark:bg-slate-900/60",
  input: "w-full h-11 px-10 rounded-xl border border-slate-200/70 dark:border-white/10 bg-white dark:bg-slate-950 text-sm outline-none focus:ring-2 focus:ring-sky-300 dark:focus:ring-sky-600",
  select: "w-full h-11 px-3 rounded-xl border border-slate-200/70 dark:border-white/10 bg-white dark:bg-slate-950 text-sm outline-none focus:ring-2 focus:ring-sky-300 dark:focus:ring-sky-600",
  btn: "px-3 py-2 rounded-xl border border-slate-200/70 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 transition",
  btnPrimary: "px-4 py-2.5 rounded-xl bg-sky-600 text-white font-medium shadow-sm hover:bg-sky-700 transition",
  iconBtn: "inline-flex items-center justify-center h-10 w-10 rounded-xl border border-slate-200/70 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 transition",
  pillTabs: "flex gap-1 rounded-2xl p-1 border bg-white/80 dark:bg-slate-900/80 border-slate-200/70 dark:border-white/10 shadow-sm",
  pill: (active: boolean) =>
    `px-4 py-2 rounded-xl text-sm ${active ? "bg-slate-100 dark:bg-white/10 font-medium" : "hover:bg-slate-50 dark:hover:bg-white/5"}`,
  th: "px-4 py-3 font-semibold text-slate-600 dark:text-slate-300 text-xs uppercase tracking-wide",
  td: "px-4 py-3 text-sm",
  kbd: "inline-flex items-center gap-1 rounded-md px-1.5 py-[2px] text-[11px] font-medium border border-slate-200/70 dark:border-white/10 bg-slate-50 dark:bg-white/5",
};

function SearchIcon() {
  return (
    <svg className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 opacity-60" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M15.5 14h-.79l-.28-.27A6.5 6.5 0 1 0 14 15.5l.27.28v.79l5 5 1.5-1.5-5-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z" />
    </svg>
  );
}

/* ===================== Utilities ===================== */
function useDebounced<T>(value: T, delay = 350) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

function Section({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-5">
      {/* Grid: en lg dividimos en [títulos | acciones]; en móviles se apila */}
      <div className="mb-3 grid gap-1 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
          {subtitle && <p className="text-sm text-slate-500 dark:text-slate-300">{subtitle}</p>}
        </div>
        {/* Limite de ancho para evitar que “empuje” */}
        {actions && <div className="w-full lg:w-auto max-w-[720px]">{actions}</div>}
      </div>
      {children}
    </section>
  );
}

function SkeletonRows({ rows = 6 }: { rows?: number }) {
  return (
    <tbody>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i} className="border-b border-slate-100 dark:border-white/10 animate-pulse">
          <td className={`${shell.td}`} colSpan={6}>
            <div className="h-6 rounded bg-slate-100 dark:bg-white/10" />
          </td>
        </tr>
      ))}
    </tbody>
  );
}

/* ===================== Formularios ===================== */
function FormulariosPanel() {
  const router = useRouter();
  const [rows, setRows] = useState<{ id: string; title: string; version: string; questions: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const debounced = useDebounced(query, 250);

  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    try {
      setErr(null);
      setLoading(true);
      const data = await listQuestionnaires();
      setRows(data);
    } catch (e: any) {
      setErr(e?.message || "Error listando cuestionarios");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  function newQuestionnaire() {
    const id = crypto.randomUUID();
    const q: AdminQuestionnaire = { id, title: "Nuevo cuestionario", version: "v1", timezone: "America/Bogota", questions: [] };
    sessionStorage.setItem(`draft:${id}`, JSON.stringify(q));
    router.push(`/admin/${id}`);
  }
  async function onDuplicate(id: string) {
    const v = prompt("Nueva versión (opcional):") || undefined;
    const res = await duplicateQuestionnaire(id, v);
    router.push(`/admin/${res.id}`);
  }
  async function onDelete(id: string) {
    if (!confirm("¿Eliminar definitivamente este cuestionario?")) return;
    await deleteQuestionnaire(id);
    load();
  }
  async function onExport(id: string) {
    try {
      const q = await getQuestionnaire(id);
      const blob = new Blob([JSON.stringify(q, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${q.title.replace(/[^\w\-]+/g, "_")}_${q.version}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(e?.message || "No se pudo exportar");
    }
  }
  function triggerImport() { fileRef.current?.click(); }
  async function onImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; e.target.value = "";
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text()) as AdminQuestionnaire;
      if (!parsed?.id || !parsed?.title || !parsed?.version || !Array.isArray(parsed?.questions)) {
        throw new Error("JSON inválido (requiere id, title, version, questions[])");
      }
      const saved = await upsertQuestionnaire(parsed);
      alert("Cuestionario importado");
      router.push(`/admin/${saved.id}`);
    } catch (e: any) {
      alert(e?.message || "No se pudo importar");
    }
  }

  const filtered = useMemo(() => {
    const q = debounced.trim().toLowerCase();
    return !q
      ? rows
      : rows.filter((r) => r.title.toLowerCase().includes(q) || r.version.toLowerCase().includes(q));
  }, [rows, debounced]);

  return (
    <Section
      title="Formularios"
      subtitle="Crea, edita, duplica e importa/exporta cuestionarios."
      actions={
  <div className="grid w-full grid-cols-2 md:grid-cols-5 gap-2">
    <div className="relative col-span-2 md:col-span-3">
      <SearchIcon />
      <input
        className={shell.input + " pl-9"}
        placeholder="Buscar por título/versión…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Buscar cuestionarios"
      />
    </div>
    <button onClick={triggerImport} className={shell.btn + " col-span-1"}>Importar</button>
    <button onClick={newQuestionnaire} className={shell.btnPrimary + " col-span-1"}>Nuevo</button>
    <input ref={fileRef} type="file" accept="application/json,.json" className="hidden" onChange={onImportFile} />
  </div>
}
    >
      <div className={`${shell.card} divide-y divide-slate-100 dark:divide-white/10`}>
        <div className="p-4">
          {err && (
            <div className="rounded-xl border border-rose-200/70 dark:border-rose-900/40 bg-rose-50/60 dark:bg-rose-950/30 text-rose-800 dark:text-rose-200 p-4 mb-3">
              {err} <button onClick={load} className="underline ml-2">Reintentar</button>
            </div>
          )}

          {loading ? (
            <ul className="grid gap-3">{Array.from({ length: 4 }).map((_, i) => (
              <li key={i} className="p-5 rounded-xl border border-slate-100 dark:border-white/10 bg-slate-50/60 dark:bg-white/5 animate-pulse h-[84px]" />
            ))}</ul>
          ) : filtered.length === 0 ? (
            <div className="text-sm text-slate-500 py-6">No hay cuestionarios.</div>
          ) : (
            <ul className="grid gap-3">
              {filtered.map((r) => (
                <li key={r.id} className="p-5 rounded-xl border border-slate-100 dark:border-white/10 bg-white dark:bg-slate-900 flex items-center justify-between">
                  <div className="min-w-0">
                    <div className="text-base font-medium truncate">
                      {r.title} <span className="text-slate-500">({r.version})</span>
                    </div>
                    <div className="text-sm text-slate-600 dark:text-white/70">
                      {r.questions} pregunta{r.questions === 1 ? "" : "s"}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Link href={`/admin/${r.id}`} className={shell.btn}>Editar</Link>
                    <button onClick={() => onExport(r.id)} className={shell.btn}>Exportar</button>
                    <button onClick={() => onDuplicate(r.id)} className={shell.btn}>Duplicar</button>
                    <button onClick={() => onDelete(r.id)} className={`${shell.btn} hover:bg-rose-50`}>Eliminar</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Section>
  );
}

/* ===================== Actores (paginación PRO) ===================== */
function ActoresPanel() {
  const [query, setQuery] = useState("");
  const debouncedQ = useDebounced(query, 350);
  const [tipo, setTipo] = useState<ActorTipo | "">("");
  const [pageSize, setPageSize] = useState(25);
  const [page, setPage] = useState(1);

  const [display, setDisplay] = useState<AdminActor[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const [editing, setEditing] = useState<AdminActor | null>(null);
  const [creating, setCreating] = useState(false);

  // control de carrera
  const reqId = useRef(0);

  // reset a primera página al cambiar filtros
  useEffect(() => { setPage(1); }, [debouncedQ, tipo, pageSize]);

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

        // ¿server-side paging?
        const serverPaged = !!res.next || !!res.prev || (typeof res.count === "number" && res.count !== res.results.length);

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

    return () => { cancelled = true; };
  }, [debouncedQ, tipo, page, pageSize]);

  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  const from = count === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(count, page * pageSize);

  async function onDelete(id: string) {
    if (!confirm("¿Eliminar actor?")) return;
    await adminDeleteActor(id);
    setPage((p) => p); // recarga con los mismos filtros
  }
  async function onEditSubmit(actor: AdminActor | Partial<AdminActor>) {
    if (!actor.id) return;
    await adminUpdateActor(actor.id, actor as AdminActor);
    setEditing(null);
    setPage((p) => p);
  }
  async function onCreateSubmit(actor: Partial<AdminActor>) {
    await adminCreateActor(actor as any);
    setCreating(false);
    setPage(1);
  }

  return (
    <Section
      title="Actores"
      subtitle="Gestiona el catálogo de actores. Usa búsqueda y filtros para acotar resultados."
      actions={
  <div className="grid w-full grid-cols-2 md:grid-cols-6 gap-2">
    {/* Buscador: ocupa 2 cols en móvil, 3 en md */}
    <div className="relative col-span-2 md:col-span-3">
      <SearchIcon />
      <input
        className={shell.input + " pl-9"}
        placeholder="Buscar por nombre/documento…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Buscar actores"
      />
    </div>
    {/* Filtro tipo: 1 col móvil, 2 en md */}
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
    {/* Page size: 1 col */}
    <select
      className={`${shell.select} col-span-1 md:col-span-1`}
      value={pageSize}
      onChange={(e) => setPageSize(Number(e.target.value))}
      aria-label="Elementos por página"
    >
      {[10, 25, 50, 100].map((n) => (
        <option key={n} value={n}>{n} / página</option>
      ))}
    </select>
    {/* Botón: 2 cols en móvil (full), 1 en md */}
    <button onClick={() => setCreating(true)} className={shell.btnPrimary + " col-span-2 md:col-span-1"}>
      Nuevo
    </button>
  </div>
}
    >
      <div className={`${shell.card} overflow-hidden`}>
        {/* Toolbar de paginación */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 px-4 py-3 border-b border-slate-100 dark:border-white/10">
          <div className="text-sm text-slate-600 dark:text-slate-300">{loading ? "Cargando…" : `${from}–${to} de ${count}`}</div>
          <div className="flex items-center gap-2">
            <button className={shell.iconBtn} disabled={page <= 1 || loading} onClick={() => setPage(1)} title="Primera">«</button>
            <button className={shell.iconBtn} disabled={page <= 1 || loading} onClick={() => setPage((p) => Math.max(1, p - 1))} title="Anterior">‹</button>
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
            <button className={shell.iconBtn} disabled={page >= totalPages || loading} onClick={() => setPage((p) => Math.min(totalPages, p + 1))} title="Siguiente">›</button>
            <button className={shell.iconBtn} disabled={page >= totalPages || loading} onClick={() => setPage(totalPages)} title="Última">»</button>
          </div>
        </div>

        {/* Tabla */}
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
              <tbody><tr><td colSpan={5} className={`${shell.td} text-center text-slate-500`}>No hay actores.</td></tr></tbody>
            ) : (
              <tbody>
                {display.map((a) => (
                  <tr key={a.id} className="border-b last:border-0 border-slate-100 dark:border-white/10">
                    <td className={shell.td}>{a.nombre}</td>
                    <td className={shell.td}>{a.tipo}</td>
                    <td className={shell.td}>{a.documento || "—"}</td>
                    <td className={shell.td}>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs ${a.activo ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200" : "bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-slate-200"}`}>
                        {a.activo ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td className={shell.td}>
                      <div className="flex gap-2">
                        <button onClick={() => setEditing(a)} className={shell.btn}>Editar</button>
                        <button onClick={() => onDelete(a.id)} className={`${shell.btn} hover:bg-rose-50`}>Eliminar</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            )}
          </table>
        </div>
      </div>

      {/* Modales */}
      {editing && <ActorModal actor={editing} onClose={() => setEditing(null)} onSubmit={onEditSubmit} />}
      {creating && <ActorModal actor={{ id: "", nombre: "", tipo: "PROVEEDOR", activo: true }} onClose={() => setCreating(false)} onSubmit={onCreateSubmit} />}
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
  const [tipo, setTipo] = useState<ActorTipo>(actor.tipo as ActorTipo || "PROVEEDOR");
  const [documento, setDocumento] = useState(actor.documento ?? "");
  const [activo, setActivo] = useState(actor.activo ?? true);

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="w-[380px] max-w-[92vw] p-7 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-white/10 shadow-2xl">
        <h3 className="text-lg font-semibold mb-4">{actor.id ? "Editar actor" : "Nuevo actor"}</h3>
        <form
          onSubmit={(e) => { e.preventDefault(); onSubmit({ ...actor, nombre, tipo, documento, activo }); }}
          className="space-y-4"
        >
          <label className="block">
            <span className="text-sm">Nombre</span>
            <input className={shell.input} value={nombre} onChange={(e) => setNombre(e.target.value)} required />
          </label>
          <label className="block">
            <span className="text-sm">Tipo</span>
            <select className={shell.select} value={tipo} onChange={(e) => setTipo(e.target.value as ActorTipo)}>
              <option value="PROVEEDOR">Proveedor</option>
              <option value="TRANSPORTISTA">Transportista</option>
              <option value="RECEPTOR">Receptor</option>
            </select>
          </label>
          <label className="block">
            <span className="text-sm">Documento</span>
            <input className={shell.input} value={documento} onChange={(e) => setDocumento(e.target.value)} />
          </label>
          <label className="inline-flex items-center gap-2">
            <input type="checkbox" checked={!!activo} onChange={() => setActivo((a) => !a)} />
            <span className="text-sm">Activo</span>
          </label>
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" className={shell.btn} onClick={onClose}>Cancelar</button>
            <button type="submit" className={shell.btnPrimary}>Guardar</button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ===================== Usuarios ===================== */
function UsuariosPanel() {
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    setLoading(true); setErr(null);
    try { setUsers(await listAdminUsers()); }
    catch (e: any) { setErr(e?.message || "Error cargando usuarios"); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  async function onDelete(id: number) { if (confirm("¿Eliminar usuario?")) { await deleteAdminUser(id); load(); } }
  async function onEditSubmit(u: AdminUser | Partial<AdminUser>) { if (!u.username) return; await upsertAdminUser(u as AdminUser); setEditing(null); load(); }
  async function onCreateSubmit(u: Partial<AdminUser>) { await upsertAdminUser(u as AdminUser); setCreating(false); load(); }

  const rows = users || [];

  return (
    <Section
      title="Usuarios"
      subtitle="Crea y gestiona usuarios de administración."
      actions={<button onClick={() => setCreating(true)} className={shell.btnPrimary}>Nuevo</button>}
    >
      <div className={`${shell.card} overflow-hidden`}>
        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead className="sticky top-0 bg-white/90 dark:bg-slate-900/90 backdrop-blur">
              <tr className="border-b border-slate-100 dark:border-white/10">
                <th className={shell.th}>Usuario</th>
                <th className={shell.th}>Email</th>
                <th className={shell.th}>Staff</th>
                <th className={shell.th}>Activo</th>
                <th className={`${shell.th} w-[1%] whitespace-nowrap`}>Acciones</th>
              </tr>
            </thead>
            {loading ? (
              <SkeletonRows rows={6} />
            ) : err ? (
              <tbody><tr><td colSpan={5} className={`${shell.td} text-center text-rose-600`}>{err}</td></tr></tbody>
            ) : rows.length === 0 ? (
              <tbody><tr><td colSpan={5} className={`${shell.td} text-center text-slate-500`}>No hay usuarios.</td></tr></tbody>
            ) : (
              <tbody>
                {rows.map((u) => (
                  <tr key={u.id} className="border-b last:border-0 border-slate-100 dark:border-white/10">
                    <td className={shell.td}>{u.username}</td>
                    <td className={shell.td}>{u.email || "—"}</td>
                    <td className={shell.td}>{u.is_staff ? "Sí" : "No"}</td>
                    <td className={shell.td}>{u.is_active ? "Sí" : "No"}</td>
                    <td className={shell.td}>
                      <div className="flex gap-2">
                        <button onClick={() => setEditing(u)} className={shell.btn}>Editar</button>
                        <button onClick={() => onDelete(u.id!)} className={`${shell.btn} hover:bg-rose-50`}>Eliminar</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            )}
          </table>
        </div>
      </div>

      {editing && <UserModal user={editing} onClose={() => setEditing(null)} onSubmit={onEditSubmit} />}
      {creating && <UserModal user={{ id: undefined, username: "", email: "", is_staff: false, is_superuser: false, is_active: true, password: "" }} onClose={() => setCreating(false)} onSubmit={onCreateSubmit} />}
    </Section>
  );
}

function UserModal({
  user, onClose, onSubmit,
}: { user: Partial<AdminUser>; onClose: () => void; onSubmit: (user: AdminUser | Partial<AdminUser>) => void; }) {
  const [username, setUsername] = useState(user.username ?? "");
  const [email, setEmail] = useState(user.email ?? "");
  const [is_staff, setStaff] = useState(user.is_staff ?? false);
  const [is_superuser, setSuper] = useState(user.is_superuser ?? false);
  const [is_active, setActive] = useState(user.is_active ?? true);
  const [password, setPassword] = useState(user.password ?? "");

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="w-[380px] max-w-[92vw] p-7 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-white/10 shadow-2xl">
        <h3 className="text-lg font-semibold mb-4">{user.id ? "Editar usuario" : "Nuevo usuario"}</h3>
        <form
          onSubmit={(e) => { e.preventDefault(); onSubmit({ ...user, username, email, is_staff, is_superuser, is_active, password }); }}
          className="space-y-4"
        >
          <label className="block">
            <span className="text-sm">Usuario</span>
            <input className={shell.input} value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label className="block">
            <span className="text-sm">Email</span>
            <input className={shell.input} type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <div className="flex items-center gap-4 flex-wrap">
            <label className="inline-flex items-center gap-2">
              <input type="checkbox" checked={!!is_staff} onChange={() => setStaff((v) => !v)} />
              <span className="text-sm">Staff</span>
            </label>
            <label className="inline-flex items-center gap-2">
              <input type="checkbox" checked={!!is_superuser} onChange={() => setSuper((v) => !v)} />
              <span className="text-sm">Superuser</span>
            </label>
            <label className="inline-flex items-center gap-2">
              <input type="checkbox" checked={!!is_active} onChange={() => setActive((v) => !v)} />
              <span className="text-sm">Activo</span>
            </label>
          </div>
          <label className="block">
            <span className="text-sm">Contraseña</span>
            <input className={shell.input} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" placeholder={user.id ? "(Dejar vacío para no cambiar)" : ""} />
          </label>
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" className={shell.btn} onClick={onClose}>Cancelar</button>
            <button type="submit" className={shell.btnPrimary}>Guardar</button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ===================== Página principal ===================== */
export default function AdminGeneralPage() {
  const router = useRouter();
  const [tab, setTab] = useState<"formularios" | "actores" | "usuarios">("formularios");

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace(`/login?next=${encodeURIComponent("/admin")}`);
    }
  }, [router]);

  function logout() {
    if (!confirm("¿Cerrar sesión?")) return;
    clearAuthToken();
    router.replace("/login");
  }

  return (
    <main className={shell.page}>
      <div className={shell.container}>
        <div className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Administración</h1>
            <p className="text-sm text-slate-500 dark:text-slate-300">Gestión de formularios, actores y usuarios.</p>
          </div>
          <div className="flex items-center gap-2">
            <nav className={shell.pillTabs} role="tablist" aria-label="Secciones">
              <button role="tab" aria-selected={tab === "formularios"} className={shell.pill(tab === "formularios")} onClick={() => setTab("formularios")}>Formularios</button>
              <button role="tab" aria-selected={tab === "actores"} className={shell.pill(tab === "actores")} onClick={() => setTab("actores")}>Actores</button>
              <button role="tab" aria-selected={tab === "usuarios"} className={shell.pill(tab === "usuarios")} onClick={() => setTab("usuarios")}>Usuarios</button>
            </nav>
            <button onClick={logout} className={shell.btn} title="Cerrar sesión">Cerrar sesión</button>
          </div>
        </div>

        {tab === "formularios" && <FormulariosPanel />}
        {tab === "actores" && <ActoresPanel />}
        {tab === "usuarios" && <UsuariosPanel />}
      </div>
    </main>
  );
}
