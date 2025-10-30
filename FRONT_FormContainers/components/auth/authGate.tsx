"use client";

import { ReactNode, useEffect, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useSessionState } from "./useSessionState";

/**
 * AuthGate - Guard de rutas minimalista para App Router (client component).
 *
 * Qué hace:
 * 1) Considera como públicas las rutas explícitas en PUBLIC_ROUTES.
 * 2) Todo lo que empiece por un prefijo en ALWAYS_PROTECTED_PREFIXES se considera protegido.
 * 3) Para rutas protegidas, si no hay sesión, redirige a /login?next=.
 * 4) Usa `useSessionState` para reaccionar a cambios locales y entre pestañas.
 *
 * Importante:
 * - No consulta servidor; confía en el token del login unificado.
 * - Evita parpadeos en páginas protegidas hasta tener lectura inicial.
 */

const PUBLIC_ROUTES = new Set<string>(["/", "/login"]);

const ALWAYS_PROTECTED_PREFIXES = [
  "/admin",
  "/panel",
  "/historial",
  "/formulario",
] as const;

function isPublicRoute(pathname: string | null) {
  if (!pathname) return true;
  return PUBLIC_ROUTES.has(pathname);
}

function isUnderProtectedPrefix(pathname: string | null) {
  if (!pathname) return false;
  return ALWAYS_PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
}

function buildCurrentUrl(pathname: string | null, search: URLSearchParams | null) {
  const base = pathname || "/";
  const query = search?.toString();
  return query && query.length ? `${base}?${query}` : base;
}

export default function AuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const session = useSessionState();

  const pathProtected = useMemo(() => {
    if (!pathname) return false;
    if (isPublicRoute(pathname)) return false;
    return isUnderProtectedPrefix(pathname);
  }, [pathname]);

  useEffect(() => {
    if (!session.ready) return;
    if (!pathProtected) return;
    if (session.authed) return;

    const current = buildCurrentUrl(pathname, search);
    const next = encodeURIComponent(current);
    router.replace(`/login?next=${next}`);
  }, [session.ready, session.authed, pathProtected, pathname, search, router]);

  if (!session.ready && pathProtected) {
    return <div className="min-h-[30vh]" />;
  }

  return <>{children}</>;
}
