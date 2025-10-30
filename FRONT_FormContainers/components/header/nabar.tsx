"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { clearAuthToken } from "@/lib/api.admin";
import { useSessionState } from "../auth/useSessionState";

const baseLink =
  "inline-flex items-center gap-2 px-3 py-2 text-sm md:text-base rounded-md border-b-2 border-transparent text-slate-700 dark:text-bone hover:bg-slate-50/60 dark:hover:bg-white/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/30";
const activeLink = "text-sky-600 dark:text-sky-400 border-current";

const Q_FASE1 = process.env.NEXT_PUBLIC_Q_FASE1_ID || null;

type NavItem = {
  href: string;
  label: string;
  title: string;
  active: boolean;
  prefetch?: boolean;
};

export default function Navbar() {
  const pathname = usePathname();
  const session = useSessionState();
  const isAuth = session.ready ? session.authed : false;
  const isStaff = session.ready ? session.isStaff : false;
  const username = session.ready ? session.username : null;

  const isActive = useCallback(
    (href: string) => {
      if (!pathname) return false;
      return pathname === href || pathname.startsWith(`${href}/`);
    },
    [pathname],
  );

  const hrefFormulario = Q_FASE1
    ? `/formulario?questionnaire_id=${Q_FASE1}`
    : "/formulario";

  const homeActive = isActive("/");
  const formularioActive = isActive("/formulario");
  const panelActive = isActive("/panel");
  const historialActive = isActive("/historial");
  const adminHref = "/admin";
  const adminActive = isActive(adminHref);

  const navItems = useMemo<NavItem[]>(
    () => {
      const items: NavItem[] = [
        {
          href: "/",
          label: "Inicio",
          title: "Inicio",
          active: homeActive,
        },
        {
          href: hrefFormulario,
          label: "Formulario",
          title: "Completar formulario",
          active: formularioActive,
        },
        {
          href: "/panel",
          label: "Panel",
          title: "Panel principal",
          active: panelActive,
        },
        {
          href: "/historial",
          label: "Historial",
          title: "Historial de formularios",
          active: historialActive,
        },
      ];

      if (isAuth && isStaff) {
        items.push({
          href: adminHref,
          label: "Admin",
          title: "Administracion",
          active: adminActive,
          prefetch: false,
        });
      }

      return items;
    },
    [
      adminActive,
      adminHref,
      formularioActive,
      hrefFormulario,
      historialActive,
      homeActive,
      isAuth,
      isStaff,
      panelActive,
    ],
  );

  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [userMenuPos, setUserMenuPos] = useState<{
    top: number;
    left: number;
    minWidth: number;
  } | null>(null);
  const userButtonRef = useRef<HTMLButtonElement | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setUserMenuOpen(false);
    setMobileOpen(false);
  }, [pathname]);

  const toggleUserMenu = useCallback(() => {
    setMobileOpen(false);
    setUserMenuOpen((current) => {
      const next = !current;
      if (next && userButtonRef.current) {
        const rect = userButtonRef.current.getBoundingClientRect();
        const width = Math.max(220, rect.width);
        const viewportWidth = window.innerWidth;
        const left = Math.min(
          Math.max(8, rect.right - width),
          viewportWidth - width - 8,
        );
        setUserMenuPos({
          top: rect.bottom + 8,
          left,
          minWidth: width,
        });
      }
      return next;
    });
  }, []);

  useEffect(() => {
    function onDocClick(event: MouseEvent) {
      if (!userMenuOpen) return;
      const target = event.target as Node;
      if (userButtonRef.current?.contains(target)) return;
      setUserMenuOpen(false);
    }

    function onEsc(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setUserMenuOpen(false);
      }
    }

    function onScroll() {
      if (userMenuOpen) setUserMenuOpen(false);
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
  }, [userMenuOpen]);

  const toggleMobileMenu = useCallback(() => {
    setMobileOpen((current) => {
      const next = !current;
      if (next) {
        setUserMenuOpen(false);
      }
      return next;
    });
  }, []);

  useEffect(() => {
    if (!mobileOpen) return;

    function onEsc(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMobileOpen(false);
      }
    }

    function onResize() {
      if (window.innerWidth >= 768) {
        setMobileOpen(false);
      }
    }

    window.addEventListener("keydown", onEsc);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("keydown", onEsc);
      window.removeEventListener("resize", onResize);
    };
  }, [mobileOpen]);

  const loginHref = `/login?next=${encodeURIComponent(pathname || "/")}`;

  const onLogout = useCallback(() => {
    clearAuthToken();
    const current =
      typeof window !== "undefined"
        ? encodeURIComponent(window.location.pathname || "/")
        : "%2F";
    window.location.replace(`/login?next=${current}`);
  }, []);

  const closeMobileMenu = useCallback(() => setMobileOpen(false), []);

  return (
    <>
      <div className="flex h-14 items-center justify-between gap-2">
        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 transition hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 md:hidden dark:border-white/10 dark:bg-slate-900 dark:text-bone dark:hover:bg-slate-800"
          onClick={toggleMobileMenu}
          aria-expanded={mobileOpen}
          aria-controls="mobile-nav-panel"
          aria-label={mobileOpen ? "Cerrar menu" : "Abrir menu"}
        >
          <svg
            className="h-5 w-5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          >
            {mobileOpen ? (
              <path d="M6 6l12 12M6 18L18 6" />
            ) : (
              <>
                <path d="M4 6h16" />
                <path d="M4 12h16" />
                <path d="M4 18h16" />
              </>
            )}
          </svg>
        </button>

        <div className="hidden flex-1 items-center justify-center gap-2 overflow-x-auto md:flex md:gap-3">
          {navItems.map(({ href, label, title, active, prefetch }) => (
            <Link
              key={href}
              href={href}
              prefetch={prefetch}
              className={`${baseLink} ${active ? activeLink : ""}`}
              aria-current={active ? "page" : undefined}
              title={title}
            >
              {label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {isAuth ? (
            <>
              <button
                ref={userButtonRef}
                type="button"
                className={`${baseLink} ${userMenuOpen ? activeLink : ""}`}
                aria-haspopup="menu"
                aria-expanded={userMenuOpen}
                onClick={toggleUserMenu}
                title={username || "Cuenta"}
              >
                <span className="inline-grid h-6 w-6 place-items-center rounded-full bg-sky-500/10 text-sky-600 font-semibold">
                  {(username || "U").slice(0, 1).toUpperCase()}
                </span>
                <span className="hidden sm:inline font-medium">
                  {username || "Usuario"}
                </span>
                <svg
                  className="h-4 w-4 opacity-70"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M5.5 7.5l4.5 4.5 4.5-4.5" />
                </svg>
              </button>

              {userMenuOpen && userMenuPos && (
                <div
                  role="menu"
                  style={{
                    position: "fixed",
                    top: userMenuPos.top,
                    left: userMenuPos.left,
                    minWidth: userMenuPos.minWidth,
                  }}
                  className="z-[9999] overflow-hidden rounded-xl border border-slate-200/70 bg-white shadow-lg dark:border-white/10 dark:bg-slate-900"
                >
                  <div className="px-3 py-2 text-xs text-slate-500">
                    Sesion iniciada
                  </div>

                  <Link
                    href="/panel"
                    role="menuitem"
                    className="block px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-white/5"
                    onClick={() => setUserMenuOpen(false)}
                  >
                    Panel
                  </Link>
                  <Link
                    href="/historial"
                    role="menuitem"
                    className="block px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-white/5"
                    onClick={() => setUserMenuOpen(false)}
                  >
                    Historial
                  </Link>

                  {isStaff && (
                    <Link
                      href="/admin"
                      role="menuitem"
                      className="block px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-white/5"
                      onClick={() => setUserMenuOpen(false)}
                    >
                      Administracion
                    </Link>
                  )}

                  <div className="my-1 h-px bg-slate-100 dark:bg-white/10" />

                  <button
                    role="menuitem"
                    className="w-full px-4 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-white/5"
                    onClick={onLogout}
                  >
                    Cerrar sesion
                  </button>
                </div>
              )}
            </>
          ) : (
            <Link
              href={loginHref}
              className={`${baseLink} ${isActive("/login") ? activeLink : ""}`}
              aria-current={isActive("/login") ? "page" : undefined}
              title="Iniciar sesion"
            >
              Iniciar sesion
            </Link>
          )}
        </div>
      </div>

      {mobileOpen && (
        <div className="md:hidden">
          <button
            type="button"
            className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
            onClick={closeMobileMenu}
            aria-hidden="true"
          />
          <div
            id="mobile-nav-panel"
            className="fixed inset-x-4 top-[72px] z-50 rounded-2xl border border-slate-200/70 bg-white p-4 shadow-xl dark:border-white/10 dark:bg-slate-900"
          >
            <div className="space-y-2">
              {navItems.map(({ href, label, title, active, prefetch }) => (
                <Link
                  key={`mobile-${href}`}
                  href={href}
                  prefetch={prefetch}
                  className={`${baseLink} w-full justify-between ${active ? activeLink : ""}`}
                  aria-current={active ? "page" : undefined}
                  title={title}
                  onClick={closeMobileMenu}
                >
                  <span>{label}</span>
                  {active && (
                    <svg
                      className="h-4 w-4 text-sky-500"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path d="M7.5 13l-2.5-2.5 1.41-1.41L7.5 10.17l5.59-5.58L14.5 6l-7 7z" />
                    </svg>
                  )}
                </Link>
              ))}
            </div>

            <div className="mt-4 border-t border-slate-200/70 pt-4 dark:border-white/10">
              {isAuth ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <span className="inline-grid h-9 w-9 place-items-center rounded-full bg-sky-500/10 text-sky-600 font-semibold">
                      {(username || "U").slice(0, 1).toUpperCase()}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-slate-900 dark:text-bone">
                        {username || "Usuario"}
                      </p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Sesion activa
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="w-full rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-200 dark:bg-white/10 dark:text-bone dark:hover:bg-white/20"
                    onClick={() => {
                      closeMobileMenu();
                      onLogout();
                    }}
                  >
                    Cerrar sesion
                  </button>
                </div>
              ) : (
                <Link
                  href={loginHref}
                  className="block rounded-lg bg-sky-600 px-4 py-2 text-center text-sm font-medium text-white transition hover:bg-sky-500"
                  onClick={closeMobileMenu}
                >
                  Iniciar sesion
                </Link>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
