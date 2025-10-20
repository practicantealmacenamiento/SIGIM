/* lib/api.admin.ts — Cliente Admin (login unificado, rutas /api/v1)
 * -----------------------------------------------------------------------------
 * Este cliente:
 * - Usa un único token (Bearer) en localStorage.
 * - No depende de cookies para autenticación.
 * - Ofrece utilidades resilientes (apiTry) que prueban múltiples rutas.
 * - Normaliza respuestas (whoami, actores, cuestionarios).
 *
 * NOTAS:
 * - installGlobalAuthFetch() inyecta Authorization automáticamente en window.fetch.
 * - parseError() intenta devolver mensajes útiles del backend.
 * - Las funciones de “management” priorizan prefijos ADMIN_MGMT_PREFIX.
 * - Mantén las variables NEXT_PUBLIC_* en tu .env para adaptar prefijos/host.
 * --------------------------------------------------------------------------- */

export type ActorTipo = "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR";

export type AdminChoice = {
  id: string;
  text: string;
  branch_to: string | null;
};

export type AdminQuestionType = "text" | "number" | "date" | "file" | "choice";

export type AdminQuestion = {
  id: string;
  text: string;
  type: AdminQuestionType;
  required: boolean;
  order: number;
  choices: AdminChoice[] | null;
  /** Modos específicos para preguntas de archivo (opcional según backend). */
  file_mode?: "image_only" | "image_ocr" | "ocr_only";
  /** Etiqueta semántica informativa (no funcional). */
  semantic_tag?: string;
};

export type AdminQuestionnaire = {
  id: string;
  title: string;
  version: string;
  timezone: string;
  questions: AdminQuestion[];
};

export type AdminUser = {
  id?: number;
  username: string;
  email?: string;
  is_staff: boolean;
  is_superuser: boolean;
  is_active: boolean;
  password?: string;
};

export type WhoAmI = {
  id?: number | string;
  username: string;
  email?: string;
  is_staff: boolean;
};

/* ===================== Config ===================== */

const DEFAULT_API_PORT = 8000;

/** Base URL del API. Si no hay NEXT_PUBLIC_API_URL, deriva del window.location. */
const API_BASE =
  (typeof window !== "undefined" &&
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "")) ||
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:${DEFAULT_API_PORT}`
    : `http://127.0.0.1:${DEFAULT_API_PORT}`);

/** Prefijos principales (sin “/” final). */
const ADMIN_PREFIX = (process.env.NEXT_PUBLIC_ADMIN_PREFIX || "/api/v1").replace(
  /\/$/,
  ""
);
const AUTH_PREFIX = (process.env.NEXT_PUBLIC_AUTH_PREFIX || "/api/v1").replace(
  /\/$/,
  ""
);
const ADMIN_MGMT_PREFIX = (
  process.env.NEXT_PUBLIC_ADMIN_MGMT_PREFIX || "/api/v1/management"
).replace(/\/$/, "");

/** Claves de almacenamiento local (configurables por ENV). */
export const AUTH_TOKEN_KEY =
  process.env.NEXT_PUBLIC_AUTH_TOKEN_KEY || "auth:access_token";
const USERNAME_KEY =
  process.env.NEXT_PUBLIC_AUTH_USERNAME_KEY || "auth:username";
const STAFF_KEY =
  process.env.NEXT_PUBLIC_AUTH_IS_STAFF_KEY || "auth:is_staff";

/* ===================== Auth helpers ===================== */

/** Lee el token de acceso almacenado en localStorage. */
export function getAuthToken(): string | undefined {
  if (typeof localStorage === "undefined") return undefined;
  return localStorage.getItem(AUTH_TOKEN_KEY) || undefined;
}

/** Persiste el token de acceso en localStorage. */
export function setAuthToken(token: string) {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

/** Elimina cookies heredadas (si existían) para evitar estados inconsistentes. */
export function purgeLegacyAuthArtifacts() {
  if (typeof document === "undefined") return;
  const kill = (name: string) =>
    (document.cookie = `${name}=; Path=/; Max-Age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax`);
  ["is_staff", "auth_username", "sessionid", "csrftoken", "auth_token"].forEach(
    kill
  );
}

/** Limpia token + metadatos en localStorage y artefactos legacy. */
export function clearAuthToken() {
  if (typeof localStorage !== "undefined") {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(
      process.env.NEXT_PUBLIC_AUTH_USERNAME_KEY || "auth:username"
    );
    localStorage.removeItem(
      process.env.NEXT_PUBLIC_AUTH_IS_STAFF_KEY || "auth:is_staff"
    );
  }
  purgeLegacyAuthArtifacts();
}

/** Devuelve true si hay token en localStorage. */
export function isAuthenticated() {
  return !!getAuthToken();
}

/* ===================== Fetch base ===================== */

/** Intenta extraer un mensaje de error útil desde una Response JSON o, si falla, el status text. */
async function parseError(res: Response) {
  try {
    const data = await res.json();
    if (typeof data === "string") return data;
    if (data?.detail) return data.detail;
    if (data?.error) return data.error;
    if (data && typeof data === "object") return JSON.stringify(data);
  } catch {
    // ignore
  }
  return `${res.status} ${res.statusText}`;
}

/**
 * apiFetch
 * -----
 * Envia fetch con:
 * - Authorization: Bearer <token> (si existe)
 * - Content-Type: application/json cuando hay body “string”.
 * - credentials: "omit" (no usa cookies).
 * Lanza Error con mensaje normalizado en respuestas !ok.
 */
async function apiFetch<T = any>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  const url = `${API_BASE}${path}`;

  // Si el caller pasó Headers o un objeto simple, homogenizamos en Record<string,string>.
  const incomingHeaders =
    init.headers instanceof Headers
      ? Object.fromEntries(init.headers.entries())
      : (init.headers as Record<string, string>) || {};

  // Content-Type automático SOLO si el body es string (JSON). Para FormData/etc no se setea.
  const hasStringBody = typeof init.body === "string";
  const baseHeaders: Record<string, string> = {
    Accept: "application/json",
    ...(hasStringBody ? { "Content-Type": "application/json" } : {}),
  };
  const headers: Record<string, string> = {
    ...baseHeaders,
    ...incomingHeaders,
  };
  if (token && !headers.Authorization) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(url, {
    ...init,
    headers,
    credentials: "omit",
  });

  if (res.status === 401) {
    clearAuthToken();
    throw new Error("No autorizado. Inicia sesión nuevamente.");
  }
  if (!res.ok) throw new Error(await parseError(res));
  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}

/**
 * apiTry
 * -----
 * Prueba varias rutas (en orden) hasta que una responda OK.
 * Si todas fallan, relanza el último error.
 */
async function apiTry<T = any>(
  paths: string[],
  init: RequestInit = {}
): Promise<T> {
  let lastErr: unknown = null;
  for (const p of paths) {
    try {
      return await apiFetch<T>(p, init);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("No se pudo resolver el endpoint");
}

/** Serializa un objeto a querystring, omitiendo undefined/null/"" */
function toQuery(params?: Record<string, any>) {
  if (!params) return "";
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "") return;
    usp.append(k, String(v));
  });
  const s = usp.toString();
  return s ? `?${s}` : "";
}

/* ===================== Bootstrap cliente ===================== */

/**
 * Inyecta un wrapper alrededor de window.fetch para añadir el token Bearer
 * automáticamente cuando exista, y limpiar auth en 401.
 * Idempotente: sólo se instala una vez.
 */
export function installGlobalAuthFetch() {
  if (typeof window === "undefined") return;
  const w = window as any;
  if (w.__authFetchInstalled) return;

  const origFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers || {});
    const token = getAuthToken();
    if (token && !headers.has("Authorization"))
      headers.set("Authorization", `Bearer ${token}`);
    const res = await origFetch(input, { ...init, headers });
    if (res.status === 401) clearAuthToken();
    return res;
  };
  w.__authFetchInstalled = true;
}

/**
 * fetchWhoAmI
 * -----
 * Intenta diversas rutas de “whoami/me”.
 * Normaliza el shape de usuario.
 */
export async function fetchWhoAmI(): Promise<WhoAmI> {
  const candidates = [
    `${AUTH_PREFIX}/whoami/`,
    `${AUTH_PREFIX}/me/`,
    `/api/v1/users/me/`,
  ];
  let last: any = null;
  for (const p of candidates) {
    try {
      const data = await apiFetch<any>(p);
      const u = data?.user ?? data;
      return {
        id: u?.id,
        username: String(u?.username ?? u?.user ?? u?.email ?? "user"),
        email: u?.email,
        is_staff: !!(u?.is_staff ?? u?.staff ?? u?.is_admin),
      };
    } catch (e) {
      last = e;
    }
  }
  throw last || new Error("No se pudo obtener whoami");
}

/* ===================== Login ===================== */

/**
 * adminLogin
 * -----
 * Intenta autenticarse en varias rutas conocidas:
 * - /login/
 * - /jwt/create/
 * - /api/token/
 * Si el primer candidato devuelve 400 (credenciales) aborta early con ese error.
 * Al autenticar:
 * - Guarda token.
 * - Sincroniza username / is_staff en localStorage (si puede).
 */
export async function adminLogin(username: string, password: string) {
  const body = JSON.stringify({ username, password });
  const candidates = [
    `${AUTH_PREFIX}/login/`,
    `${AUTH_PREFIX}/jwt/create/`,
    `/api/token/`,
  ];

  let lastErr: any = null;
  for (const url of candidates) {
    try {
      const res = await fetch(`${API_BASE}${url}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        credentials: "omit",
        body,
      });

      if (!res.ok) {
        const errMsg = await parseError(res);
        // Si el endpoint principal retorna 400, no seguimos probando alternativas
        if (url === candidates[0] && res.status === 400) {
          throw new Error(errMsg || "Usuario y/o contraseña incorrectos.");
        }
        lastErr = new Error(errMsg);
        continue;
      }

      const j = await res.json().catch(() => ({}));
      const token =
        j?.access ||
        j?.token ||
        j?.access_token ||
        j?.key ||
        j?.jwt ||
        j?.data?.token ||
        j?.data?.access;

      if (!token || typeof token !== "string") {
        lastErr = new Error("El servidor no devolvió token de acceso.");
        continue;
      }

      setAuthToken(token);

      // Best-effort: sincronizar username/is_staff
      try {
        const me = await fetchWhoAmI();
        if (typeof localStorage !== "undefined") {
          if (me?.username) localStorage.setItem(USERNAME_KEY, String(me.username));
          localStorage.setItem(STAFF_KEY, me?.is_staff ? "1" : "0");
        }
      } catch {
        // no romper login si whoami falla
      }
      return;
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("No se pudo iniciar sesión");
}

/* ===================== Formularios ===================== */

/**
 * Crea un cuestionario nuevo (management).
 * Devuelve el objeto creado (incluye id).
 */
export async function createQuestionnaire(input: {
  title: string;
  version?: string;
  timezone?: string;
  questions?: Array<{
    text: string;
    type?: string;
    required?: boolean;
    order?: number;
    file_mode?: string;
    semantic_tag?: string | null;
    choices?: Array<{ text: string; branch_to?: string | null }>;
  }>;
}) {
  const body = {
    title: input.title,
    version: input.version ?? "v1",
    timezone: input.timezone ?? "America/Bogota",
    ...(Array.isArray(input.questions) ? { questions: input.questions } : {}),
  };
  const created = await apiFetch(`${ADMIN_MGMT_PREFIX}/questionnaires/`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  return created;
}

/** Actualiza (PATCH) campos del cuestionario por id. */
export async function updateQuestionnaire(id: string, payload: any) {
  return apiFetch(`${ADMIN_MGMT_PREFIX}/questionnaires/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

/** Normaliza una pregunta a nuestro shape (AdminQuestion). */
function normalizeQuestion(raw: any, idx: number): AdminQuestion {
  const id = String(raw?.id ?? raw?.uuid ?? raw?.pk ?? `${idx + 1}`);
  const type = (raw?.type ?? raw?.tipo ?? "text") as AdminQuestionType;

  const choicesRaw: any[] | null = Array.isArray(raw?.choices)
    ? raw.choices
    : Array.isArray(raw?.opciones)
    ? raw.opciones
    : null;

  const choices: AdminChoice[] | null = choicesRaw
    ? choicesRaw.map((c, j) => ({
        id: String(c?.id ?? c?.uuid ?? c?.pk ?? `${id}-c${j + 1}`),
        text: String(c?.text ?? c?.label ?? c?.texto ?? ""),
        branch_to: c?.branch_to ?? c?.rama_a ?? null,
      }))
    : null;

  return {
    id,
    text: String(raw?.text ?? raw?.titulo ?? raw?.pregunta ?? ""),
    type,
    required: !!(raw?.required ?? raw?.obligatoria ?? false),
    order: Number(raw?.order ?? raw?.orden ?? idx + 1),
    choices,
    file_mode: raw?.file_mode,
    semantic_tag: raw?.semantic_tag ?? raw?.etiqueta ?? undefined,
  };
}

/**
 * Lista cuestionarios (con #preguntas) mezclando listado ligero + detalle en paralelo.
 * Mantiene el orden del backend.
 */
export async function listQuestionnaires(): Promise<
  { id: string; title: string; version: string; questions: number }[]
> {
  const data = await apiTry<any>([
    `${ADMIN_MGMT_PREFIX}/questionnaires/`,
    `${ADMIN_PREFIX}/cuestionarios/`,
    `${ADMIN_PREFIX}/questionnaires/`,
  ]);

  const rows: { id: string; title: string; version: string }[] = (
    Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : []
  ).map((it: any) => ({
    id: String(it.id ?? it.uuid ?? it.pk),
    title: String(it.title ?? it.nombre ?? "Sin título"),
    version: String(it.version ?? it.vers ?? "v1"),
  }));

  // Hidratar conteo de preguntas en paralelo (concurrency limitada)
  const limit = 4;
  let i = 0;
  const results: {
    id: string;
    title: string;
    version: string;
    questions: number;
  }[] = [];

  async function next() {
    const idx = i++;
    if (idx >= rows.length) return;
    const r = rows[idx];
    try {
      const detail = await apiTry<any>([
        `${ADMIN_MGMT_PREFIX}/questionnaires/${r.id}/`,
        `${ADMIN_PREFIX}/cuestionarios/${r.id}/`,
        `${ADMIN_PREFIX}/questionnaires/${r.id}/`,
      ]);
      const qs = Array.isArray(detail?.questions)
        ? detail.questions
        : detail?.preguntas ?? [];
      results[idx] = { ...r, questions: Array.isArray(qs) ? qs.length : 0 };
    } catch {
      results[idx] = { ...r, questions: 0 };
    }
    await next();
  }

  await Promise.all(
    Array.from({ length: Math.min(limit, rows.length) }, () => next())
  );

  return results;
}

/** Obtiene un cuestionario normalizado (con todas sus preguntas). */
export async function getQuestionnaire(
  id: string
): Promise<AdminQuestionnaire> {
  const raw = await apiTry<any>([
    `${ADMIN_MGMT_PREFIX}/questionnaires/${id}/`,
    `${ADMIN_PREFIX}/cuestionarios/${id}/`,
    `${ADMIN_PREFIX}/questionnaires/${id}/`,
  ]);
  const rawQs: any[] = Array.isArray(raw?.questions)
    ? raw.questions
    : raw?.preguntas ?? [];
  const questions = rawQs.map(normalizeQuestion);
  return {
    id: String(raw.id ?? id),
    title: raw.title ?? raw.nombre ?? "Sin título",
    version: raw.version ?? raw.vers ?? "v1",
    timezone: raw.timezone ?? raw.zona_horaria ?? "America/Bogota",
    questions,
  };
}

/**
 * Crea/actualiza un cuestionario con shape estable.
 * Devuelve el cuestionario normalizado tras guardar.
 */
export async function upsertQuestionnaire(
  q: AdminQuestionnaire
): Promise<AdminQuestionnaire> {
  const payload = {
    id: q.id,
    title: q.title,
    version: q.version,
    timezone: q.timezone,
    questions: q.questions.map((x) => ({
      id: x.id,
      text: x.text,
      type: x.type,
      required: x.required,
      order: x.order,
      choices: x.choices
        ? x.choices.map((c) => ({
            id: c.id,
            text: c.text,
            branch_to: c.branch_to,
          }))
        : null,
      ...(x.file_mode ? { file_mode: x.file_mode } : {}),
      ...(x.semantic_tag ? { semantic_tag: x.semantic_tag } : {}),
    })),
  };

  const hasId = !!q.id;
  const paths = hasId
    ? [
        `${ADMIN_MGMT_PREFIX}/questionnaires/${q.id}/`,
        `${ADMIN_PREFIX}/cuestionarios/${q.id}/`,
        `${ADMIN_PREFIX}/questionnaires/${q.id}/`,
      ]
    : [
        `${ADMIN_MGMT_PREFIX}/questionnaires/`,
        `${ADMIN_PREFIX}/cuestionarios/`,
        `${ADMIN_PREFIX}/questionnaires/`,
      ];
  const method = hasId ? "PUT" : "POST";

  const saved = await apiTry<any>(paths, {
    method,
    body: JSON.stringify(payload),
  });
  return await getQuestionnaire(String(saved?.id ?? q.id));
}

/** Duplica un cuestionario opcionalmente cambiando version. */
export async function duplicateQuestionnaire(id: string, newVersion?: string) {
  const body = newVersion ? { version: newVersion } : undefined;
  const res = await apiTry<any>(
    [
      `${ADMIN_MGMT_PREFIX}/questionnaires/${id}/duplicate/`,
      `${ADMIN_PREFIX}/cuestionarios/${id}/duplicar/`,
      `${ADMIN_PREFIX}/cuestionarios/${id}/duplicate/`,
      `${ADMIN_PREFIX}/questionnaires/${id}/duplicate/`,
    ],
    { method: "POST", body: body ? JSON.stringify(body) : undefined }
  );
  return { id: String(res?.id ?? res?.uuid ?? id) };
}

/** Elimina un cuestionario por id. */
export async function deleteQuestionnaire(id: string) {
  await apiTry<void>(
    [
      `${ADMIN_MGMT_PREFIX}/questionnaires/${id}/`,
      `${ADMIN_PREFIX}/cuestionarios/${id}/`,
      `${ADMIN_PREFIX}/questionnaires/${id}/`,
    ],
    { method: "DELETE" }
  );
}

/**
 * Reordena preguntas de un cuestionario.
 * Prueba distintos endpoints y distintos payloads aceptados comúnmente.
 */
export async function reorderQuestions(
  questionnaireId: string,
  orderedIds: string[]
): Promise<void> {
  // prefijos (no depende de constantes externas para evitar errores de compilación)
  const MGMT = (
    process.env.NEXT_PUBLIC_ADMIN_MGMT_PREFIX || "/api/v1/management"
  ).replace(/\/$/, "");
  const APIV1 = (process.env.NEXT_PUBLIC_ADMIN_PREFIX || "/api/v1").replace(
    /\/$/,
    ""
  );

  const urls = [
    `${MGMT}/questionnaires/${questionnaireId}/reorder/`,
    `${MGMT}/questionnaires/${questionnaireId}/orden/`,
    `${APIV1}/cuestionarios/${questionnaireId}/reorder/`,
    `${APIV1}/cuestionarios/${questionnaireId}/orden/`,
    `${APIV1}/questionnaires/${questionnaireId}/reorder/`,
  ];

  const payloads = [{ order: orderedIds }, { questions: orderedIds }, { ids: orderedIds }];

  let lastErr: unknown = null;
  for (const u of urls) {
    for (const p of payloads) {
      try {
        await apiFetch<void>(u, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(p),
        });
        return;
      } catch (e) {
        lastErr = e;
      }
    }
  }
  throw lastErr || new Error("No se pudo reordenar las preguntas");
}

/* ===================== Actores (con paginación) ===================== */

export type Actor = {
  id: string;
  nombre: string;
  tipo: ActorTipo;
  documento?: string | null;
  activo: boolean;
};

export type Paginated<T> = {
  results: T[];
  count: number;
  page: number;
  page_size: number;
  next?: string | null;
  prev?: string | null;
};

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
  mapper: (x: any) => T
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

/**
 * adminListActors
 * -----
 * Lista actores con paginación real; prioriza management y ofrece fallbacks.
 */
export async function adminListActors(params: {
  search?: string;
  tipo?: ActorTipo | "";
  page?: number;
  page_size?: number;
}): Promise<Paginated<Actor>> {
  const page = Math.max(1, Number(params.page ?? 1));
  const page_size = Math.min(200, Math.max(5, Number(params.page_size ?? 20)));

  const q = toQuery({
    search: params.search,
    tipo: params.tipo,
    page,
    page_size,
  });

  const raw = await apiTry<any>([
    `${ADMIN_MGMT_PREFIX}/actors/${q}`,
    `${ADMIN_MGMT_PREFIX}/actores/${q}`,
    `${ADMIN_PREFIX}/actors/${q}`,
    `${ADMIN_PREFIX}/actores/${q}`,
  ]);

  return normalizePagination(raw, page, page_size, normalizeActor);
}

/** Crea un actor y lo devuelve normalizado. */
export async function adminCreateActor(actor: Partial<Actor>) {
  const payload = {
    nombre: actor.nombre,
    name: actor.nombre,
    tipo: actor.tipo,
    type: actor.tipo,
    documento: actor.documento ?? null,
    document: actor.documento ?? null,
    activo: actor.activo ?? true,
    active: actor.activo ?? true,
  };
  const created = await apiTry<any>(
    [
      `${ADMIN_MGMT_PREFIX}/actors/`,
      `${ADMIN_MGMT_PREFIX}/actores/`,
      `${ADMIN_PREFIX}/actors/`,
      `${ADMIN_PREFIX}/actores/`,
    ],
    { method: "POST", body: JSON.stringify(payload) }
  );
  return normalizeActor(created);
}

/** Actualiza (PATCH) un actor y devuelve el resultado normalizado. */
export async function adminUpdateActor(id: string, actor: Partial<Actor>) {
  const payload: any = {
    ...(actor.nombre !== undefined
      ? { nombre: actor.nombre, name: actor.nombre }
      : {}),
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
    { method: "PATCH", body: JSON.stringify(payload) }
  );
  return normalizeActor(updated);
}

/** Elimina un actor por id. */
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

/** Atajo que devuelve sólo resultados (sin metadatos de paginación). */
export async function listActors(params: {
  search?: string;
  tipo?: ActorTipo | "";
  page?: number;
  page_size?: number;
}) {
  const { results } = await adminListActors(params);
  return results || [];
}

/* ===================== Usuarios ===================== */

/** Lista usuarios admin (normalizados). */
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

/** Crea/actualiza un usuario admin y devuelve el resultado normalizado. */
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
  if (user.password && user.password.trim() !== "")
    payload.password = user.password;

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

/** Elimina un usuario admin. */
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
