"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { adminLogin } from "@/lib/api.admin";
import { CARD, INPUT } from "@/lib/ui";

async function loginDirect(u: string, p: string) {
  const res = await fetch("/api/login/", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: u, password: p }),
  });
  if (!res.ok) {
    try {
      const j = await res.json();
      throw new Error(j?.detail || j?.error || res.statusText || "Error de inicio de sesión");
    } catch {
      const t = await res.text().catch(() => "");
      throw new Error(t || res.statusText || "Error de inicio de sesión");
    }
  }
  await res.json().catch(() => ({}));
}

/* Sanea el "next": nunca permitir volver a /login (evita loops) */
function safeNextUrl(nextRaw: string | null): string {
  if (!nextRaw) return "/";
  try {
    const u = new URL(nextRaw, window.location.origin);
    if (u.origin !== window.location.origin) return "/";
    const path = u.pathname || "/";
    if (path.startsWith("/login")) return "/";
    return path + u.search + u.hash;
  } catch {
    return "/";
  }
}

function LoginForm() {
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const search = useSearchParams();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    setErr(null);

    try {
      // 1) flujo normal
      await adminLogin(u, p);
    } catch (e1: any) {
      // 2) fallback blindado (garantiza cookies/sesión aunque falle whoami)
      try {
        await loginDirect(u, p);
      } catch (e2: any) {
        setErr(e2?.message || e1?.message || "Error de inicio de sesión");
        setLoading(false);
        return;
      }
    }

    // Delay más largo para asegurar que las cookies se establezcan correctamente
    await new Promise((r) => setTimeout(r, 500));
    
    // Verificar que las cookies se establecieron correctamente
    const authToken = document.cookie.includes('auth_token=');
    const isStaff = document.cookie.includes('is_staff=');
    
    if (!authToken && !isStaff) {
      setErr("Error: Las credenciales no se guardaron correctamente. Intenta de nuevo.");
      setLoading(false);
      return;
    }

    const next = safeNextUrl(search?.get("next"));
    // replace con reload de la app ya autenticada
    window.location.replace(next);
  }

  return (
    <main className="min-h-[calc(100vh-80px)] w-full px-6 md:px-8 py-10">
      <div className="mx-auto max-w-[520px]">
        <form onSubmit={onSubmit} className={`${CARD} p-8 md:p-10`} noValidate>
          <h1 className="text-2xl md:text-3xl font-semibold mb-6">Acceso administración</h1>

          <label className="block mb-4">
            <span className="text-sm">Usuario</span>
            <input
              className={INPUT}
              value={u}
              onChange={(e) => setU(e.target.value)}
              autoComplete="username"
              required
            />
          </label>

          <label className="block mb-6">
            <span className="text-sm">Contraseña</span>
            <input
              className={INPUT}
              type="password"
              value={p}
              onChange={(e) => setP(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          {err && (
            <p className="text-red-600 mb-4" role="alert" aria-live="polite">
              {err}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="min-h-[44px] px-5 py-2.5 rounded-xl bg-sky-600 text-white font-medium disabled:opacity-70"
          >
            {loading ? "Ingresando…" : "Ingresar"}
          </button>
        </form>
      </div>
    </main>
  );
}

export default function AdminLoginPage() {
  return (
    <Suspense fallback={
      <main className="min-h-[calc(100vh-80px)] w-full px-6 md:px-8 py-10">
        <div className="mx-auto max-w-[520px]">
          <div className={`${CARD} p-8 md:p-10`}>
            <h1 className="text-2xl md:text-3xl font-semibold mb-6">Acceso administración</h1>
            <div className="animate-pulse">
              <div className="h-4 bg-gray-200 rounded mb-2"></div>
              <div className="h-10 bg-gray-200 rounded mb-4"></div>
              <div className="h-4 bg-gray-200 rounded mb-2"></div>
              <div className="h-10 bg-gray-200 rounded mb-6"></div>
              <div className="h-11 bg-gray-200 rounded"></div>
            </div>
          </div>
        </div>
      </main>
    }>
      <LoginForm />
    </Suspense>
  );
}
