"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { clearAuthToken, isAuthenticated } from "@/lib/api.admin";

import { ActoresPanel } from "./components/ActoresPanel";
import { FormulariosPanel } from "./components/FormulariosPanel";
import { UsuariosPanel } from "./components/UsuariosPanel";
import { shell } from "./components/ui";
import { useToasts } from "./components/toasts";

type TabKey = "formularios" | "actores" | "usuarios";

const TAB_STORAGE_KEY = "admin.tab";

export default function AdminGeneralPage() {
  const router = useRouter();
  const { push, view } = useToasts();

  const [tab, setTab] = useState<TabKey>(() => {
    if (typeof window === "undefined") return "formularios";
    return (localStorage.getItem(TAB_STORAGE_KEY) as TabKey) || "formularios";
  });

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace(`/login?next=${encodeURIComponent("/admin")}`);
    }
  }, [router]);

  useEffect(() => {
    try {
      localStorage.setItem(TAB_STORAGE_KEY, tab);
    } catch {
      /* noop */
    }
  }, [tab]);

  function logout() {
    if (!confirm("¿Cerrar sesión?")) return;
    clearAuthToken();
    router.replace("/login");
  }

  return (
    <main className={shell.page}>
      <div className={shell.container}>
        <Header tab={tab} onChangeTab={setTab} onLogout={logout} />

        {tab === "formularios" && <FormulariosPanel toast={push} />}
        {tab === "actores" && <ActoresPanel toast={push} />}
        {tab === "usuarios" && <UsuariosPanel toast={push} />}
      </div>

      {view}
    </main>
  );
}

function Header({
  tab,
  onChangeTab,
  onLogout,
}: {
  tab: TabKey;
  onChangeTab: (tab: TabKey) => void;
  onLogout: () => void;
}) {
  return (
    <div className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Administración</h1>
        <p className="text-sm text-slate-500 dark:text-slate-300">
          Gestión de formularios, actores y usuarios.
        </p>
      </div>
      <div className="flex items-center gap-2">
        <nav className={shell.pillTabs} role="tablist" aria-label="Secciones">
          <button
            role="tab"
            aria-selected={tab === "formularios"}
            className={shell.pill(tab === "formularios")}
            onClick={() => onChangeTab("formularios")}
          >
            Formularios
          </button>
          <button
            role="tab"
            aria-selected={tab === "actores"}
            className={shell.pill(tab === "actores")}
            onClick={() => onChangeTab("actores")}
          >
            Actores
          </button>
          <button
            role="tab"
            aria-selected={tab === "usuarios"}
            className={shell.pill(tab === "usuarios")}
            onClick={() => onChangeTab("usuarios")}
          >
            Usuarios
          </button>
        </nav>
        <button onClick={onLogout} className={shell.btn} title="Cerrar sesión">
          Cerrar sesión
        </button>
      </div>
    </div>
  );
}
