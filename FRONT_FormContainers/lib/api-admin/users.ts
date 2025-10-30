/**
 * Operaciones del módulo de usuarios administrativos.
 * Mantiene la lógica de list, upsert y delete.
 */
import { ADMIN_MGMT_PREFIX, ADMIN_PREFIX } from "./constants";
import { apiTry } from "./client";
import type { AdminUser } from "./types";

export async function listAdminUsers(): Promise<AdminUser[]> {
  const data = await apiTry<any>([
    `${ADMIN_MGMT_PREFIX}/users/`,
    `${ADMIN_MGMT_PREFIX}/usuarios/`,
    `${ADMIN_PREFIX}/users/`,
    `${ADMIN_PREFIX}/usuarios/`,
  ]);

  const rows: any[] = Array.isArray(data) ? data : data?.results ?? [];
  return rows.map((u) => ({
    id: u.id,
    username: u.username ?? u.user ?? "",
    email: u.email ?? "",
    is_staff: !!(u.is_staff ?? u.staff ?? u.is_admin),
    is_superuser: !!u.is_superuser,
    is_active: !!(u.is_active ?? u.active ?? true),
  }));
}

export async function upsertAdminUser(user: Partial<AdminUser>) {
  const hasId = !!user.id;
  const payload: any = {
    ...(user.username !== undefined ? { username: user.username } : {}),
    ...(user.email !== undefined ? { email: user.email } : {}),
    ...(user.is_staff !== undefined
      ? { is_staff: !!user.is_staff, staff: !!user.is_staff }
      : {}),
    ...(user.is_superuser !== undefined
      ? { is_superuser: !!user.is_superuser }
      : {}),
    ...(user.is_active !== undefined
      ? { is_active: !!user.is_active, active: !!user.is_active }
      : {}),
  };
  if (user.password && user.password.trim() !== "") {
    payload.password = user.password;
  }

  const urlCandidates = hasId
    ? [
        `${ADMIN_MGMT_PREFIX}/users/${user.id}/`,
        `${ADMIN_MGMT_PREFIX}/usuarios/${user.id}/`,
        `${ADMIN_PREFIX}/users/${user.id}/`,
        `${ADMIN_PREFIX}/usuarios/${user.id}/`,
      ]
    : [
        `${ADMIN_MGMT_PREFIX}/users/`,
        `${ADMIN_MGMT_PREFIX}/usuarios/`,
        `${ADMIN_PREFIX}/users/`,
        `${ADMIN_PREFIX}/usuarios/`,
      ];

  const method = hasId ? "PATCH" : "POST";
  const saved = await apiTry<any>(urlCandidates, {
    method,
    body: JSON.stringify(payload),
  });

  return {
    id: saved.id,
    username: saved.username ?? saved.user ?? "",
    email: saved.email ?? "",
    is_staff: !!(saved.is_staff ?? saved.staff ?? saved.is_admin),
    is_superuser: !!saved.is_superuser,
    is_active: !!(saved.is_active ?? saved.active ?? true),
  } as AdminUser;
}

export async function deleteAdminUser(id: number) {
  await apiTry<void>(
    [
      `${ADMIN_MGMT_PREFIX}/users/${id}/`,
      `${ADMIN_MGMT_PREFIX}/usuarios/${id}/`,
      `${ADMIN_PREFIX}/users/${id}/`,
      `${ADMIN_PREFIX}/usuarios/${id}/`,
    ],
    { method: "DELETE" }
  );
}



