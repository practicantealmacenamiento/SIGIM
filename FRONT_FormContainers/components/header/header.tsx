"use client";

/**
 * Encabezado principal del sitio.
 * - Sticky + blur para mantenerse visible al desplazar.
 * - Grid de 3 columnas: título / navbar / acciones (tema + logo).
 * - Mantiene el contrato actual: named export `Header`.
 *
 * Accesibilidad:
 * - role="banner" para marcar el encabezado del sitio.
 * - Título visible "SIGIM".
 */

import Navbar from "./nabar";            // ⚠️ Se mantiene el import tal cual para no romper.
import { LogoPrebel } from "./logoPrebel";
import ToggleTheme from "../theme/toggleTheme";

export const Header = () => {
  return (
    <header
      role="banner"
      className="sticky top-0 z-50 w-full border-b border-slate-200/60 dark:border-white/10 bg-white/70 dark:bg-slate-900/70 backdrop-blur-lg"
    >
      <div className="h-16 px-4 md:px-6">
        {/* Layout: [Título] [Navegación flexible] [Acciones] */}
        <div className="grid w-full grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3">
          {/* Título de la aplicación */}
          <h1 className="text-xl md:text-2xl font-bold text-slate-900 dark:text-white">
            SIGIM
          </h1>

          {/* Navegación principal (crece/encoge con el espacio disponible) */}
          <nav aria-label="Navegación principal" className="min-w-0">
            <Navbar />
          </nav>

          {/* Acciones del header: toggle de tema + logo */}
          <div className="flex items-center gap-3 justify-self-end">
            <ToggleTheme />
            <LogoPrebel />
          </div>
        </div>
      </div>
    </header>
  );
};

