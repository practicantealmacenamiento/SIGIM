"use client";

import { ReactNode, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { isAuthenticated } from "@/lib/api.admin";

/**
 * Gate minimalista: solo confía en el token del login unificado (localStorage).
 * - Redirige a /login?next=… cuando no hay token en rutas protegidas.
 * - Reacciona a cambios de pestaña/foco y al evento 'storage'.
 */

const PUBLIC_ROUTES = new Set<string>([
  "/", "/login", "/registro", "/recuperar", "/verificacion", "/faq", "/contacto",
]);

// Si quieres que /formulario sea público, quítalo de aquí.
// Por tu comentario, lo BLOQUEAMOS tras logout:
const ALWAYS_PROTECTED_PREFIXES = ["/admin", "/panel", "/historial", "/formulario", "/seleccion-formulario"];

export default function AuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const [authed, setAuthed] = useState<boolean | null>(null);

  const pathProtected = useMemo(() => {
    if (!pathname) return false;
    if (PUBLIC_ROUTES.has(pathname)) return false;
    return ALWAYS_PROTECTED_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/"));
  }, [pathname]);

  // eval inicial + listeners
  useEffect(() => {
    const recompute = () => setAuthed(isAuthenticated());
    recompute();

    const onStorage = (e: StorageEvent) => {
      if (!e.key) return recompute();
      const key = process.env.NEXT_PUBLIC_AUTH_TOKEN_KEY || "auth:access_token";
      if (e.key === key) recompute();
    };
    const onFocus = () => recompute();
    const onVis = () => document.visibilityState === "visible" && recompute();

    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVis);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, []);

  // redirección si corresponde
  useEffect(() => {
    if (authed === null) return; // aún evaluando
    if (!pathProtected) return;  // ruta pública
    if (authed) return;          // ok

    const current = pathname + (search?.toString() ? `?${search.toString()}` : "");
    const next = encodeURIComponent(current);
    router.replace(`/login?next=${next}`);
  }, [authed, pathProtected, pathname, router, search]);

  // Evita “parpadeo” mostrando children antes de decidir
  if (authed === null && pathProtected) {
    return <div className="min-h-[30vh]" />; // skeleton mínimo
  }
  return <>{children}</>;
}
