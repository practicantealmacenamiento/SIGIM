"use client";

import { useEffect } from "react";
import { installGlobalAuthFetch, fetchWhoAmI, isAuthenticated, purgeLegacyAuthArtifacts } from "@/lib/api.admin";

const USERNAME_KEY = process.env.NEXT_PUBLIC_AUTH_USERNAME_KEY || "auth:username";
const STAFF_KEY = process.env.NEXT_PUBLIC_AUTH_IS_STAFF_KEY || "auth:is_staff";

/**
 * Bootstrap de auth (cliente):
 * - Instala fetch con Bearer.
 * - Si hay token: sincroniza username/is_staff en localStorage.
 * - Si NO hay token: borra rastros legacy (cookies antiguas).
 * - ⚠️ Ya NO crea cookies.
 */
export default function ClientAuthBootstrap() {
  useEffect(() => {
    installGlobalAuthFetch();

    (async () => {
      if (!isAuthenticated()) {
        // sin token => limpia restos
        purgeLegacyAuthArtifacts();
        if (typeof localStorage !== "undefined") {
          localStorage.removeItem(USERNAME_KEY);
          localStorage.removeItem(STAFF_KEY);
        }
        return;
      }

      try {
        const me = await fetchWhoAmI();
        if (typeof localStorage !== "undefined") {
          if (me?.username) localStorage.setItem(USERNAME_KEY, String(me.username));
          localStorage.setItem(STAFF_KEY, me?.is_staff ? "1" : "0");
        }
      } catch {
        // si whoami falla, no rompemos
      }
    })();
  }, []);

  return null;
}
