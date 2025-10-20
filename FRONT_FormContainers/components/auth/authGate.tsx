"use client";

import { ReactNode, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { isAuthenticated } from "@/lib/api.admin";

/**
 * AuthGate — Guard de rutas minimalista para App Router (client component).
 *
 * Qué hace:
 * 1) Considera como públicas las rutas explícitas en PUBLIC_ROUTES.
 * 2) Todo lo que empiece por un prefijo en ALWAYS_PROTECTED_PREFIXES se considera protegido.
 * 3) Para rutas protegidas, si no hay token válido (via isAuthenticated()), redirige a /login?next=… .
 * 4) Reacciona a cambios de pestaña, bfcache (pageshow) y al evento 'storage' (logout/login en otra pestaña).
 *
 * Importante:
 * - No consulta servidor. Confía en el token del login unificado (localStorage) que valida `isAuthenticated()`.
 * - Evita parpadeo en rutas protegidas hasta que determine si hay sesión.
 */

// Rutas públicas “exactas”
const PUBLIC_ROUTES = new Set<string>([
  "/",
  "/login",
  "/registro",
  "/recuperar",
  "/verificacion",
  "/faq",
  "/contacto",
]);

/**
 * Prefijos SIEMPRE protegidos.
 * Nota: si deseas que /formulario sea público, elimínalo de esta lista.
 */
const ALWAYS_PROTECTED_PREFIXES = [
  "/admin",
  "/panel",
  "/historial",
  "/formulario",
  "/seleccion-formulario",
] as const;

// Clave del token en localStorage (permite override por env en build)
const AUTH_KEY =
  (process.env.NEXT_PUBLIC_AUTH_TOKEN_KEY as string) || "auth:access_token";

/** Util: ¿es pública la ruta exacta? */
function isPublicRoute(pathname: string | null): boolean {
  if (!pathname) return true;
  return PUBLIC_ROUTES.has(pathname);
}

/** Util: ¿está bajo un prefijo protegido? */
function isUnderProtectedPrefix(pathname: string | null): boolean {
  if (!pathname) return false;
  return ALWAYS_PROTECTED_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  );
}

/** Util: string actual (ruta + query) para armar el `next=` de /login */
function buildCurrentUrl(pathname: string | null, search: URLSearchParams | null): string {
  const base = pathname || "/";
  const q = search?.toString();
  return q && q.length ? `${base}?${q}` : base;
}

export default function AuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();

  // null = evaluando | true/false = resultado de isAuthenticated()
  const [authed, setAuthed] = useState<boolean | null>(null);

  /** ¿Esta ruta requiere autenticación? (memo para evitar recomputar) */
  const pathProtected = useMemo<boolean>(() => {
    if (!pathname) return false;
    if (isPublicRoute(pathname)) return false;
    return isUnderProtectedPrefix(pathname);
  }, [pathname]);

  /** Re-evalúa auth de manera segura (no rompe el render si hay error en isAuthenticated) */
  const recomputeAuth = () => {
    try {
      // isAuthenticated() internamente lee localStorage → token bajo AUTH_KEY
      setAuthed(isAuthenticated());
    } catch {
      setAuthed(false);
    }
  };

  // Evaluación inicial + listeners (storage/focus/visibility/pageshow)
  useEffect(() => {
    // 1) primera evaluación
    recomputeAuth();

    // 2) listeners relevantes
    const onStorage = (e: StorageEvent) => {
      // Si no especifica clave, es un “clear” masivo → re-evaluar igual
      if (!e.key) return recomputeAuth();
      if (e.key === AUTH_KEY) recomputeAuth();
    };

    const onFocus = () => recomputeAuth();
    const onVisibility = () => {
      if (document.visibilityState === "visible") recomputeAuth();
    };
    // Páginas servidas desde bfcache (Safari/Firefox): pageshow con persisted=true
    const onPageShow = (ev: PageTransitionEvent) => {
      if ((ev as any).persisted) recomputeAuth();
    };

    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pageshow", onPageShow as any);

    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pageshow", onPageShow as any);
    };
  }, []); // solo una vez en el ciclo de vida del componente

  // Redirección si corresponde (ruta protegida + no autenticado)
  useEffect(() => {
    if (authed === null) return; // aún evaluando
    if (!pathProtected) return;  // ruta pública → no hacemos nada
    if (authed) return;          // autenticado → puede ver children

    const current = buildCurrentUrl(pathname, search);
    const next = encodeURIComponent(current);
    router.replace(`/login?next=${next}`);
  }, [authed, pathProtected, pathname, search, router]);

  // Evitar “parpadeo” en páginas protegidas mientras se evalúa auth
  if (authed === null && pathProtected) {
    return <div className="min-h-[30vh]" />; // skeleton mínimo, sin layout shift llamativo
  }

  return <>{children}</>;
}

