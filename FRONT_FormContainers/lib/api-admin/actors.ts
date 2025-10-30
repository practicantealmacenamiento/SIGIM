/**
 * Operaciones de actores con paginación, normalización y CRUD.
 */
import { ADMIN_MGMT_PREFIX, ADMIN_PREFIX } from "./constants";
import { apiTry, toQuery } from "./client";
import type { Actor, ActorTipo, Paginated } from "./types";

function normalizeActor(raw: any): Actor {
  return {
    id: String(raw?.id ?? raw?.uuid ?? raw?.pk ?? ""),
    nombre: String(raw?.nombre ?? raw?.name ?? ""),
    tipo: (raw?.tipo ?? raw?.type ?? "PROVEEDOR") as ActorTipo,
    documento: raw?.documento ?? raw?.document ?? null,
    activo: !!(raw?.activo ?? raw?.active ?? true),
  };
}

function normalizePagination<T>(
  raw: any,
  page: number,
  page_size: number,
  mapper: (value: any) => T
): Paginated<T> {
  const rows: any[] = Array.isArray(raw) ? raw : raw?.results ?? [];
  const results = rows.map(mapper);
  const count = typeof raw?.count === "number" ? raw.count : results.length;
  return {
    results,
    count,
    page,
    page_size,
    next: raw?.next ?? null,
    prev: raw?.previous ?? null,
  };
}

export async function adminListActors(params: {
  search?: string;
  tipo?: ActorTipo | "";
  page?: number;
  page_size?: number;
}): Promise<Paginated<Actor>> {
  const page = params.page ?? 1;
  const page_size = params.page_size ?? 20;

  const query = toQuery({
    search: params.search ?? "",
    tipo: params.tipo ?? "",
    page,
    page_size,
  });

  const raw = await apiTry<any>([
    `${ADMIN_MGMT_PREFIX}/actors/${query}`,
    `${ADMIN_MGMT_PREFIX}/actores/${query}`,
    `${ADMIN_PREFIX}/actors/${query}`,
    `${ADMIN_PREFIX}/actores/${query}`,
  ]);

  return normalizePagination(raw, page, page_size, normalizeActor);
}

export async function adminCreateActor(actor: Partial<Actor>) {
  const payload = {
    ...(actor.nombre !== undefined ? { nombre: actor.nombre, name: actor.nombre } : {}),
    ...(actor.tipo !== undefined ? { tipo: actor.tipo, type: actor.tipo } : {}),
    ...(actor.documento !== undefined
      ? { documento: actor.documento, document: actor.documento }
      : {}),
    ...(actor.activo !== undefined
      ? { activo: actor.activo, active: actor.activo }
      : {}),
  };

  const created = await apiTry<any>(
    [
      `${ADMIN_MGMT_PREFIX}/actors/`,
      `${ADMIN_MGMT_PREFIX}/actores/`,
      `${ADMIN_PREFIX}/actors/`,
      `${ADMIN_PREFIX}/actores/`,
    ],
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );

  return normalizeActor(created);
}

export async function adminUpdateActor(id: string, actor: Partial<Actor>) {
  const payload = {
    ...(actor.nombre !== undefined ? { nombre: actor.nombre, name: actor.nombre } : {}),
    ...(actor.tipo !== undefined ? { tipo: actor.tipo, type: actor.tipo } : {}),
    ...(actor.documento !== undefined
      ? { documento: actor.documento, document: actor.documento }
      : {}),
    ...(actor.activo !== undefined
      ? { activo: actor.activo, active: actor.activo }
      : {}),
  };

  const updated = await apiTry<any>(
    [
      `${ADMIN_MGMT_PREFIX}/actors/${id}/`,
      `${ADMIN_MGMT_PREFIX}/actores/${id}/`,
      `${ADMIN_PREFIX}/actors/${id}/`,
      `${ADMIN_PREFIX}/actores/${id}/`,
    ],
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );

  return normalizeActor(updated);
}

export async function adminDeleteActor(id: string) {
  await apiTry<void>(
    [
      `${ADMIN_MGMT_PREFIX}/actors/${id}/`,
      `${ADMIN_MGMT_PREFIX}/actores/${id}/`,
      `${ADMIN_PREFIX}/actors/${id}/`,
      `${ADMIN_PREFIX}/actores/${id}/`,
    ],
    { method: "DELETE" }
  );
}

export async function listActors(params: {
  search?: string;
  tipo?: ActorTipo | "";
  page?: number;
  page_size?: number;
}) {
  const { results } = await adminListActors(params);
  return results || [];
}


