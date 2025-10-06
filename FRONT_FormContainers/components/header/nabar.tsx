"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  AUTH_TOKEN_KEY,
  clearAuthToken,
  getAuthToken,
} from "@/lib/api.admin";

/**
 * Navbar limpia y auto-suficiente con login unificado:
 * - Solo lee localStorage (nada de cookies).
 * - Claves configurables por ENV para username/is_staff.
 * - Recalcula en: mount, cambio de ruta, eventos de storage/focus/visibility.
 * - Muestra "Admin" si hay token y NO existe is_staff=false (o si is_staff=true).
 */

const baseLink =
  "inline-flex items-center gap-2 px-3 py-2 text-sm md:text-base rounded-md border-b-2 border-transparent text-slate-700 dark:text-bone hover:bg-slate-50/60 dark:hover:bg-white/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/30";
const activeLink = "text-sky-600 dark:text-sky-400 border-current";

const Q_FASE1 = process.env.NEXT_PUBLIC_Q_FASE1_ID || null;

// Claves para username y staff (puedes cambiarlas por ENV sin tocar código)
const USERNAME_KEY =
  process.env.NEXT_PUBLIC_AUTH_USERNAME_KEY || "auth:username";
const STAFF_KEY =
  process.env.NEXT_PUBLIC_AUTH_IS_STAFF_KEY || "auth:is_staff";

function parseBool(v: string | null | undefined): boolean {
  if (!v) return false;
  const s = v.trim().toLowerCase();
  return s === "1" || s === "true" || s === "yes" || s === "on";
}

export default function Navbar() {
  const pathname = usePathname();

  // ===== Auth (solo localStorage) =====
  const [isAuth, setIsAuth] = useState(false);
  const [isStaff, setIsStaff] = useState(false);
  const [username, setUsername] = useState<string | null>(null);

  const recomputeAuth = () => {
    const token =
      typeof localStorage !== "undefined"
        ? localStorage.getItem(AUTH_TOKEN_KEY)
        : null;
    const name =
      typeof localStorage !== "undefined"
        ? localStorage.getItem(USERNAME_KEY)
        : null;
    const staffStored =
      typeof localStorage !== "undefined"
        ? localStorage.getItem(STAFF_KEY)
        : null;

    const authed = !!(token || getAuthToken()); // doble chequeo por seguridad

    // Regla: si STAFF_KEY existe, respétalo; si no existe, y hay token => mostrar Admin optimistamente
    const staff =
      staffStored === null ? !!token : parseBool(staffStored);

    setIsAuth(authed);
    setIsStaff(staff);
    setUsername(name && name.trim() ? name.trim() : null);
  };

  // Montaje + listeners globales
  useEffect(() => {
    recomputeAuth();

    const onStorage = (e: StorageEvent) => {
      // Solo reaccionar si cambian nuestras claves
      if (
        !e.key ||
        e.key === AUTH_TOKEN_KEY ||
        e.key === USERNAME_KEY ||
        e.key === STAFF_KEY
      ) {
        recomputeAuth();
      }
    };
    const onFocus = () => recomputeAuth();
    const onVis = () =>
      document.visibilityState === "visible" && recomputeAuth();

    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVis);

    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVis);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Recalcular al cambiar de ruta y cerrar menú si estaba abierto
  useEffect(() => {
    recomputeAuth();
    setOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  // ===== Helpers de navegación =====
  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  const hrefFormulario = Q_FASE1
    ? `/formulario?questionnaire_id=${Q_FASE1}`
    : "/seleccion-formulario";

  const formularioIsActive =
    isActive("/formulario") ||
    isActive("/fase1") ||
    isActive("/seleccion-formulario");

  const adminHref = "/admin";
  const adminIsActive = isActive("/admin");

  // ===== Dropdown =====
  const [open, setOpen] = useState(false);
  const [menuPos, setMenuPos] = useState<{
    top: number;
    left: number;
    minWidth: number;
  } | null>(null);
  const btnRef = useRef<HTMLButtonElement | null>(null);

  function toggleMenu() {
    setOpen((v) => {
      const next = !v;
      if (next && btnRef.current) {
        const r = btnRef.current.getBoundingClientRect();
        const minWidth = Math.max(220, r.width);
        const viewportW = window.innerWidth;
        const left = Math.min(
          Math.max(8, r.right - minWidth),
          viewportW - minWidth - 8
        );
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

  function onLogout() {
  clearAuthToken();
  const next = typeof window !== "undefined" ? encodeURIComponent(window.location.pathname) : "";
  window.location.replace(`/login?next=${next || "/"}`);
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

          {isAuth && isStaff && (
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
                <svg
                  className="w-4 h-4 opacity-70"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M5.5 7.5l4.5 4.5 4.5-4.5" />
                </svg>
              </button>

              {open && menuPos && (
                <div
                  role="menu"
                  style={{
                    position: "fixed",
                    top: menuPos.top,
                    left: menuPos.left,
                    minWidth: menuPos.minWidth,
                  }}
                  className="rounded-xl border border-slate-200/70 dark:border-white/10 bg-white dark:bg-slate-900 shadow-lg overflow-hidden z-[9999]"
                >
                  <div className="px-3 py-2 text-xs text-slate-500">
                    Sesión iniciada
                  </div>

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
