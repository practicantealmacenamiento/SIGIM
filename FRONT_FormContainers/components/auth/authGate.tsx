"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { whoami } from "@/lib/auth";

type Props = { children: React.ReactNode; adminOnly?: boolean; redirectTo?: string };

/**
 * Bloquea la vista hasta resolver auth; evita loops y parpadeos.
 * - Si adminOnly, además exige is_staff.
 * - redirectTo por defecto: "/login"
 */
export default function AuthGate({ children, adminOnly = false, redirectTo = "/login" }: Props) {
  const router = useRouter();
  const [ok, setOk] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const me = await whoami();
        if (!me.is_authenticated) {
          if (alive) router.replace(redirectTo);
          return;
        }
        if (adminOnly && !me.is_staff) {
          if (alive) router.replace(redirectTo);
          return;
        }
        if (alive) setOk(true);
      } catch {
        if (alive) router.replace(redirectTo);
      }
    })();
    return () => { alive = false; };
  }, [adminOnly, redirectTo, router]);

  if (!ok) return null; // o un skeleton
  return <>{children}</>;
}
