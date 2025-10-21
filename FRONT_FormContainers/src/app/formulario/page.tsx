"use client";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Formulario from "@/components/formulario";

// ==============================================
// Formulario — Page (app/formulario/page.tsx)
// ----------------------------------------------
// - Resuelve questionnaire_id y submission_id desde la URL
// - Fallback a NEXT_PUBLIC_Q_FASE1_ID cuando no viene en la URL
// - Estados de carga/empty robustos y consistentes con el resto del Admin
// - Sin montar <Formulario> hasta tener un questionnaire_id resuelto
// ==============================================

const Q_FASE1 = process.env.NEXT_PUBLIC_Q_FASE1_ID ?? null;

function LoadingScreen() {
  return (
    <div className="min-h-[calc(100vh-80px)] grid place-items-center bg-gradient-to-b from-slate-50 to-white dark:from-[#0b1220] dark:to-[#0b1220]">
      <div className="w-full max-w-[680px] px-6">
        <div className="rounded-2xl border border-slate-200/70 dark:border-white/10 bg-white/90 dark:bg-slate-900/90 shadow-lg backdrop-blur p-6">
          <div className="h-6 w-40 rounded bg-slate-100 dark:bg-white/10 animate-pulse mb-4" />
          <div className="space-y-2">
            <div className="h-4 w-3/4 rounded bg-slate-100 dark:bg-white/10 animate-pulse" />
            <div className="h-4 w-2/3 rounded bg-slate-100 dark:bg-white/10 animate-pulse" />
            <div className="h-4 w-1/2 rounded bg-slate-100 dark:bg-white/10 animate-pulse" />
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="min-h-[calc(100vh-80px)] grid place-items-center bg-gradient-to-b from-slate-50 to-white dark:from-[#0b1220] dark:to-[#0b1220]">
      <div className="w-full max-w-[680px] px-6">
        <div className="rounded-2xl border border-amber-200/70 dark:border-amber-900/40 bg-amber-50/70 dark:bg-amber-900/20 text-amber-900 dark:text-amber-200 shadow p-6">
          <h2 className="text-lg font-semibold mb-1">No se pudo iniciar el formulario</h2>
          <p className="text-sm opacity-90">{message}</p>
          <p className="text-xs opacity-70 mt-3">
            Suministra <span className="font-mono">questionnaire_id</span> en la URL,
            por ejemplo: <span className="font-mono">/formulario?questionnaire_id=&lt;UUID&gt;</span>
          </p>
        </div>
      </div>
    </div>
  );
}

function FormularioContent() {
  const sp = useSearchParams();

  // undefined = aún no resolvimos; null/string = resuelto
  const [qid, setQid] = useState<string | null | undefined>(undefined);
  const [sid, setSid] = useState<string | null>(null);

  useEffect(() => {
    // Lee de la URL; si no viene, cae al .env de Fase 1
    const q = sp.get("questionnaire_id");
    const s = sp.get("submission_id");
    // Normalizamos vacío a null
    setQid(q ? q : Q_FASE1);
    setSid(s || null);
  }, [sp]);

  // Evita que el componente Formulario se monte sin ID todavía
  if (qid === undefined) {
    return <LoadingScreen />;
  }

  // Si no logramos resolver un questionnaire_id, mostramos empty state
  if (qid === null) {
    return (
      <EmptyState message={`No hay questionnaire_id en la URL ni NEXT_PUBLIC_Q_FASE1_ID configurado en el entorno.`} />
    );
  }

  return <Formulario questionnaire_id={qid} submission_id={sid} />;
}

export default function FormularioPage() {
  return (
    <Suspense fallback={<LoadingScreen />}>
      <FormularioContent />
    </Suspense>
  );
}




