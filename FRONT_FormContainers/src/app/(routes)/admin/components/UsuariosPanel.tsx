import { useCallback, useEffect, useState } from "react";

import {
  deleteAdminUser,
  listAdminUsers,
  upsertAdminUser,
  type AdminUser,
} from "@/lib/api.admin";

import { shell, Section, SkeletonRows } from "./ui";
import type { ToastPush } from "./toasts";

type Props = {
  toast: ToastPush;
};

export function UsuariosPanel({ toast }: Props) {
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      setUsers(await listAdminUsers());
    } catch (e: any) {
      setErr(e?.message || "Error cargando usuarios");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onDelete(id: number) {
    try {
      if (confirm("¿Eliminar usuario?")) {
        await deleteAdminUser(id);
        toast("ok", "Usuario eliminado");
        load();
      }
    } catch (e: any) {
      toast("err", e?.message || "No se pudo eliminar");
    }
  }

  async function onEditSubmit(u: AdminUser | Partial<AdminUser>) {
    try {
      if (!u.username) return;
      await upsertAdminUser(u as AdminUser);
      toast("ok", "Usuario actualizado");
      setEditing(null);
      load();
    } catch (e: any) {
      toast("err", e?.message || "No se pudo actualizar");
    }
  }

  async function onCreateSubmit(u: Partial<AdminUser>) {
    try {
      await upsertAdminUser(u as AdminUser);
      toast("ok", "Usuario creado");
      setCreating(false);
      load();
    } catch (e: any) {
      toast("err", e?.message || "No se pudo crear");
    }
  }

  const rows = users || [];

  return (
    <Section
      title="Usuarios"
      subtitle="Crea y gestiona usuarios de administración."
      actions={
        <button onClick={() => setCreating(true)} className={shell.btnPrimary}>
          Nuevo
        </button>
      }
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
              <tbody>
                <tr>
                  <td colSpan={5} className={`${shell.td} text-center text-rose-600`}>
                    {err}
                  </td>
                </tr>
              </tbody>
            ) : rows.length === 0 ? (
              <tbody>
                <tr>
                  <td colSpan={5} className={`${shell.td} text-center text-slate-500`}>
                    No hay usuarios.
                  </td>
                </tr>
              </tbody>
            ) : (
              <tbody>
                {rows.map((u) => (
                  <tr
                    key={u.id}
                    className="border-b last:border-0 border-slate-100 dark:border-white/10"
                  >
                    <td className={shell.td}>{u.username}</td>
                    <td className={shell.td}>{u.email || "-"}</td>
                    <td className={shell.td}>{u.is_staff ? "Sí" : "No"}</td>
                    <td className={shell.td}>{u.is_active ? "Sí" : "No"}</td>
                    <td className={shell.td}>
                      <div className="flex gap-2">
                        <button onClick={() => setEditing(u)} className={shell.btn}>
                          Editar
                        </button>
                        <button
                          onClick={() => onDelete(u.id!)}
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
        <UserModal
          user={editing}
          onClose={() => setEditing(null)}
          onSubmit={onEditSubmit}
        />
      )}
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
      aria-label={user.id ? "Editar usuario" : "Nuevo usuario"}
    >
      <div className="w-[380px] max-w-[92vw] p-7 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-white/10 shadow-2xl">
        <h3 className="text-lg font-semibold mb-4">
          {user.id ? "Editar usuario" : "Nuevo usuario"}
        </h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({
              ...user,
              username,
              email,
              is_staff,
              is_superuser,
              is_active,
              password: password || undefined,
            });
          }}
          className="space-y-4"
        >
          <label className="block">
            <span className="text-sm">Usuario</span>
            <input
              className={shell.input}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </label>
          <label className="block">
            <span className="text-sm">Email</span>
            <input
              className={shell.input}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={!!is_staff}
                onChange={() => setStaff((v) => !v)}
              />
              <span className="text-sm">Staff</span>
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={!!is_superuser}
                onChange={() => setSuper((v) => !v)}
              />
              <span className="text-sm">Superuser</span>
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={!!is_active}
                onChange={() => setActive((v) => !v)}
              />
              <span className="text-sm">Activo</span>
            </label>
          </div>
          <label className="block">
            <span className="text-sm">Contraseña</span>
            <input
              className={shell.input}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              placeholder={user.id ? "(Dejar vacío para no cambiar)" : ""}
            />
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
