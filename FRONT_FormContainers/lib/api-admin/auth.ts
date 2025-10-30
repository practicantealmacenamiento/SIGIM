/**
 * Acciones de autenticación: installGlobalAuthFetch, whoami y login.
 */
import { API_BASE, AUTH_PREFIX } from "./constants";
import {
  getAuthToken,
  setAuthToken,
  clearAuthToken,
  AUTH_USERNAME_KEY,
  AUTH_IS_STAFF_KEY,
} from "./auth-storage";
import { apiFetch, parseError } from "./client";
import type { WhoAmI } from "./types";

export function installGlobalAuthFetch() {
  if (typeof window === "undefined") return;
  const w = window as any;
  if (w.__authFetchInstalled) return;

  const origFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers || {});
    const token = getAuthToken();
    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    const res = await origFetch(input, { ...init, headers });
    if (res.status === 401) clearAuthToken();
    return res;
  };
  w.__authFetchInstalled = true;
}

export async function fetchWhoAmI(): Promise<WhoAmI> {
  const candidates = [
    `${AUTH_PREFIX}/whoami/`,
    `${AUTH_PREFIX}/me/`,
    `/api/v1/users/me/`,
  ];
  let last: any = null;
  for (const path of candidates) {
    try {
      const data = await apiFetch<any>(path);
      const u = data?.user ?? data;
      return {
        id: u?.id,
        username: String(u?.username ?? u?.user ?? u?.email ?? "user"),
        email: u?.email,
        is_staff: !!(u?.is_staff ?? u?.staff ?? u?.is_admin),
      };
    } catch (err) {
      last = err;
    }
  }
  throw last || new Error("No se pudo obtener whoami");
}

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
        if (url === candidates[0] && res.status === 400) {
          throw new Error(errMsg || "Usuario y/o contraseña incorrectos.");
        }
        lastErr = new Error(errMsg);
        continue;
      }

      const payload = await res.json().catch(() => ({}));
      const token =
        payload?.access ||
        payload?.token ||
        payload?.access_token ||
        payload?.key ||
        payload?.jwt ||
        payload?.data?.token ||
        payload?.data?.access;

      if (!token || typeof token !== "string") {
        lastErr = new Error("El servidor no devolvió token de acceso.");
        continue;
      }

      setAuthToken(token);

      try {
        const me = await fetchWhoAmI();
        if (typeof localStorage !== "undefined") {
          if (me?.username) localStorage.setItem(AUTH_USERNAME_KEY, String(me.username));
          localStorage.setItem(AUTH_IS_STAFF_KEY, me?.is_staff ? "1" : "0");
        }
      } catch {
        /* ignore */
      }
      return;
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr || new Error("No se pudo iniciar sesión");
}


