/* eslint-disable @next/next/no-html-link-for-pages */
"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { adminLogin, isAuthenticated } from "@/lib/api.admin";
import { CARD, INPUT } from "@/lib/ui";

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

function EyeIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <path d="M1.5 12s3.6-7.5 10.5-7.5S22.5 12 22.5 12 18.9 19.5 12 19.5 1.5 12 1.5 12Z" stroke="currentColor" strokeWidth="1.5"/>
      <circle cx="12" cy="12" r="3.25" stroke="currentColor" strokeWidth="1.5"/>
    </svg>
  );
}
function EyeOffIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <path d="M3 3l18 18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M6.2 6.6C3.9 8.3 2.4 10.6 1.5 12c0 0 3.6 7.5 10.5 7.5 2 0 3.8-.5 5.3-1.3M17.8 6.2A10.9 10.9 0 0 0 12 4.5C5.1 4.5 1.5 12 1.5 12c.5.8 1.1 1.8 2.1 2.8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M9.2 9.2A3.25 3.25 0 0 0 12 15.25c.5 0 1-.1 1.4-.3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

function Spinner({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-block h-4 w-4 rounded-full border-2 border-white/80 border-t-transparent animate-spin ${className}`} aria-hidden />
  );
}

function LoginForm() {
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [showPass, setShowPass] = useState(false);
  const [capsOn, setCapsOn] = useState(false);
  const [touchedPass, setTouchedPass] = useState(false);

  const search = useSearchParams();

  const canSubmit = useMemo(() => {
    return u.trim().length > 0 && p.length > 0 && !loading;
  }, [u, p, loading]);

  useEffect(() => {
    if (err) {
      // Quita el error cuando el usuario vuelve a escribir
      const t = setTimeout(() => setErr(null), 4000);
      return () => clearTimeout(t);
    }
  }, [err]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;

    setLoading(true);
    setErr(null);

    try {
      await adminLogin(u.trim(), p); // token en localStorage + whoami (interno)
    } catch (e: any) {
      setErr(e?.message || "Error de inicio de sesión");
      setLoading(false);
      return;
    }

    if (!isAuthenticated()) {
      setErr("Error: no se estableció el token de sesión. Intenta de nuevo.");
      setLoading(false);
      return;
    }

    const next = safeNextUrl(search?.get("next"));
    window.location.replace(next);
  }

  return (
    <main className="min-h-[calc(100vh-80px)] w-full px-6 md:px-8 py-10">
      <div className="mx-auto max-w-[520px]">
        <form
          onSubmit={onSubmit}
          className={`${CARD} p-8 md:p-10 transition-[box-shadow,transform] duration-200 ${err ? "animate-[shake_160ms_2]" : ""}`}
          noValidate
          aria-busy={loading}
        >
          <h1 className="text-2xl md:text-3xl font-semibold mb-2">Acceso</h1>
          <p className="text-sm text-slate-500 dark:text-white/60 mb-6">
            Ingresa tus credenciales para continuar.
          </p>

          {/* Usuario */}
          <label className="block mb-4">
            <span className="text-sm">Usuario</span>
            <input
              className={`${INPUT} transition-shadow duration-150 focus:shadow-sm`}
              value={u}
              onChange={(e) => setU(e.target.value)}
              autoComplete="username"
              required
              autoFocus
              inputMode="email"
            />
          </label>

          {/* Contraseña */}
          <label className="block mb-2">
            <span className="text-sm">Contraseña</span>
            <div className="relative">
              <input
                className={`${INPUT} pr-12 transition-shadow duration-150 focus:shadow-sm`}
                type={showPass ? "text" : "password"}
                value={p}
                onChange={(e) => { setP(e.target.value); setTouchedPass(true); }}
                onKeyUp={(e) => setCapsOn(e.getModifierState?.("CapsLock") || false)}
                onKeyDown={(e) => setCapsOn(e.getModifierState?.("CapsLock") || false)}
                onBlur={() => setCapsOn(false)}
                autoComplete="current-password"
                required
                aria-describedby={capsOn && touchedPass ? "caps-hint" : undefined}
              />
              <button
                type="button"
                onClick={() => setShowPass(s => !s)}
                aria-label={showPass ? "Ocultar contraseña" : "Mostrar contraseña"}
                aria-pressed={showPass}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-2 text-slate-600 hover:bg-slate-100 dark:text-white/70 dark:hover:bg-white/10 transition"
                tabIndex={0}
              >
                {showPass ? <EyeOffIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
              </button>
            </div>
          </label>

          {/* Hint de CapsLock */}
          {capsOn && touchedPass && (
            <div
              id="caps-hint"
              className="mb-4 mt-1 inline-flex items-center gap-2 text-xs px-2 py-1 rounded-lg bg-amber-50 text-amber-800 border border-amber-200 dark:bg-amber-400/10 dark:text-amber-200 dark:border-amber-300/20"
              role="status"
              aria-live="polite"
            >
              <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M12 8l4 4H8l4-4Z" /><path d="M12 16v-1.5" strokeLinecap="round"/>
              </svg>
              Bloq Mayús activado
            </div>
          )}

          {/* Error */}
          {err && (
            <p
              className="text-red-600 dark:text-red-400 mb-4 transition-opacity"
              role="alert"
              aria-live="assertive"
            >
              {err}
            </p>
          )}

          <div className="mt-2 flex items-center gap-3">
            <button
              type="submit"
              disabled={!canSubmit}
              className={`min-h-[44px] px-5 py-2.5 rounded-xl bg-skyBlue text-white font-medium shadow 
              transition-all duration-150 hover:opacity-95 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-skyBlue/60
              disabled:opacity-60 disabled:cursor-not-allowed inline-flex items-center gap-2`}
            >
              {loading && <Spinner />}
              {loading ? "Ingresando…" : "Ingresar"}
            </button>

            {/* Opcional: enlace de ayuda */}
            <a
              href="/"
              className="text-sm text-slate-600 dark:text-white/70 underline underline-offset-4 hover:opacity-80"
            >
              ¿Olvidaste tu contraseña?
            </a>
          </div>
        </form>
      </div>

      {/* Anim keyframes (shake suave) */}
      <style jsx global>{`
        @keyframes shake {
          0% { transform: translateX(0); }
          25% { transform: translateX(-4px); }
          50% { transform: translateX(0); }
          75% { transform: translateX(4px); }
          100% { transform: translateX(0); }
        }
      `}</style>
    </main>
  );
}

export default function LoginPage() {
  return <LoginForm />;
}
