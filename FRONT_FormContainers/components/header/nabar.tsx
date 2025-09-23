"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { adminTokenKey, clearAdminToken, adminLogout } from "@/lib/api.admin";

/**
 * Navbar robusta y auto-suficiente:
 * - Detecta auth desde cookies (sessionid, is_staff, auth_token) y LS (admin_token).
 * - Recalcula en: mount, cambio de ruta, storage/focus/visibility.
 * - Muestra "Admin" solo si is_staff=1 o (hay token y no existe is_staff=0).
 * - Cierra dropdown en click fuera, scroll, resize, ESC.
 * - No redirige por su cuenta; el caller decide.
 */

const baseLink =
  "inline-flex items-center gap-2 px-3 py-2 text-sm md:text-base rounded-md border-b-2 border-transparent text-slate-700 dark:text-bone hover:bg-slate-50/60 dark:hover:bg-white/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/30";
const activeLink = "text-sky-600 dark:text-sky-400 border-current";

const Q_FASE1 = process.env.NEXT_PUBLIC_Q_FASE1_ID || null;

// ---- cookies ----
function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}
function truthyCookie(v: string | null): boolean {
  if (!v) return false;
  const s = v.trim().toLowerCase();
  return s === "1" || s === "true" || s === "yes" || s === "on";
}

export default function Navbar() {
  const pathname = usePathname();

  // ===== Auth (cookies/LS) =====
  const [isAuth, setIsAuth] = useState(false);
  const [isStaff, setIsStaff] = useState(false);
  const [username, setUsername] = useState<string | null>(null);

  const recomputeAuth = () => {
    const lsToken =
      typeof localStorage !== "undefined" ? localStorage.getItem(adminTokenKey) : null;
    const cookieToken = getCookie("auth_token");
    const sessionId = getCookie("sessionid");
    const cookieStaff = getCookie("is_staff");
    const nameCookie = getCookie("auth_username");
    const nameLS =
      typeof localStorage !== "undefined" ? localStorage.getItem("auth_username") : null;

    const authed = !!(lsToken || cookieToken || sessionId);

    let staff = false;
    if (cookieStaff !== null) {
      staff = truthyCookie(cookieStaff);
    } else if (lsToken || cookieToken) {
      staff = true; // optimista hasta que whoami precise
    }

    const name =
      (nameCookie && nameCookie.trim()) ||
      (nameLS && nameLS.trim()) ||
      null;

    setIsAuth(authed);
    setIsStaff(staff);
    setUsername(name);
  };

  // Montaje + listeners globales
  useEffect(() => {
    recomputeAuth();

    const onStorage = (e: StorageEvent) => {
      if (!e.key || e.key === adminTokenKey || e.key === "auth_username") recomputeAuth();
    };
    const onFocus = () => recomputeAuth();
    const onVis = () => document.visibilityState === "visible" && recomputeAuth();

    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVis);

    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, []);

  // Recalcular al cambiar de ruta
  useEffect(() => {
    recomputeAuth();
  }, [pathname]);

  // ===== Navigation state =====
  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  const hrefFormulario = Q_FASE1
    ? `/formulario?questionnaire_id=${Q_FASE1}`
    : "/seleccion-formulario";

  const formularioIsActive =
    isActive("/formulario") || isActive("/fase1") || isActive("/seleccion-formulario");

  const adminHref = "/admin";
  const adminIsActive = isActive("/admin");

  // ===== Dropdown =====
  const [open, setOpen] = useState(false);
  const [menuPos, setMenuPos] = useState<{ top: number; left: number; minWidth: number } | null>(null);
  const btnRef = useRef<HTMLButtonElement | null>(null);

  function toggleMenu() {
    setOpen((v) => {
      const next = !v;
      if (next && btnRef.current) {
        const r = btnRef.current.getBoundingClientRect();
        const minWidth = Math.max(220, r.width);
        const viewportW = window.innerWidth;
        const left = Math.min(Math.max(8, r.right - minWidth), viewportW - minWidth - 8);
        setMenuPos({ top: r.bottom + 8, left, minWidth });
      }
      return next;
    });
  }

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!open) return;
      const t = e.target as Node;
      if (btnRef.current?.contains(t)) return;
      setOpen(false);
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    function onScroll() {
      if (open) setOpen(false);
    }
    document.addEventListener("click", onDocClick);
    document.addEventListener("keydown", onEsc);
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onScroll);
    return () => {
      document.removeEventListener("click", onDocClick);
      document.removeEventListener("keydown", onEsc);
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onScroll);
    };
  }, [open]);

  const loginHref = `/login?next=${encodeURIComponent(pathname || "/")}`;

  async function onLogout() {
    try {
      await adminLogout(); // intenta cerrar sesión en back (si existe)
    } finally {
      try { clearAdminToken(); } catch {}
      document.cookie = "is_staff=0; Path=/; Max-Age=60; SameSite=Lax";
      window.location.replace(loginHref); // sin loop (replace)
    }
  }

  return (
    <header className="w-full border-b bg-background">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <nav className="flex items-center gap-2 md:gap-3 whitespace-nowrap overflow-x-auto">
          <Link
            href="/"
            className={`${baseLink} ${isActive("/") ? activeLink : ""}`}
            aria-current={isActive("/") ? "page" : undefined}
            title="Inicio"
          >
            Inicio
          </Link>

          <Link
            href={hrefFormulario}
            className={`${baseLink} ${formularioIsActive ? activeLink : ""}`}
            aria-current={formularioIsActive ? "page" : undefined}
            title={Q_FASE1 ? "Abrir Fase 1" : "Seleccionar formulario"}
          >
            Formulario
          </Link>

          <Link
            href="/panel"
            className={`${baseLink} ${isActive("/panel") ? activeLink : ""}`}
            aria-current={isActive("/panel") ? "page" : undefined}
          >
            Panel
          </Link>

          <Link
            href="/historial"
            className={`${baseLink} ${isActive("/historial") ? activeLink : ""}`}
            aria-current={isActive("/historial") ? "page" : undefined}
          >
            Historial
          </Link>

          {isStaff && (
            <Link
              href={adminHref}
              prefetch={false}
              className={`${baseLink} ${adminIsActive ? activeLink : ""}`}
              aria-current={adminIsActive ? "page" : undefined}
              title="Administración"
            >
              Admin
            </Link>
          )}
        </nav>

        <div className="flex items-center gap-2">
          {isAuth ? (
            <>
              <button
                ref={btnRef}
                type="button"
                className={`${baseLink} ${open ? activeLink : ""}`}
                aria-haspopup="menu"
                aria-expanded={open}
                onClick={toggleMenu}
                title={username || "Cuenta"}
              >
                <span className="inline-grid place-items-center w-6 h-6 rounded-full bg-sky-500/10 text-sky-600 font-semibold">
                  {(username || "U").slice(0, 1).toUpperCase()}
                </span>
                <span className="font-medium">{username || "Usuario"}</span>
                <svg className="w-4 h-4 opacity-70" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path d="M5.5 7.5l4.5 4.5 4.5-4.5" />
                </svg>
              </button>

              {open && menuPos && (
                <div
                  role="menu"
                  style={{ position: "fixed", top: menuPos.top, left: menuPos.left, minWidth: menuPos.minWidth }}
                  className="rounded-xl border border-slate-200/70 dark:border-white/10 bg-white dark:bg-slate-900 shadow-lg overflow-hidden z-[9999]"
                >
                  <div className="px-3 py-2 text-xs text-slate-500">Sesión iniciada</div>

                  <Link
                    href="/panel"
                    role="menuitem"
                    className="block px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-white/5"
                    onClick={() => setOpen(false)}
                  >
                    Panel
                  </Link>
                  <Link
                    href="/historial"
                    role="menuitem"
                    className="block px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-white/5"
                    onClick={() => setOpen(false)}
                  >
                    Historial
                  </Link>

                  {isStaff && (
                    <Link
                      href="/admin"
                      role="menuitem"
                      className="block px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-white/5"
                      onClick={() => setOpen(false)}
                    >
                      Administración
                    </Link>
                  )}

                  <div className="my-1 h-px bg-slate-100 dark:bg-white/10" />

                  <button
                    role="menuitem"
                    className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-white/5"
                    onClick={onLogout}
                  >
                    Cerrar sesión
                  </button>
                </div>
              )}
            </>
          ) : (
            <Link
              href={loginHref}
              className={`${baseLink} ${isActive("/login") ? activeLink : ""}`}
              aria-current={isActive("/login") ? "page" : undefined}
              title="Iniciar sesión"
            >
              Iniciar sesión
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
