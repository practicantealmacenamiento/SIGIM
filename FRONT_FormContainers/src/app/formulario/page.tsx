"use client";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import Formulario from "@/components/formulario";

const Q_FASE1 = process.env.NEXT_PUBLIC_Q_FASE1_ID || null;

export default function FormularioPage() {
  const sp = useSearchParams();

  // undefined = aún no resolvimos; null/string = resuelto
  const [qid, setQid] = useState<string | null | undefined>(undefined);
  const [sid, setSid] = useState<string | null>(null);

  useEffect(() => {
    // lee de la URL; si no viene, cae al .env de Fase 1
    const q = sp.get("questionnaire_id");
    const s = sp.get("submission_id");
    setQid(q ?? Q_FASE1);
    setSid(s);
  }, [sp]);

  // Evita que el componente Formulario se monte sin ID todavía
  if (qid === undefined) {
    return <div className="p-8 text-lg">Cargando…</div>;
  }

  return <Formulario questionnaire_id={qid} submission_id={sid} />;
}



