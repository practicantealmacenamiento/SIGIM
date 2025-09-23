"use client";

import { useEffect, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";

/* --- helpers cookies muy simples --- */
function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}
function hasAuthHints() {
  // Verificar múltiples señales de autenticación
  const sessionId = getCookie("sessionid");
  const authToken = getCookie("auth_token");
  const isStaff = getCookie("is_staff");
  const authUsername = getCookie("auth_username");
  
  // También verificar localStorage como fallback
  let localToken = null;
  try {
    localToken = typeof localStorage !== "undefined" ? localStorage.getItem("admin_token") : null;
  } catch {}
  
  return !!(sessionId || authToken || isStaff || authUsername || localToken);
}

/* Rutas públicas => NO redirigir nunca. */
const PUBLIC_PREFIXES = [
  "/login",
  "/public",
  "/_next",          // assets
  "/favicon.ico",    // iconos
];

function isPublic(pathname: string) {
  return PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const router = useRouter();
  const redirected = useRef(false);

  useEffect(() => {
    // Nada de redirecciones en rutas públicas
    if (isPublic(pathname)) {
      console.log("[AuthGate] Public route, skipping auth check:", pathname);
      return;
    }

    const authHints = hasAuthHints();
    console.log("[AuthGate] Checking auth for:", pathname, "hasAuthHints:", authHints);

    // Si no hay señales de auth, llevar a la ruta de login unificada (/login)
    if (!authHints && !redirected.current) {
      console.log("[AuthGate] No auth hints, redirecting to login");
      redirected.current = true; // evita múltiples replace en renders sucesivos
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    } else {
      redirected.current = false;
    }
  }, [pathname, router]);

  return <>{children}</>;
}
