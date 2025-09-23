"use client";

import { useEffect } from "react";
import { installGlobalAuthFetch, fetchWhoAmI } from "@/lib/api.admin";
import { setCookie } from "@/lib/http";

export default function ClientAuthBootstrap() {
  useEffect(() => {
    installGlobalAuthFetch();

    // Sincroniza cookie de rol para la nabar (no es crítico si falla)
    (async () => {
      try {
        const me = await fetchWhoAmI();
        setCookie("is_staff", me?.is_staff ? "1" : "0", 7);
      } catch { /* ignore */ }
    })();
  }, []);

  return null;
}

