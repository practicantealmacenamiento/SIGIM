// lib/auth.ts
import {
  adminLogin,
  fetchWhoAmI,
  getAuthToken,
  clearAuthToken,
  AUTH_TOKEN_KEY,
} from "./api.admin";

/** Usuario básico tal como lo expone api.admin.fetchWhoAmI */
export type AdminWhoAmI = {
  id?: number | string;
  username: string;
  email?: string;
  is_staff: boolean;
};

/** Shape “clásico” que algunas pantallas podrían esperar */
export type WhoAmI = {
  is_authenticated: boolean;
  id: number | string | null;
  username: string | null;
  is_staff: boolean;
};

/**
 * Login unificado:
 * - usa adminLogin (que guarda el token en localStorage bajo AUTH_TOKEN_KEY)
 * - luego obtiene el usuario con fetchWhoAmI
 * - devuelve { token, user }
 */
export async function login(username: string, password: string) {
  await adminLogin(username, password); // setea token y username/is_staff en localStorage
  const token = getAuthToken() || "";
  const user = await fetchWhoAmI(); // AdminWhoAmI
  return { token, user };
}

/**
 * Compat: loginApi (antes usaba cookies). Ahora delega al login unificado.
 * Devuelve el mismo formato esperado por llamadas antiguas:
 * { token: string; user: { is_staff: boolean } }
 */
export async function loginApi(usernameOrEmail: string, password: string) {
  const { token, user } = await login(usernameOrEmail, password);
  return { token, user: { is_staff: !!user.is_staff } };
}

/**
 * whoami “clásico”:
 * - intenta fetchWhoAmI(); si falla, retorna is_authenticated=false
 * - mantiene el shape antiguo para no romper consumidores
 */
export async function whoami(): Promise<WhoAmI> {
  try {
    const u = await fetchWhoAmI(); // AdminWhoAmI
    return {
      is_authenticated: true,
      id: (u.id as any) ?? null,
      username: u.username ?? null,
      is_staff: !!u.is_staff,
    };
  } catch {
    return {
      is_authenticated: false,
      id: null,
      username: null,
      is_staff: false,
    };
  }
}

/** Cerrar sesión en cliente: limpia token y artefactos legacy (ver api.admin) */
export function logoutClient() {
  clearAuthToken();
}

/** Utilidad: leer el token actual (por si alguna pantalla lo necesita) */
export function getToken(): string | undefined {
  return getAuthToken();
}

/** Clave donde se guarda el token en localStorage (por si quieres referenciarla) */
export const AUTH_STORAGE_KEY = AUTH_TOKEN_KEY;
