"use client";

import { useEffect } from "react";
import {
  installGlobalAuthFetch,
  fetchWhoAmI,
  isAuthenticated,
  purgeLegacyAuthArtifacts,
} from "@/lib/api.admin";

/**
 * ClientAuthBootstrap — Inicializa el entorno de autenticación en el cliente.
 *
 * Qué hace al montarse:
 * 1) Instala un `fetch` global con inyección de `Authorization: Bearer …` (installGlobalAuthFetch).
 * 2) Si NO hay token (`isAuthenticated()` = false):
 *    - Borra artefactos legacy (cookies antiguas, etc.) vía `purgeLegacyAuthArtifacts()`.
 *    - Limpia de localStorage: auth:username, auth:is_staff (o claves equivalentes vía ENV).
 * 3) Si HAY token:
 *    - Llama `fetchWhoAmI()` y sincroniza en localStorage:
 *      - username → USERNAME_KEY
 *      - is_staff → STAFF_KEY ("1"/"0")
 *
 * Importante:
 * - No crea ni toca cookies nuevas (solo limpia legacy si no hay token).
 * - Silencia errores en whoami: si falla, no rompe el render ni cambia navegación.
 */

// Claves en localStorage (permiten override por variables públicas de build)
const USERNAME_KEY =
  (process.env.NEXT_PUBLIC_AUTH_USERNAME_KEY as string) || "auth:username";
const STAFF_KEY =
  (process.env.NEXT_PUBLIC_AUTH_IS_STAFF_KEY as string) || "auth:is_staff";

// Utilidad: acceso seguro a localStorage en client-side
function lsSet(key: string, value: string) {
  try {
    if (typeof localStorage !== "undefined") localStorage.setItem(key, value);
  } catch {
    /* ignore storage errors */
  }
}
function lsRemove(key: string) {
  try {
    if (typeof localStorage !== "undefined") localStorage.removeItem(key);
  } catch {
    /* ignore storage errors */
  }
}

export default function ClientAuthBootstrap() {
  useEffect(() => {
    // 1) Instala el fetch global autenticado (idempotente según tu implementación)
    installGlobalAuthFetch();

    // 2) Sincronización de señales de sesión
    (async () => {
      // Sin token → limpiar rastros legacy + limpiar LS y salir
      if (!isAuthenticated()) {
        purgeLegacyAuthArtifacts();
        lsRemove(USERNAME_KEY);
        lsRemove(STAFF_KEY);
        return;
      }

      // Con token → consultar perfil y sincronizar LS (sin romper si falla)
      try {
        const me = await fetchWhoAmI();
        if (me?.username) lsSet(USERNAME_KEY, String(me.username));
        lsSet(STAFF_KEY, me?.is_staff ? "1" : "0");
      } catch {
        // whoami falló: no hacemos nada para no interrumpir la UX
      }
    })();
    // Solo al montar: no depende de props/estado
  }, []);

  // No renderiza UI
  return null;
}

