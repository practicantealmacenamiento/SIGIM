"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

/**
 * AuthProvider — Contexto mínimo de autenticación para App Router.
 *
 * Principios:
 * - No llama al servidor salvo para /api/whoami/ (y /api/login/ cuando se usa login()).
 * - Sincroniza señales de sesión en cookies (visibles para middleware/SSR) y, opcionalmente, localStorage.
 * - No gestiona navegación; la página que llama logout decide a dónde ir.
 *
 * Mantiene compatibilidad total con el código que ya tienes:
 * - Cookies: "auth_token" (token), "is_staff" (1/0), "auth_username" (lo lees si existe).
 * - LocalStorage: "admin_token".
 * - Delay bootstrap: 100ms.
 * - Endpoints: /api/whoami/ (GET), /api/login/ (POST).
 */

// ========= Config & tipos públicos =========

export type WhoAmI = {
  is_authenticated: boolean;
  id: number | null;
  username: string | null;
  is_staff: boolean;
};

type AuthState = {
  loading: boolean;
  user: WhoAmI | null;
  login: (
    usernameOrEmail: string,
    password: string
  ) => Promise<{ token: string; user: WhoAmI }>;
  logout: () => void;
  refresh: () => Promise<void>;
};

// Claves/identificadores usados por cookies/LS (mantener nombres existentes)
const ADMIN_TOKEN_KEY = "admin_token";
const COOKIE_AUTH_TOKEN = "auth_token";
const COOKIE_IS_STAFF = "is_staff";
const COOKIE_AUTH_USERNAME = "auth_username";

// Flag de depuración silenciosa (no cambia el comportamiento)
const DEBUG =
  (typeof process !== "undefined" &&
    process.env.NEXT_PUBLIC_AUTH_DEBUG === "1") ||
  false;

// ========= Utils de cookies/LS (seguros para client-side) =========

/** Lee una cookie por nombre (solo en navegador). */
function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

/** Setea cookie con SameSite=Lax y Path=/ (como estaba). */
function setCookie(name: string, value: string, days = 7) {
  if (typeof document === "undefined") return;
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(
    value
  )}; Path=/; Expires=${expires}; SameSite=Lax`;
}

/** Elimina cookie por Max-Age=0. */
function delCookie(name: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax`;
}

/** Obtiene token desde localStorage o, en su defecto, desde cookie. */
function getToken(): string | null {
  try {
    if (typeof localStorage !== "undefined") {
      const t = localStorage.getItem(ADMIN_TOKEN_KEY);
      if (t) return t;
    }
  } catch {
    /* ignore */
  }
  return getCookie(COOKIE_AUTH_TOKEN);
}

// ========= Llamadas a API (respetando tus endpoints actuales) =========

/**
 * whoamiWithToken — GET /api/whoami/
 * - Incluye Authorization: Token ${token} si se provee.
 * - En caso no-OK limpia cookies locales relevantes y lanza Error("No autenticado").
 * - Si está autenticado, sincroniza cookie is_staff=1/0 (7 días).
 */
async function whoamiWithToken(token?: string | null): Promise<WhoAmI> {
  const headers: HeadersInit = token ? { Authorization: `Token ${token}` } : {};
  const res = await fetch("/api/whoami/", {
    method: "GET",
    credentials: "include",
    headers,
  });

  if (!res.ok) {
    // Sin sesión → limpieza local mínima
    delCookie(COOKIE_IS_STAFF);
    delCookie(COOKIE_AUTH_TOKEN);
    delCookie(COOKIE_AUTH_USERNAME);
    throw new Error("No autenticado");
  }

  const me = (await res.json()) as WhoAmI;

  if (me?.is_authenticated) {
    setCookie(COOKIE_IS_STAFF, me.is_staff ? "1" : "0", 7);
  }

  return me;
}

// ========= Contexto =========

const AuthCtx = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<WhoAmI | null>(null);

  /**
   * Bootstrap de sesión:
   * 1) Intenta detectar señales de auth (token LS/cookie, cookies auxiliares).
   * 2) Si hay señales → whoami con token si existe; si no, con sesión (credentials: include).
   * 3) Si no hay señales, igualmente intenta whoami por si existe sesión activa de servidor.
   *
   * Nota: mantengo el delay de 100ms para evitar race conditions tras login.
   */
  useEffect(() => {
    let mounted = true;
    const tid = setTimeout(async () => {
      try {
        const token = getToken();
        const isStaffCookie = getCookie(COOKIE_IS_STAFF);
        const authUsernameCookie = getCookie(COOKIE_AUTH_USERNAME);

        if (DEBUG) {
          console.log("[AuthProvider] bootstrap signals", {
            hasToken: !!token,
            hasIsStaff: !!isStaffCookie,
            hasUsername: !!authUsernameCookie,
          });
        }

        if (token || isStaffCookie || authUsernameCookie) {
          const me = await whoamiWithToken(token || undefined);
          if (mounted && me?.is_authenticated) {
            if (DEBUG) console.log("[AuthProvider] authenticated via token/cookies", me);
            setUser(me);
            return;
          }
        }

        // Intento “por si acaso” hay sesión de servidor activa
        const me = await whoamiWithToken();
        if (mounted && me?.is_authenticated) {
          if (DEBUG) console.log("[AuthProvider] authenticated via server session", me);
          setUser(me);
        }
      } catch (error) {
        if (DEBUG) console.log("[AuthProvider] bootstrap failed", error);
        // Dejar user=null silenciosamente
      } finally {
        if (mounted) setLoading(false);
      }
    }, 100);

    return () => {
      mounted = false;
      clearTimeout(tid);
    };
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      loading,
      user,

      /**
       * login — POST /api/login/
       * - Envía { username, password } con credentials: "include".
       * - Espera { token } y lo sincroniza en cookie y localStorage.
       * - Llama whoami() con el token y retorna { token, user }.
       */
      async login(usernameOrEmail: string, password: string) {
        setLoading(true);
        try {
          const res = await fetch("/api/login/", {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: usernameOrEmail, password }),
          });

          if (!res.ok) {
            let msg = res.statusText;
            try {
              const d = await res.json();
              msg = (d as any)?.detail || (d as any)?.error || msg;
            } catch {
              /* ignore */
            }
            throw new Error(msg || "Error de inicio de sesión");
          }

          const { token } = (await res.json()) as { token: string };

          // Sincronización local (mismos nombres que ya usas)
          setCookie(COOKIE_AUTH_TOKEN, token, 7);
          try {
            localStorage.setItem(ADMIN_TOKEN_KEY, token);
          } catch {
            /* ignore */
          }

          const me = await whoamiWithToken(token);
          setUser(me);
          return { token, user: me };
        } finally {
          setLoading(false);
        }
      },

      /**
       * logout — Limpia señales locales de sesión.
       * La navegación post-logout la decide quien llame a esta función.
       */
      logout() {
        delCookie(COOKIE_AUTH_TOKEN);
        delCookie(COOKIE_IS_STAFF);
        try {
          localStorage.removeItem(ADMIN_TOKEN_KEY);
        } catch {
          /* ignore */
        }
        setUser(null);
      },

      /**
       * refresh — Revalida sesión consultando /api/whoami/ con token si existe.
       */
      async refresh() {
        const token = getToken();
        const me = await whoamiWithToken(token || undefined);
        setUser(me);
      },
    }),
    [loading, user]
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
