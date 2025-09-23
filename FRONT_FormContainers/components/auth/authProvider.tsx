"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

// === helpers de cookies/ls (visibles al middleware) ===
function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}
function setCookie(name: string, value: string, days = 7) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; Expires=${expires}; SameSite=Lax`;
}
function delCookie(name: string) {
  document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax`;
}

// === integra con tu api.admin.ts ===
export type WhoAmI = {
  is_authenticated: boolean;
  id: number | null;
  username: string | null;
  is_staff: boolean;
};

const ADMIN_TOKEN_KEY = "admin_token";

function getToken(): string | null {
  try {
    if (typeof localStorage !== "undefined") {
      const t = localStorage.getItem(ADMIN_TOKEN_KEY);
      if (t) return t;
    }
  } catch {}
  return getCookie("auth_token");
}

async function whoamiWithToken(token?: string | null): Promise<WhoAmI> {
  const headers: HeadersInit = token ? { Authorization: `Token ${token}` } : {};
  const res = await fetch("/api/whoami/", {
    method: "GET",
    credentials: "include",
    headers,
  });
  
  if (!res.ok) {
    // Si no está autenticado, limpiar cookies locales
    delCookie("is_staff");
    delCookie("auth_token");
    delCookie("auth_username");
    throw new Error("No autenticado");
  }
  
  const me = (await res.json()) as WhoAmI;
  
  // Solo sincronizar cookies si está autenticado
  if (me?.is_authenticated) {
    setCookie("is_staff", me?.is_staff ? "1" : "0", 7);
  }
  
  return me;
}

type AuthState = {
  loading: boolean;
  user: WhoAmI | null;
  login: (usernameOrEmail: string, password: string) => Promise<{ token: string; user: WhoAmI }>;
  logout: () => void;
  refresh: () => Promise<void>;
};

const AuthCtx = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<WhoAmI | null>(null);

  // Bootstrap: intenta recuperar sesión usando token (LS/cookie)
  useEffect(() => {
    let mounted = true;
    
    // Pequeño delay para asegurar que las cookies estén disponibles después del login
    const checkAuth = async () => {
      try {
        // Verificar múltiples fuentes de autenticación
        const token = getToken();
        const isStaffCookie = getCookie("is_staff");
        const authUsernameCookie = getCookie("auth_username");
        
        console.log("[AuthProvider] Checking auth:", { 
          hasToken: !!token, 
          hasIsStaff: !!isStaffCookie, 
          hasUsername: !!authUsernameCookie 
        });
        
        // Si hay señales de autenticación, intentar whoami
        if (token || isStaffCookie || authUsernameCookie) {
          const me = await whoamiWithToken(token || undefined);
          if (mounted && me?.is_authenticated) {
            console.log("[AuthProvider] User authenticated:", me);
            setUser(me);
            return;
          }
        }
        
        // Si no hay señales claras, aún intentar whoami por si hay sesión activa
        const me = await whoamiWithToken();
        if (mounted && me?.is_authenticated) {
          console.log("[AuthProvider] User authenticated via session:", me);
          setUser(me);
        }
      } catch (error) {
        console.log("[AuthProvider] Auth check failed:", error);
        // sin sesión válida; dejamos user=null
      } finally {
        if (mounted) setLoading(false);
      }
    };
    
    // Pequeño delay para evitar race conditions
    setTimeout(checkAuth, 100);
    
    return () => { mounted = false; };
  }, []);

  const value = useMemo<AuthState>(() => ({
    loading,
    user,
    // Este login es opcional si mantienes tu login actual en la página;
    // lo dejamos por si en algún punto quieres usar el provider.
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
          try { const d = await res.json(); msg = d?.detail || d?.error || msg; } catch {}
          throw new Error(msg || "Error de inicio de sesión");
        }
        const { token } = await res.json();
        // guarda cookie para middleware y, si quieres, también en LS:
        setCookie("auth_token", token, 7);
        try { localStorage.setItem(ADMIN_TOKEN_KEY, token); } catch {}
        const me = await whoamiWithToken(token);
        setUser(me);
        return { token, user: me };
      } finally {
        setLoading(false);
      }
    },
    logout() {
      delCookie("auth_token");
      delCookie("is_staff");
      try { localStorage.removeItem(ADMIN_TOKEN_KEY); } catch {}
      setUser(null);
      // la página que llame logout decide a dónde navegar
    },
    async refresh() {
      const token = getToken();
      const me = await whoamiWithToken(token || undefined);
      setUser(me);
    },
  }), [loading, user]);

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
