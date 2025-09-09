// lib/auth.ts
import { http, cookies, setToken, clearToken } from "./http";

export type WhoAmI = {
  is_authenticated: boolean;
  id: number | string | null;
  username: string | null;
  is_staff: boolean;
};

// Login unificado: solo token; si necesitas sesión para panel admin, el endpoint ya la crea.
export async function login(usernameOrEmail: string, password: string) {
  // /api/admin/login crea sesión y devuelve token
  const data = await http<{ token: string; user?: { username?: string; is_staff?: boolean } }>(
    "admin/login",
    { method: "POST", json: { username: usernameOrEmail, password }, useAdminBase: true, useSession: true }
  );

  setToken(data.token);
  if (data?.user?.username) {
    try { localStorage.setItem("auth_username", data.user.username); } catch {}
  }

  // Sincroniza cookie is_staff (útil para middleware/navbar si lo usas)
  try {
    const me = await whoami(); // ya usa token o cookie de sesión
    cookies.set("is_staff", me.is_staff ? "1" : "0", 7);
  } catch {}

  return data;
}

export async function whoami(): Promise<WhoAmI> {
  // Siempre 200; mira el JSON. Usa sesión si existe; también manda Authorization si hay token
  const me = await http<WhoAmI>("admin/whoami", { method: "GET", useAdminBase: true, useSession: true });
  // Mantén username “cacheado” para la UI
  try { localStorage.setItem("auth_username", me?.username || ""); } catch {}
  // Señal de UI
  cookies.set("is_staff", me?.is_staff ? "1" : "0", 7);
  return me;
}

export async function logout() {
  // Pide al backend invalidar sesión y revocar tokens (idempotente)
  try { await http("logout", { method: "POST", useSession: true }); } catch {}

  // Limpieza agresiva en cliente (evita “datos fantasma” en Home)
  clearToken();
  try { localStorage.removeItem("auth_username"); } catch {}
  cookies.del("auth_token");
  cookies.del("is_staff");
}
