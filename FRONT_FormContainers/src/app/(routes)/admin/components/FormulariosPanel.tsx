import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ChangeEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createQuestionnaire,
  deleteQuestionnaire,
  duplicateQuestionnaire,
  getQuestionnaire,
  listQuestionnaires,
  upsertQuestionnaire,
  type AdminQuestionnaire,
} from "@/lib/api.admin";

import { useDebounced } from "./hooks";
import { shell, SearchIcon, Section } from "./ui";
import type { ToastPush } from "./toasts";

type Props = {
  toast: ToastPush;
};

export function FormulariosPanel({ toast }: Props) {
  const router = useRouter();
  const [rows, setRows] = useState<
    { id: string; title: string; version: string; questions: number }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const debounced = useDebounced(query, 250);

  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      setErr(null);
      setLoading(true);
      const data = await listQuestionnaires();
      setRows(data);
    } catch (e: any) {
      setErr(e?.message || "Error listando cuestionarios");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function newQuestionnaire() {
    try {
      setLoading(true);
      const created = await createQuestionnaire({
        title: "Nuevo cuestionario",
        version: "v1",
        timezone: "America/Bogota",
        questions: [],
      });
      const newId = String(
        (created as any)?.id ?? (created as AdminQuestionnaire)?.id ?? ""
      );
      if (!newId) throw new Error("El backend no devolvió un ID para el nuevo cuestionario.");
      toast("ok", "Cuestionario creado");
      router.push(`/admin/${newId}`);
    } catch (e: any) {
      toast("err", e?.message || "No se pudo crear el cuestionario");
    } finally {
      setLoading(false);
    }
  }

  async function onDuplicate(id: string) {
    try {
      const v = prompt("Nueva versión (opcional):") || undefined;
      const res = await duplicateQuestionnaire(id, v);
      toast("ok", "Cuestionario duplicado");
      router.push(`/admin/${res.id}`);
    } catch (e: any) {
      toast("err", e?.message || "No se pudo duplicar");
    }
  }

  async function onDelete(id: string) {
    try {
      if (!confirm("¿Eliminar definitivamente este cuestionario?")) return;
      await deleteQuestionnaire(id);
      toast("ok", "Eliminado correctamente");
      load();
    } catch (e: any) {
      toast("err", e?.message || "No se pudo eliminar");
    }
  }

  async function onExport(id: string) {
    try {
      const q = await getQuestionnaire(id);
      const blob = new Blob([JSON.stringify(q, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${String(q.title || "cuestionario")
        .replace(/[^\w\-]+/g, "_")}_${q.version || "v1"}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast("ok", "Exportado");
    } catch (e: any) {
      toast("err", e?.message || "No se pudo exportar");
    }
  }

  function triggerImport() {
    fileRef.current?.click();
  }

  async function onImportFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text()) as AdminQuestionnaire;
      if (!parsed?.id || !parsed?.title || !parsed?.version || !Array.isArray(parsed?.questions)) {
        throw new Error("JSON inválido (requiere id, title, version, questions[])");
      }
      const saved = await upsertQuestionnaire(parsed);
      toast("ok", "Cuestionario importado");
      router.push(`/admin/${saved.id}`);
    } catch (e: any) {
      toast("err", e?.message || "No se pudo importar");
    }
  }

  const filtered = useMemo(() => {
    const q = debounced.trim().toLowerCase();
    return !q
      ? rows
      : rows.filter(
          (r) =>
            r.title.toLowerCase().includes(q) ||
            r.version.toLowerCase().includes(q)
        );
  }, [rows, debounced]);

  return (
    <Section
      title="Formularios"
      subtitle="Crea, edita, duplica e importa/exporta cuestionarios."
      actions={
        <div className="grid w-full grid-cols-2 md:grid-cols-5 gap-2">
          <div className="relative col-span-2 md:col-span-3">
            <SearchIcon />
            <input
              className={shell.input + " pl-9"}
              placeholder="Buscar por título/versión."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Buscar cuestionarios"
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 hidden md:block">
              <span className={shell.kbd}>/</span>
            </div>
          </div>
          <button onClick={triggerImport} className={shell.btn + " col-span-1"}>
            Importar
          </button>
          <button onClick={newQuestionnaire} className={shell.btnPrimary + " col-span-1"}>
            Nuevo
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={onImportFile}
          />
        </div>
      }
    >
      <div className={`${shell.card} divide-y divide-slate-100 dark:divide-white/10`}>
        <div className="p-4">
          {err && (
            <div className="rounded-xl border border-rose-200/70 dark:border-rose-900/40 bg-rose-50/60 dark:bg-rose-950/30 text-rose-800 dark:text-rose-200 p-4 mb-3">
              {err} <button onClick={load} className="underline ml-2">Reintentar</button>
            </div>
          )}

          {loading ? (
            <ul className="grid gap-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <li
                  key={i}
                  className="p-5 rounded-xl border border-slate-100 dark:border-white/10 bg-slate-50/60 dark:bg-white/5 animate-pulse h-[84px]"
                />
              ))}
            </ul>
          ) : filtered.length === 0 ? (
            <div className="text-sm text-slate-500 py-6">No hay cuestionarios.</div>
          ) : (
            <ul className="grid gap-3">
              {filtered.map((r) => (
                <li
                  key={r.id}
                  className="p-5 rounded-xl border border-slate-100 dark:border-white/10 bg-white dark:bg-slate-900 flex items-center justify-between"
                >
                  <div className="min-w-0">
                    <div className="text-base font-medium truncate">
                      {r.title} <span className="text-slate-500">({r.version})</span>
                    </div>
                    <div className="text-sm text-slate-600 dark:text-white/70">
                      {r.questions} pregunta{r.questions === 1 ? "" : "s"}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Link href={`/admin/${r.id}`} className={shell.btn} title="Editar cuestionario">
                      Editar
                    </Link>
                    <button onClick={() => onExport(r.id)} className={shell.btn} title="Exportar JSON">
                      Exportar
                    </button>
                    <button onClick={() => onDuplicate(r.id)} className={shell.btn} title="Duplicar">
                      Duplicar
                    </button>
                    <button
                      onClick={() => onDelete(r.id)}
                      className={`${shell.btn} hover:bg-rose-50`}
                      title="Eliminar"
                    >
                      Eliminar
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Section>
  );
}
