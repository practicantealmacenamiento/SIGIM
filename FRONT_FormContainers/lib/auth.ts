// lib/auth.ts
import { http, cookies } from "./http";
import { adminLogin, fetchWhoAmI } from "./api.admin";

export async function login(username: string, password: string) {
  const loginData = await adminLogin(username, password);
  const me = await fetchWhoAmI(loginData.token);
  return { token: loginData.token, user: me };
}

export type WhoAmI = {
  is_authenticated: boolean;
  id: number | null;
  username: string | null;
  is_staff: boolean;
};

export async function loginApi(usernameOrEmail: string, password: string) {
  const data = await http<{ token: string; user: { is_staff: boolean } }>("/api/login/", {
    method: "POST",
    json: { username: usernameOrEmail, password },
  });
  // Guardamos token e indicador de staff (el backend ya dejó sesión + csrftoken)
  cookies.set("auth_token", data.token, 7);
  cookies.set("is_staff", data.user.is_staff ? "1" : "0", 7);
  return data;
}

export async function whoami(): Promise<WhoAmI> {
  const me = await http<WhoAmI>("/api/whoami/", { method: "GET" });
  cookies.set("is_staff", me.is_staff ? "1" : "0", 7); // sincroniza por si cambió
  return me;
}

export function logoutClient() {
  cookies.del("auth_token");
  cookies.del("is_staff");
  // La cookie de sesión (HttpOnly) se invalida en server o por expiración.
}
