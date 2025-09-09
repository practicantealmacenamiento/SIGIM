"use client";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CARD, INPUT } from "@/lib/ui";

/* Utilidad simple para leer cookies (CSRF si aplica) */
function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

/* POST directo al backend vía rewrite de Next (sin forzar barra final) */
async function loginDirect(username: string, password: string) {
  const csrf = getCookie("csrftoken");
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (csrf) headers["X-CSRFToken"] = csrf;

  const res = await fetch("/api/admin/login", {
    method: "POST",
    credentials: "include",       // recibe Set-Cookie
    cache: "no-store",            // evita cache raras en dev
    redirect: "manual",           // no sigas 30x (corta 308/301 automáticos)
    headers,
    body: JSON.stringify({ username, password }),
  });

  // Algunos adaptadores devuelven opaqueredirect con redirect: "manual" → cookie ya quedó
  const redirected = res.type === "opaqueredirect" || (res.status >= 300 && res.status < 400);
  if (!res.ok && !redirected) {
    let msg = "Error de inicio de sesión";
    try {
      const j = await res.json();
      msg = j?.detail || j?.error || msg;
    } catch {
      try { msg = (await res.text()) || msg; } catch {}
    }
    throw new Error(msg);
  }
}

/* Sanea el "next": nunca volver a /login */
function safeNextUrl(nextRaw: string | null): string {
  if (!nextRaw) return "/admin"; // puedes elegir "/" si prefieres
  try {
    const u = new URL(nextRaw, window.location.origin);
    if (u.origin !== window.location.origin) return "/admin";
    const p = u.pathname || "/";
    if (p.startsWith("/admin/login") || p === "/login") return "/admin";
    return p + u.search + u.hash;
  } catch {
    return "/admin";
  }
}

export default function AdminLoginPage() {
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const search = useSearchParams();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    setErr(null);

    try {
      // Solo un flujo: POST directo. No llamamos adminLogin() para no disparar whoami.
      await loginDirect(u, p);

      // Opcional: “calienta” la sesión con whoami SIN slash (evita 308)
      // Puedes comentar esto si tu guard ya lo hace por su cuenta.
      await fetch("/api/admin/whoami", {
        credentials: "include",
        cache: "no-store",
        redirect: "manual",
      }).catch(() => { /* no bloquea el login */ });

      // Asegura flush de cookies y refresco de RSC
      await new Promise((r) => setTimeout(r, 20));
      const next = safeNextUrl(search?.get("next"));
      router.replace(next);
      router.refresh();
    } catch (e: any) {
      setErr(e?.message || "Error de inicio de sesión");
      setLoading(false);
    }
  }

  // Si ya hay sesión, no muestres el form: redirige a next o /admin
  useEffect(() => {
    const already = getCookie("sessionid") || getCookie("auth_token");
    if (already) {
      const next = safeNextUrl(search?.get("next"));
      router.replace(next);
      router.refresh();
    }
  }, [router, search]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    setErr(null);

    try {
      const csrf = getCookie("csrftoken");
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (csrf) headers["X-CSRFToken"] = csrf;

      // POST directo (tu versión actual está OK)
      const res = await fetch("/api/admin/login", {
        method: "POST",
        credentials: "include",
        cache: "no-store",
        redirect: "manual",
        headers,
        body: JSON.stringify({ username: u, password: p }),
      });

      const redirected = res.type === "opaqueredirect" || (res.status >= 300 && res.status < 400);
      if (!res.ok && !redirected) {
        let msg = "Error de inicio de sesión";
        try {
          const j = await res.json();
          msg = j?.detail || j?.error || msg;
        } catch {
          try { msg = (await res.text()) || msg; } catch {}
        }
        throw new Error(msg);
      }

      // Calentar sesión (opcional)
      await fetch("/api/admin/whoami", { credentials: "include", cache: "no-store", redirect: "manual" }).catch(() => {});
      await new Promise((r) => setTimeout(r, 20));

      const next = safeNextUrl(search?.get("next"));
      router.replace(next);
      router.refresh();
    } catch (e: any) {
      setErr(e?.message || "Error de inicio de sesión");
      setLoading(false);
    }
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
