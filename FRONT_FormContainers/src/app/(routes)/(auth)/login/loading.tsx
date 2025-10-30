/*Componentes de carga para la pagina de login mientras se autentica el usuario*/

"use client";

import { CARD } from "@/lib/ui";

export default function LoginLoading() {
  return (
    <main className="min-h-[calc(100vh-80px)] w-full px-6 md:px-8 py-10">
      <div className="mx-auto max-w-[520px]">
        <div className={`${CARD} p-8 md:p-10`}>
          <h1 className="text-2xl md:text-3xl font-semibold mb-6">Acceso</h1>
          <div className="space-y-4 animate-pulse">
            <div className="h-4 rounded bg-gray-200/70 dark:bg-white/10" />
            <div className="h-10 rounded bg-gray-200/70 dark:bg-white/10" />
            <div className="h-4 rounded bg-gray-200/70 dark:bg-white/10" />
            <div className="h-10 rounded bg-gray-200/70 dark:bg-white/10" />
            <div className="h-11 rounded bg-gray-200/70 dark:bg-white/10" />
          </div>
        </div>
      </div>
    </main>
  );
}
