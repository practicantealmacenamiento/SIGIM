"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  // Formularios
  listQuestionnaires,
  getQuestionnaire,
  upsertQuestionnaire,
  duplicateQuestionnaire,
  deleteQuestionnaire,
  // Actores (ADMIN CRUD)
  adminListActors,
  adminCreateActor,
  adminUpdateActor,
  adminDeleteActor,
  // Usuarios
  listAdminUsers,
  upsertAdminUser,
  deleteAdminUser,
  // Auth
  clearAdminToken,
  // Tipos
  type AdminQuestionnaire,
  type Actor as AdminActor,
  type ActorTipo,
  type AdminUser,
} from "@/lib/api.admin";
import { CARD, INPUT } from "@/lib/ui";

function Section({
  title,
  children,
  actions,
}: {
  title: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <section className="mb-8">
      <div className="flex items-center justify-between gap-3 mb-4">
        <h2 className="text-xl font-semibold">{title}</h2>
        {actions}
      </div>
      {children}
    </section>
  );
}

function LoadingCard() {
  return (
    <li className={`${CARD} p-5 md:p-6 animate-pulse`}>
      <div className="flex items-center justify-between gap-4">
        <div className="space-y-2 w-full">
          <div className="h-5 w-64 rounded bg-slate-200/70 dark:bg-white/10" />
          <div className="h-4 w-40 rounded bg-slate-200/70 dark:bg-white/10" />
        </div>
        <div className="flex gap-2">
          <div className="h-10 w-20 rounded-xl bg-slate-200/70 dark:bg-white/10" />
          <div className="h-10 w-24 rounded-xl bg-slate-200/70 dark:bg-white/10" />
          <div className="h-10 w-24 rounded-xl bg-slate-200/70 dark:bg-white/10" />
        </div>
      </div>
    </li>
  );
}

/* -------------------- Pestaña: Formularios -------------------- */
function FormulariosPanel() {
  const router = useRouter();
  const [rows, setRows] = useState<{ id: string; title: string; version: string; questions: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const [filter, setFilter] = useState("");
  const [sortKey, setSortKey] = useState<"title" | "version" | "questions">("title");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    try {
      setErr(null);
      setLoading(true);
      const data = await listQuestionnaires();
      setRows(data);
    } catch (e: any) {
      setErr(e?.message || "Error listando");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  function newQuestionnaire() {
    const id = crypto.randomUUID();
    const qn: AdminQuestionnaire = {
      id,
      title: "Nuevo cuestionario",
      version: "v1",
      timezone: "America/Bogota",
      questions: [],
    };
    sessionStorage.setItem(`draft:${id}`, JSON.stringify(qn));
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
      const safeTitle = q.title.replace(/[^\w\-]+/g, "_");
      a.download = `${safeTitle}_${q.version}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(e?.message || "No se pudo exportar el cuestionario");
    }
  }

  function triggerImport() {
    fileRef.current?.click();
  }

  async function onImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text()) as AdminQuestionnaire;
      if (!parsed?.id || !parsed?.title || !parsed?.version || !Array.isArray(parsed?.questions)) {
        throw new Error("JSON inválido (debe incluir id, title, version, timezone, questions[])");
      }
      const saved = await upsertQuestionnaire(parsed);
      alert("Cuestionario importado");
      router.push(`/admin/${saved.id}`);
    } catch (e: any) {
      alert(e?.message || "No se pudo importar");
    }
  }

  function toggleSort(k: "title" | "version" | "questions") {
    if (k === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(k);
      setSortDir("asc");
    }
  }

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const base = !q ? rows : rows.filter((r) => r.title.toLowerCase().includes(q) || r.version.toLowerCase().includes(q));
    const sorted = [...base].sort((a, b) => {
      const mult = sortDir === "asc" ? 1 : -1;
      if (sortKey === "questions") return (a.questions - b.questions) * mult;
      const av = String(a[sortKey] ?? "").toLowerCase();
      const bv = String(b[sortKey] ?? "").toLowerCase();
      return av.localeCompare(bv) * mult;
    });
    return sorted;
  }, [rows, filter, sortKey, sortDir]);

  return (
    <Section
      title="Formularios"
      actions={
        <div className="flex items-center gap-2">
          <input
            className={`${INPUT} w-[240px]`}
            placeholder="Buscar por título/versión…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <button onClick={() => toggleSort("title")} className="px-3 py-1.5 rounded-lg border hover:bg-slate-50 dark:hover:bg-white/5">
            Título
          </button>
          <button onClick={() => toggleSort("version")} className="px-3 py-1.5 rounded-lg border hover:bg-slate-50 dark:hover:bg-white/5">
            Versión
          </button>
          <button
            onClick={() => toggleSort("questions")}
            className="px-3 py-1.5 rounded-lg border hover:bg-slate-50 dark:hover:bg-white/5"
          >
            Preguntas
          </button>
          <button onClick={triggerImport} className="px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5">
            Importar
          </button>
          <input ref={fileRef} type="file" accept="application/json,.json" className="hidden" onChange={onImportFile} />
          <button onClick={newQuestionnaire} className="min-h-[44px] px-4 py-2.5 rounded-xl bg-skyBlue text-white font-medium">
            Nuevo
          </button>
        </div>
      }
    >
      {loading ? (
        <ul className="grid gap-3">{Array.from({ length: 6 }).map((_, i) => <LoadingCard key={i} />)}</ul>
      ) : err ? (
        <div className={`${CARD} p-6 md:p-8 text-center`}>
          <p className="text-red-600 mb-3">{err}</p>
          <button
            onClick={load}
            className="px-4 py-2 rounded-xl bg-skyBlue text-white font-medium shadow hover:opacity-90 transition"
          >
            Reintentar
          </button>
        </div>
      ) : (
        <ul className="grid gap-3">
          {filtered.map((r) => (
            <li key={r.id} className={`${CARD} p-5 flex items-center justify-between gap-3`}>
              <div>
                <div className="text-lg font-medium">
                  {r.title} <span className="text-slate-500">({r.version})</span>
                </div>
                <div className="text-sm text-slate-600 dark:text-white/70">
                  {r.questions} pregunta{r.questions === 1 ? "" : "s"}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Link href={`/admin/${r.id}`} className="px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5">
                  Editar
                </Link>
                <button
                  onClick={() => onExport(r.id)}
                  className="px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
                >
                  Exportar
                </button>
                <button
                  onClick={() => onDuplicate(r.id)}
                  className="px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
                >
                  Duplicar
                </button>
                <button
                  onClick={() => onDelete(r.id)}
                  className="px-3 py-2 rounded-xl border hover:bg-red-50 dark:hover:bg-white/5"
                >
                  Eliminar
                </button>
              </div>
            </li>
          ))}
          {filtered.length === 0 && <li className={`${CARD} p-5`}>Sin resultados.</li>}
        </ul>
      )}
    </Section>
  );
}

/* -------------------- Pestaña: Actores (completo, editable, mismo diseño) -------------------- */
function ActoresPanel() {
  const [q, setQ] = useState("");
  const [tipo, setTipo] = useState<ActorTipo | "">("");
  const [items, setItems] = useState<AdminActor[]>([]);
  const [editing, setEditing] = useState<AdminActor | null>(null);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setErr(null);
    try {
      const data = await adminListActors({ search: q, tipo });
      setItems(data.results || []);
    } catch (e: any) {
      setErr(e?.message || "Error cargando actores");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, [q, tipo]);

  async function onDelete(id: string) {
    if (!confirm("¿Eliminar actor?")) return;
    await adminDeleteActor(id);
    load();
  }

  async function onEditSubmit(actor: AdminActor) {
    await adminUpdateActor(actor.id, actor);
    setEditing(null);
    load();
  }

  async function onCreateSubmit(actor: Partial<AdminActor>) {
    await adminCreateActor(actor as any);
    setCreating(false);
    load();
  }

  return (
    <Section
      title="Actores"
      actions={
        <div className="flex gap-2">
          <input
            className={INPUT}
            placeholder="Buscar…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <select
            className={`${INPUT} pr-8`}
            value={tipo}
            onChange={(e) => setTipo((e.target.value || "") as ActorTipo | "")}
          >
            <option value="">Todos</option>
            <option value="PROVEEDOR">Proveedor</option>
            <option value="TRANSPORTISTA">Transportista</option>
            <option value="RECEPTOR">Receptor</option>
          </select>
          <button
            onClick={() => setCreating(true)}
            className="min-h-[40px] px-4 py-2.5 rounded-xl bg-skyBlue text-white font-medium"
          >
            Nuevo
          </button>
        </div>
      }
    >
      {loading ? (
        <div className={CARD + " p-6 text-center"}>Cargando…</div>
      ) : err ? (
        <div className={CARD + " p-6 text-center text-red-600"}>{err}</div>
      ) : (
        <ul className="grid gap-3">
          {items.map((a) => (
            <li key={a.id} className={CARD + " p-5 flex items-center justify-between gap-3"}>
              <div>
                <div className="text-lg font-medium">{a.nombre}</div>
                <div className="text-sm text-slate-600 dark:text-white/70">
                  {a.tipo} • {a.documento || "Sin documento"} • {a.activo ? "Activo" : "Inactivo"}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setEditing(a)}
                  className="px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
                >
                  Editar
                </button>
                <button
                  onClick={() => onDelete(a.id)}
                  className="px-3 py-2 rounded-xl border hover:bg-red-50 dark:hover:bg-white/5"
                >
                  Eliminar
                </button>
              </div>
            </li>
          ))}
          {items.length === 0 && <li className={CARD + " p-5"}>No hay actores.</li>}
        </ul>
      )}

      {/* Modal edición */}
      {editing && (
        <ActorModal
          actor={editing}
          onClose={() => setEditing(null)}
          onSubmit={onEditSubmit}
        />
      )}

      {/* Modal creación */}
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
  const [tipo, setTipo] = useState<ActorTipo>(actor.tipo as ActorTipo || "PROVEEDOR");
  const [documento, setDocumento] = useState(actor.documento ?? "");
  const [activo, setActivo] = useState(actor.activo ?? true);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 w-[340px] shadow-lg">
        <h3 className="font-semibold text-xl mb-4">{actor.id ? "Editar actor" : "Nuevo actor"}</h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({ ...actor, nombre, tipo, documento, activo });
          }}
          className="space-y-4"
        >
          <label className="block">
            <span className="text-sm">Nombre</span>
            <input className={INPUT} value={nombre} onChange={(e) => setNombre(e.target.value)} required />
          </label>
          <label className="block">
            <span className="text-sm">Tipo</span>
            <select className={INPUT} value={tipo} onChange={(e) => setTipo(e.target.value as ActorTipo)}>
              <option value="PROVEEDOR">Proveedor</option>
              <option value="TRANSPORTISTA">Transportista</option>
              <option value="RECEPTOR">Receptor</option>
            </select>
          </label>
          <label className="block">
            <span className="text-sm">Documento</span>
            <input className={INPUT} value={documento} onChange={(e) => setDocumento(e.target.value)} />
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={!!activo} onChange={() => setActivo((a) => !a)} />
            <span className="text-sm">Activo</span>
          </label>
          <div className="flex gap-2 justify-end">
            <button type="button" className="px-3 py-2 rounded-xl border" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="px-3 py-2 rounded-xl bg-skyBlue text-white">
              Guardar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* -------------------- Pestaña: Usuarios (completo, editable, mismo diseño) -------------------- */
function UsuariosPanel() {
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setErr(null);
    try {
      const data = await listAdminUsers();
      setUsers(data);
    } catch (e: any) {
      setErr(e?.message || "Error cargando usuarios");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  async function onDelete(id: number) {
    if (!confirm("¿Eliminar usuario?")) return;
    await deleteAdminUser(id);
    load();
  }

  async function onEditSubmit(user: AdminUser) {
    await upsertAdminUser(user);
    setEditing(null);
    load();
  }

  async function onCreateSubmit(user: Partial<AdminUser>) {
    await upsertAdminUser(user as AdminUser);
    setCreating(false);
    load();
  }

  const rows = users || [];
  return (
    <Section
      title="Usuarios"
      actions={
        <div className="flex gap-2">
          <button
            onClick={() => setCreating(true)}
            className="min-h-[40px] px-4 py-2.5 rounded-xl bg-skyBlue text-white font-medium"
          >
            Nuevo
          </button>
        </div>
      }
    >
      {loading ? (
        <div className={CARD + " p-6 text-center"}>Cargando…</div>
      ) : err ? (
        <div className={CARD + " p-6 text-center text-red-600"}>{err}</div>
      ) : (
        <ul className="grid gap-3">
          {rows.map((u) => (
            <li key={u.id} className={CARD + " p-5 flex items-center justify-between gap-3"}>
              <div>
                <div className="text-lg font-medium">{u.username}</div>
                <div className="text-sm text-slate-600 dark:text-white/70">
                  {u.email || "Sin email"} • Staff: {u.is_staff ? "Sí" : "No"} • Activo: {u.is_active ? "Sí" : "No"}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setEditing(u)}
                  className="px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
                >
                  Editar
                </button>
                <button
                  onClick={() => onDelete(u.id!)}
                  className="px-3 py-2 rounded-xl border hover:bg-red-50 dark:hover:bg-white/5"
                >
                  Eliminar
                </button>
              </div>
            </li>
          ))}
          {rows.length === 0 && <li className={CARD + " p-5"}>No hay usuarios.</li>}
        </ul>
      )}

      {/* Modal edición */}
      {editing && (
        <UserModal
          user={editing}
          onClose={() => setEditing(null)}
          onSubmit={onEditSubmit}
        />
      )}

      {/* Modal creación */}
      {creating && (
        <UserModal
          user={{
            id: undefined,
            username: "",
            email: "",
            is_staff: false,
            is_superuser: false,
            is_active: true,
            password: "",
          }}
          onClose={() => setCreating(false)}
          onSubmit={onCreateSubmit}
        />
      )}
    </Section>
  );
}

function UserModal({
  user,
  onClose,
  onSubmit,
}: {
  user: Partial<AdminUser>;
  onClose: () => void;
  onSubmit: (user: AdminUser | Partial<AdminUser>) => void;
}) {
  const [username, setUsername] = useState(user.username ?? "");
  const [email, setEmail] = useState(user.email ?? "");
  const [is_staff, setStaff] = useState(user.is_staff ?? false);
  const [is_superuser, setSuper] = useState(user.is_superuser ?? false);
  const [is_active, setActive] = useState(user.is_active ?? true);
  const [password, setPassword] = useState(user.password ?? "");

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 w-[340px] shadow-lg">
        <h3 className="font-semibold text-xl mb-4">{user.id ? "Editar usuario" : "Nuevo usuario"}</h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({ ...user, username, email, is_staff, is_superuser, is_active, password });
          }}
          className="space-y-4"
        >
          <label className="block">
            <span className="text-sm">Usuario</span>
            <input className={INPUT} value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label className="block">
            <span className="text-sm">Email</span>
            <input className={INPUT} type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={!!is_staff} onChange={() => setStaff((v) => !v)} />
            <span className="text-sm">Staff</span>
            <input type="checkbox" checked={!!is_superuser} onChange={() => setSuper((v) => !v)} className="ml-4" />
            <span className="text-sm">Superuser</span>
            <input type="checkbox" checked={!!is_active} onChange={() => setActive((v) => !v)} className="ml-4" />
            <span className="text-sm">Activo</span>
          </label>
          <label className="block">
            <span className="text-sm">Contraseña</span>
            <input
              className={INPUT}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              placeholder={user.id ? "(Dejar vacío para no cambiar)" : ""}
            />
          </label>
          <div className="flex gap-2 justify-end">
            <button type="button" className="px-3 py-2 rounded-xl border" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="px-3 py-2 rounded-xl bg-skyBlue text-white">
              Guardar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* -------------------- PÁGINA PRINCIPAL ADMIN -------------------- */
export default function AdminGeneralPage() {
  const router = useRouter();
  const [tab, setTab] = useState<"formularios" | "actores" | "usuarios">("formularios");

  function logout() {
    if (!confirm("¿Cerrar sesión de administrador?")) return;
    clearAdminToken();
    router.refresh();
  }

  return (
    <main className="min-h-[calc(100vh-80px)] w-full px-6 md:px-8 py-8">
      <div className="mx-auto max-w-[1150px]">
        <div className="flex items-center justify-between gap-3 mb-6">
          <h1 className="text-3xl font-semibold">Administración</h1>
          <div className="flex items-center gap-2">
            <nav className="flex gap-1 rounded-2xl p-1 border bg-white dark:bg-slate-900 border-slate-200/70 dark:border-white/10">
              <button
                onClick={() => setTab("formularios")}
                className={`px-4 py-2 rounded-xl ${tab === "formularios" ? "bg-slate-100 dark:bg-white/10" : ""}`}
              >
                Formularios
              </button>
              <button
                onClick={() => setTab("actores")}
                className={`px-4 py-2 rounded-xl ${tab === "actores" ? "bg-slate-100 dark:bg-white/10" : ""}`}
              >
                Actores
              </button>
              <button
                onClick={() => setTab("usuarios")}
                className={`px-4 py-2 rounded-xl ${tab === "usuarios" ? "bg-slate-100 dark:bg-white/10" : ""}`}
              >
                Usuarios
              </button>
            </nav>
            <button onClick={logout} className="px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5" title="Cerrar sesión">
              Cerrar sesión
            </button>
          </div>
        </div>

        {tab === "formularios" && <FormulariosPanel />}
        {tab === "actores" && <ActoresPanel />}
        {tab === "usuarios" && <UsuariosPanel />}
      </div>
    </main>
  );
}
