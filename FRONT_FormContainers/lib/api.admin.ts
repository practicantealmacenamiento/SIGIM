// ======================
// Admin API (robusta, tolerante a timing y trailing slash)
// ======================

export const adminTokenKey = "admin_token";
export const whoami = fetchWhoAmI;

// ----------------------
// URL helpers
// ----------------------
function baseUrl() {
  return (process.env.NEXT_PUBLIC_ADMIN_API_URL || "/api/").replace(/\/?$/, "/");
}
function buildUrl(path: string) {
  const base = baseUrl();
  const p0 = String(path || "");
  const p = p0.replace(/^\/+/, "");
  const hasQuery = p.includes("?");
  const looksLikeFile = /\.[a-z0-9]+$/i.test(p);
  const endsWithSlash = p.endsWith("/");
  const finalPath = hasQuery || looksLikeFile || endsWithSlash ? p : p + "/";
  return base + finalPath;
}

// ----------------------
// Cookies helpers (versión robusta)
// ----------------------
function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

function setCookie(name: string, value: string, days = 7) {
  const exp = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; Expires=${exp}; SameSite=Lax`;
}

/** Borra el cookie en variantes comunes de dominio/SameSite para garantizar su eliminación */
function hardDeleteCookie(name: string) {
  if (typeof document === "undefined" || typeof location === "undefined") return;
  const host = location.hostname; // p.ej. app.empresa.com
  const parts = host.split(".");
  const variants = new Set<string | undefined>([
    undefined,                                                          // sin Domain
    host,                                                               // app.empresa.com
    parts.length >= 2 ? `.${parts.slice(-2).join(".")}` : undefined,    // .empresa.com
    parts.length >= 3 ? `.${parts.slice(-3).join(".")}` : undefined,    // .sub.empresa.com
  ]);
  const samesites = ["Lax", "Strict", "None"];
  for (const d of variants) {
    for (const ss of samesites) {
      document.cookie =
        `${name}=; Path=/; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=${ss};` +
        (d ? ` Domain=${d};` : "");
    }
  }
}

// Alias compatible usado en el proyecto
function delCookie(name: string) {
  hardDeleteCookie(name);
}

// ----------------------
// Token helpers
// ----------------------
export function getAdminToken(): string | null {
  if (typeof window !== "undefined") {
    const ls = localStorage.getItem(adminTokenKey);
    if (ls) return ls;
  }
  // fallback: cookie que el backend puede dejar en login
  return getCookie("auth_token");
}
export function setAdminToken(token: string) {
  if (typeof window !== "undefined") localStorage.setItem(adminTokenKey, token);
}
export function clearAdminToken() {
  if (typeof window !== "undefined") localStorage.removeItem(adminTokenKey);
  hardDeleteCookie("auth_token"); // borrado agresivo
}

// ----------------------
// fetch helpers (credenciales + token + CSRF)
// ----------------------
function withAuth(init?: RequestInit): RequestInit {
  const headers = new Headers(init?.headers || {});
  const token = getAdminToken();
  if (token && !headers.has("Authorization")) headers.set("Authorization", `Token ${token}`);

  const method = (init?.method || "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = getCookie("csrftoken");
    if (csrf && !headers.has("X-CSRFToken")) headers.set("X-CSRFToken", csrf);
  }
  return { ...init, headers, credentials: "include" as const };
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const ct = res.headers.get("content-type") || "";
    let data: any = null;
    try { data = ct.includes("application/json") ? await res.json() : await res.text(); } catch {}
    const err: any = new Error((data && (data.detail || data.error)) || res.statusText || "HTTP error");
    err.status = res.status;
    err.data = data;
    throw err;
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  if (ct.startsWith("text/")) return (await res.text()) as unknown as T;
  return (await res.blob()) as unknown as T;
}

// ======================
// Tipos que utiliza tu UI de admin
// ======================
export type UUID = string;

export type AdminChoice = { id: string; text: string; branch_to?: string | null };
export type AdminQuestion = {
  id: string;
  text: string;
  type: "text" | "number" | "date" | "file" | "choice";
  required: boolean;
  order: number;
  choices?: AdminChoice[] | null;
};
export type AdminQuestionnaire = {
  id: UUID;
  title: string;
  version: string;
  timezone: string;
  questions: AdminQuestion[];
};

export type ActorTipo = "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR";
export type Actor = {
  id: UUID;
  tipo: ActorTipo;
  nombre: string;
  documento?: string | null;
  activo: boolean;
};

export type WhoAmI = {
  is_authenticated: boolean;
  id: number | null;
  username: string | null;
  is_staff: boolean;
};

// ==== Usuarios (administración) ====
export type AdminUser = {
  id?: number;
  username: string;
  email?: string;
  is_staff: boolean;
  is_superuser: boolean;
  is_active: boolean;
  password?: string; // para creación / cambio
};

// ======================
// Utilidades de limpieza en cliente
// ======================
function nukeAuthResidues() {
  try { localStorage.removeItem("auth_username"); } catch {}
  ["auth_token", "auth_username", "sessionid", "csrftoken", "is_staff"].forEach(hardDeleteCookie);
}

// ======================
// Auth
// ======================
export async function adminLoginDetail(usernameOrEmail: string, password: string) {
  // 1) Login: crea sesión, devuelve token y (tu back) setea cookies de UI
  const url = buildUrl("admin/login/");
  const res = await fetch(url, withAuth({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: usernameOrEmail, password }),
  }));
  const data = await handleResponse<{ token: string; user?: { username?: string } }>(res);

  // 2) Persistir SIEMPRE el token (evita races en el primer whoami)
  setAdminToken(data.token);
  if (data?.user?.username) {
    try { localStorage.setItem("auth_username", data.user.username); } catch {}
  }

  // 3) Enriquecer con whoami — si falla, NO pisamos is_staff (el back ya dejó la cookie)
  try {
    const who = await fetchWhoAmI(data.token);
    if (typeof who?.username === "string") {
      try { localStorage.setItem("auth_username", who.username || ""); } catch {}
    }
  } catch { /* silencio */ }

  return data;
}

/** Compat: algunas piezas esperan que adminLogin devuelva solo el token (string) */
export async function adminLogin(usernameOrEmail: string, password: string): Promise<string> {
  const data = await adminLoginDetail(usernameOrEmail, password);
  return data.token;
}

export async function fetchWhoAmI(explicitToken?: string): Promise<WhoAmI> {
  const headers: HeadersInit = explicitToken ? { Authorization: `Token ${explicitToken}` } : {};
  const res = await fetch(buildUrl("admin/whoami"), withAuth({
    method: "GET",
    headers: { ...headers, "Cache-Control": "no-store", Pragma: "no-cache" },
    cache: "no-store",
  }));
  const who = await handleResponse<WhoAmI>(res);

  // Mantén username “cacheado” si lo usas en UI
  if (typeof who?.username === "string") {
    try { localStorage.setItem("auth_username", who.username || ""); } catch {}
  }

  // 🔑 Cookie visible para middleware/navbar
  setCookie("is_staff", who?.is_staff ? "1" : "0", 7);

  return who;
}

export async function isAdmin(): Promise<boolean> {
  try {
    const w = await fetchWhoAmI();
    return !!w?.is_staff;
  } catch { return false; }
}

/** Cierra sesión en back (si existe /admin/logout/) y limpia señales en cliente. */
export async function adminLogout() {
  try {
    const logoutUrl = buildUrl("admin/logout");
    await fetch(logoutUrl, withAuth({
      method: "POST",
      headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
      cache: "no-store",
    }));
  } catch { /* ignora si el endpoint no existe */ }

  // Limpieza AGRESIVA en el cliente (incluye auth_username)
  clearAdminToken();
  nukeAuthResidues();
}

// ======================
// Questionnaires (admin)
// ======================
export async function adminListQuestionnaires(): Promise<AdminQuestionnaire[]> {
  const res = await fetch(buildUrl("admin/questionnaires"), withAuth({ method: "GET" }));
  return handleResponse<AdminQuestionnaire[]>(res);
}

/** La UI a veces espera { questions: number } */
export async function listQuestionnaires(): Promise<{ id: string; title: string; version: string; questions: number }[]> {
  const raw = await adminListQuestionnaires();
  return raw.map(q => ({
    id: q.id,
    title: q.title,
    version: q.version,
    questions: Array.isArray(q.questions) ? q.questions.length : 0,
  }));
}

export async function adminGetQuestionnaire(id: UUID): Promise<AdminQuestionnaire> {
  const res = await fetch(buildUrl(`admin/questionnaires/${id}`), withAuth({ method: "GET" }));
  return handleResponse<AdminQuestionnaire>(res);
}
export const getQuestionnaire = adminGetQuestionnaire;

export async function adminUpsertQuestionnaire(qn: AdminQuestionnaire) {
  const res = await fetch(buildUrl("admin/questionnaires/upsert"), withAuth({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(qn),
  }));
  return handleResponse<AdminQuestionnaire>(res);
}
export const upsertQuestionnaire = adminUpsertQuestionnaire;

export async function duplicateQuestionnaire(id: UUID, nextVersion?: string): Promise<{ id: UUID }> {
  const res = await fetch(buildUrl(`admin/questionnaires/${id}/duplicate`), withAuth({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(nextVersion ? { version: nextVersion } : {}),
  }));
  return handleResponse<{ id: UUID }>(res);
}

export async function deleteQuestionnaire(id: UUID) {
  const res = await fetch(buildUrl(`admin/questionnaires/${id}`), withAuth({ method: "DELETE" }));
  if (!res.ok && res.status !== 204) await handleResponse(res);
  return { ok: true };
}

// Reordenar preguntas
export async function reorderQuestions(id: UUID, order: string[]) {
  const res = await fetch(buildUrl(`admin/questionnaires/${id}/reorder`), withAuth({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order }),
  }));
  return handleResponse<{ ok: true; questions: number }>(res);
}

// ======================
// Actors (admin)
// ======================
export async function adminListActors(
  params?: { search?: string; tipo?: ActorTipo | "" } | string
): Promise<{ results: Actor[]; count?: number; next?: string | null; previous?: string | null }> {
  let search = "";
  let tipo = "";
  if (typeof params === "string") search = params;
  else if (params) { search = params.search || ""; tipo = params.tipo || ""; }

  const qs: string[] = [];
  if (search) qs.push(`search=${encodeURIComponent(search)}`);
  if (tipo) qs.push(`tipo=${encodeURIComponent(tipo)}`);
  const query = qs.length ? `?${qs.join("&")}` : "";

  const res = await fetch(buildUrl(`admin/actors/${query}`), withAuth({ method: "GET" }));
  const data = await handleResponse<Actor[] | { results: Actor[]; count?: number; next?: string; previous?: string }>(res);

  // Soporta tanto lista simple como paginado
  if (Array.isArray(data)) return { results: data };
  return { results: data.results || [], count: data.count, next: data.next, previous: data.previous };
}

/** Alias que devuelve array (usado por historial/page.tsx) */
export async function listActors(
  params?: { search?: string; tipo?: ActorTipo | "" } | string
): Promise<Actor[]> {
  const { results } = await adminListActors(params);
  return results || [];
}

export async function adminCreateActor(payload: Omit<Actor, "id">) {
  const res = await fetch(buildUrl("admin/actors"), withAuth({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }));
  return handleResponse<Actor>(res);
}

export async function adminUpdateActor(id: UUID, patch: Partial<Omit<Actor, "id">>) {
  const res = await fetch(buildUrl(`admin/actors/${id}`), withAuth({
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  }));
  return handleResponse<Actor>(res);
}

export async function adminDeleteActor(id: UUID) {
  const res = await fetch(buildUrl(`admin/actors/${id}`), withAuth({ method: "DELETE" }));
  if (!res.ok && res.status !== 204) await handleResponse(res);
  return { ok: true };
}
export const deleteActor = adminDeleteActor;

// ======================
// Users (admin)
// ======================
export async function listAdminUsers(): Promise<AdminUser[]> {
  const res = await fetch(buildUrl("admin/users"), withAuth({ method: "GET" }));
  return handleResponse<AdminUser[]>(res);
}

export async function upsertAdminUser(payload: AdminUser): Promise<AdminUser> {
  const body: Partial<AdminUser> = {
    username: payload.username,
    email: payload.email,
    is_staff: !!payload.is_staff,
    is_superuser: !!payload.is_superuser,
    is_active: !!payload.is_active,
  };
  if (payload.password) (body as any).password = payload.password;

  if (payload.id) {
    const res = await fetch(buildUrl(`admin/users/${payload.id}`), withAuth({
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }));
    return handleResponse<AdminUser>(res);
  } else {
    const res = await fetch(buildUrl("admin/users"), withAuth({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }));
    return handleResponse<AdminUser>(res);
  }
}

export async function deleteAdminUser(id: number): Promise<{ ok: true }> {
  const res = await fetch(buildUrl(`admin/users/${id}`), withAuth({ method: "DELETE" }));
  if (!res.ok && res.status !== 204) await handleResponse(res);
  return { ok: true };
}

// ======================
// Parche global (opcional)
// ======================
let _installed = false;
/**
 * Instala un wrapper sobre window.fetch que:
 *  - agrega credenciales (cookies) siempre
 *  - agrega X-CSRFToken en métodos de escritura
 *  - agrega Authorization: Token <admin_token> si existe
 *  - fuerza "no-store" para evitar respuestas cacheadas
 * Útil si piezas aisladas del front hacen "fetch" directo.
 */
export function installGlobalAuthFetch() {
  if (_installed) return;
  if (typeof window === "undefined" || typeof window.fetch !== "function") return;

  const original = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    try {
      const headers = new Headers(init?.headers || {});
      const method = (init?.method || "GET").toUpperCase();

      // CSRF para métodos de escritura
      if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
        const csrf = getCookie("csrftoken");
        if (csrf && !headers.has("X-CSRFToken")) headers.set("X-CSRFToken", csrf);
      }
      // Token de admin
      const tok = getAdminToken();
      if (tok && !headers.has("Authorization")) headers.set("Authorization", `Token ${tok}`);

      headers.set("Cache-Control", "no-store");

      return original(input, { ...init, headers, credentials: "include", cache: "no-store" });
    } catch {
      return original(input, init);
    }
  };

  _installed = true;
}
