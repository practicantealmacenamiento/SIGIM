"use client";

import { useEffect, useMemo, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useFormFlow } from "./useFormFlow";
import Header from "./headerForm";
import QuestionCard from "./questionCard";
import type { Item } from "@/types/form";

const Q_FASE1 = process.env.NEXT_PUBLIC_Q_FASE1_ID || null;
const sanitizeParam = (v?: string | null) =>
  v == null || v === "" || v === "null" || v === "undefined" ? null : v;
const getItemKey = (it: Item) => String((it as any)?.q?.id ?? "unk");

// —— helpers para resumen ——
const getQText = (it: Item) =>
  (it as any)?.q?.text ??
  (it as any)?.q?.label ??
  (it as any)?.q?.title ??
  (it as any)?.q?.name ??
  "(Pregunta)";

const hasTextAns = (it: Item) =>
  Boolean((it as any)?.value) || Boolean((it as any)?.answer_text);

const getTextAns = (it: Item) =>
  String((it as any)?.value ?? (it as any)?.answer_text ?? "").trim();

const hasChoiceAns = (it: Item) =>
  Boolean((it as any)?.answer_choice) ||
  Boolean((it as any)?.selected_choice) ||
  (((it as any)?.choicesSelected?.length ?? 0) > 0) ||
  (((it as any)?.selectedOptions?.length ?? 0) > 0);

const getChoiceText = (it: Item) => {
  const ac = (it as any)?.answer_choice;
  if (ac?.text) return String(ac.text);
  const sc = (it as any)?.selected_choice;
  if (sc?.text) return String(sc.text);
  const arr = (it as any)?.choicesSelected ?? (it as any)?.selectedOptions;
  if (Array.isArray(arr) && arr.length) return arr.map((x: any) => x?.text ?? x?.label ?? x?.title ?? "").filter(Boolean).join(", ");
  return "";
};

const hasFileAns = (it: Item) =>
  (((it as any)?.files?.length ?? 0) > 0) ||
  Boolean((it as any)?.file || (it as any)?.file_url || (it as any)?.filePath || (it as any)?.answer_file_path);

const getFirstFileUrl = (it: Item) => {
  const farr = (it as any)?.files;
  if (Array.isArray(farr) && farr.length) return farr[0]?.url ?? farr[0];
  return (it as any)?.file_url ?? (it as any)?.file ?? (it as any)?.filePath ?? (it as any)?.answer_file_path ?? null;
};

const isAnswered = (it: Item) => hasTextAns(it) || hasChoiceAns(it) || hasFileAns(it);

function FormularioContent(props: { questionnaire_id?: string | null; submission_id?: string | null }) {
  const { questionnaire_id, submission_id } = props;
  const router = useRouter();
  const search = useSearchParams();

  const qid = useMemo(() => sanitizeParam(questionnaire_id ?? search.get("questionnaire_id")), [questionnaire_id, search]);
  const sidFromUrl = useMemo(() => sanitizeParam(submission_id ?? search.get("submission_id")), [submission_id, search]);

  const {
    submissionId,
    items, setItems,
    mostrarResumen, setMostrarResumen,
    finalizado, loading, sending, error,
    respondidas, lastRef,
    submitOne, setVal, onEnter, onSelectChoice,
    onFilesChange, removeFile,
    answerPreview, onEnviar, retryOCR,
    setActor,
    total,
  } = useFormFlow(qid, sidFromUrl);

  useEffect(() => {
    if (!qid) return;
    const curQ = search.get("questionnaire_id");
    if (curQ !== qid) {
      const qs = new URLSearchParams(Array.from(search.entries()));
      qs.set("questionnaire_id", qid);
      router.replace(`/formulario?${qs.toString()}`, { scroll: false });
    }
  }, [qid]);

  useEffect(() => {
    if (!submissionId) return;
    const curS = search.get("submission_id");
    if (curS !== submissionId) {
      const qs = new URLSearchParams(Array.from(search.entries()));
      if (qid) qs.set("questionnaire_id", qid);
      qs.set("submission_id", submissionId);
      router.replace(`/formulario?${qs.toString()}`, { scroll: false });
    }
  }, [submissionId, qid]);

  const openEditorAt = useCallback((idx: number) => {
    setMostrarResumen(false);
    setItems(prev => {
      if (!prev[idx]) return prev;
      const next = prev.slice(0, idx + 1).map((it, j) =>
        j === idx ? { ...it, editing: true, saved: false } : it
      );
      const qid = String((prev[idx] as any).q.id);
      setTimeout(() => {
        const el = document.querySelector<HTMLElement>(`[data-qid="${qid}"]`);
        el?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 50);
      return next;
    });
  }, []);

  if (!qid) {
    return (
      <main className="min-h-screen px-6 md:px-8 py-10">
        <div className="max-w-3xl mx-auto">
          <Header respondidas={respondidas} total={total} fase="entrada" regulador="Prebel" />
          <div className="mt-8 p-8 border rounded-xl shadow bg-white dark:bg-slate-800">
            <h2 className="text-2xl font-semibold">Selecciona un formulario para continuar</h2>
            <p className="mt-2 text-base text-slate-600 dark:text-white/70">
              No encontramos el identificador del cuestionario.
            </p>
            {Q_FASE1 && (
              <button
                onClick={() => router.push(`/formulario?questionnaire_id=${Q_FASE1}`)}
                className="mt-6 px-5 py-2.5 rounded-xl bg-skyBlue text-white font-medium hover:bg-skyBlue/90"
              >
                Usar formulario de Fase 1
              </button>
            )}
          </div>
        </div>
      </main>
    );
  }

  if (loading) {
    return (
      <main className="min-h-screen px-6 md:px-8 py-10">
        <div className="max-w-3xl mx-auto">
          <Header respondidas={respondidas} total={total} fase="entrada" regulador="Prebel" />
          <div className="mt-8 p-6 text-lg">Cargando…</div>
        </div>
      </main>
    );
  }

  // Si el formulario está finalizado, mostrar mensaje de éxito
  if (finalizado) {
    return (
      <main className="min-h-screen px-6 md:px-8 py-10">
        <div className="max-w-3xl mx-auto">
          <div className="text-center p-8 border rounded-xl shadow bg-white dark:bg-slate-800">
            <div className="text-6xl mb-4">✅</div>
            <h2 className="text-2xl font-semibold mb-4">¡Formulario enviado exitosamente!</h2>
            <p className="text-base text-slate-600 dark:text-white/70 mb-6">
              Tu formulario ha sido procesado correctamente. Puedes realizar otro formulario o ir al panel de control.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={() => router.push('/formulario')}
                className="px-6 py-3 rounded-xl bg-skyBlue text-white font-medium hover:bg-skyBlue/90"
              >
                Realizar otro formulario
              </button>
              <button
                onClick={() => router.push('/panel')}
                className="px-6 py-3 rounded-xl border border-slate-300 dark:border-white/20 bg-white dark:bg-slate-800 text-slate-800 dark:text-white hover:bg-slate-50 dark:hover:bg-white/5"
              >
                Ir al panel de control
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  // ⬇️ Ya NO bloqueamos el flujo si hay error. Solo mostramos un aviso arriba.
  return (
    <main className="min-h-screen pb-28 px-6 md:px-8 pt-6">
      <div className="max-w-3xl mx-auto">
        <Header respondidas={respondidas} total={total} fase="entrada" regulador="Prebel" />

        {error && (
          <div className="mt-4 rounded-lg border border-amber-300/60 bg-amber-50/70 dark:bg-amber-400/10 dark:border-amber-300/20 text-amber-900 dark:text-amber-200 px-4 py-3" role="alert">
            <span className="text-sm">⚠️ {error}</span>
          </div>
        )}

        {/* Preguntas */}
        <div className="mt-6 space-y-6">
          {items.map((it, idx) => (
            <QuestionCard
              key={getItemKey(it)}
              it={it}
              idx={idx}
              isLast={idx === items.length - 1}
              lastRef={lastRef as any}
              sending={sending}
              setVal={setVal}
              onSelectChoice={onSelectChoice}
              onEnter={onEnter}
              onFilesChange={onFilesChange}
              removeFile={removeFile}
              submitOne={submitOne}
              setItems={setItems}
              retryOCR={retryOCR}
              setActor={setActor}
              // ⬇️ Pasamos el error SOLO a la tarjeta activa para pintarlo ahí
              errorMsg={idx === items.length - 1 ? (error || null) : null}
            />
          ))}
        </div>
      </div>

      {/* Barra de acciones fija */}
      <div className="fixed bottom-0 inset-x-0 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-white/10 px-6 md:px-8 py-4 shadow-md z-50">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <span className="text-sm text-slate-500 dark:text-white/60">
            {respondidas} de {total} respondidas
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setMostrarResumen(true)}
              className="min-h-[40px] px-4 py-2 rounded-lg border border-slate-300 dark:border-white/10 bg-white dark:bg-white/5 text-slate-800 dark:text-white hover:opacity-90"
            >
              Ver resumen
            </button>
            <button
              onClick={onEnviar}
              disabled={sending || respondidas < total}
              className="min-h-[40px] px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-60"
            >
              {sending ? "Enviando…" : "Enviar"}
            </button>
          </div>
        </div>
      </div>

      {/* Modal de Resumen (sin cambios funcionales) */}
      {mostrarResumen && (
        <div
          className="fixed inset-0 z-[60] bg-black/50 flex items-end md:items-center justify-center p-0 md:p-6"
          role="dialog"
          aria-modal="true"
          onClick={() => setMostrarResumen(false)}
        >
          <div
            className="w-full md:max-w-3xl bg-white dark:bg-slate-900 rounded-t-2xl md:rounded-2xl shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="px-4 md:px-6 py-4 border-b border-slate-200 dark:border-white/10 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Resumen de respuestas</h3>
                <p className="text-sm text-slate-600 dark:text-white/60">
                  {respondidas} de {total} respondidas
                </p>
              </div>
              <button
                className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-white/20 hover:bg-slate-50 dark:hover:bg-white/5"
                onClick={() => setMostrarResumen(false)}
              >
                ✕ Cerrar
              </button>
            </div>

            {/* Body */}
            <div className="max-h-[70vh] overflow-auto p-4 md:p-6">
              {/* Pendientes */}
              <section className="mb-6">
                <h4 className="text-sm font-semibold text-amber-600 dark:text-amber-400 mb-2">
                  Pendientes
                </h4>
                <ul className="space-y-2">
                  {items.map((it, idx) =>
                    !isAnswered(it) ? (
                      <li key={`p-${getItemKey(it)}`} className="p-3 rounded-xl border border-amber-200 dark:border-amber-300/20 bg-amber-50/60 dark:bg-amber-400/10">
                        <div className="text-sm font-medium">{getQText(it)}</div>
                        <div className="mt-2 flex gap-2">
                          <button
                            onClick={() => openEditorAt(idx)}
                            className="px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-white/20 hover:bg-slate-50 dark:hover:bg-white/5"
                          >
                            Editar
                          </button>
                        </div>
                      </li>
                    ) : null
                  )}
                </ul>
                {items.every(isAnswered) && (
                  <div className="text-sm text-slate-500">No hay preguntas pendientes 🎉</div>
                )}
              </section>

              {/* Contestadas */}
              <section>
                <h4 className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mb-2">
                  Contestadas
                </h4>
                <ul className="space-y-2">
                  {items.map((it, idx) =>
                    isAnswered(it) ? (
                      <li key={`r-${getItemKey(it)}`} className="p-3 rounded-xl border border-slate-200 dark:border-white/10">
                        <div className="text-sm font-medium">{getQText(it)}</div>

                        <div className="mt-1 text-sm text-slate-700 dark:text-white/80 whitespace-pre-wrap break-words">
                          {/* preview simple para texto/opción/archivo */}
                          {(it as any)?.answer_choice?.text ??
                            (it as any)?.selected_choice?.text ??
                            (getTextAns(it) ||
                            (hasFileAns(it) ? "(adjunto)" : "(vacío)"))}
                        </div>

                        {hasFileAns(it) && (
                          <div className="mt-2">
                            <a
                              href={getFirstFileUrl(it) || "#"}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border hover:bg-slate-50 dark:hover:bg-white/5"
                            >
                              📄 Ver archivo
                            </a>
                          </div>
                        )}

                        <div className="mt-2 flex gap-2">
                          <button
                            onClick={() => openEditorAt(idx)}
                            className="px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-white/20 hover:bg-slate-50 dark:hover:bg-white/5"
                          >
                            Editar
                          </button>
                        </div>
                      </li>
                    ) : null
                  )}
                </ul>
              </section>
            </div>

            {/* Footer */}
            <div className="px-4 md:px-6 py-3 border-t border-slate-200 dark:border-white/10 flex items-center justify-end gap-2">
              <button
                onClick={() => setMostrarResumen(false)}
                className="px-4 py-2 rounded-lg border border-slate-300 dark:border-white/20 hover:bg-slate-50 dark:hover:bg-white/5"
              >
                Cerrar
              </button>
              <button
                onClick={onEnviar}
                disabled={sending || respondidas < total}
                className="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-60"
              >
                {sending ? "Enviando…" : "Enviar ahora"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default function Formulario(props: { questionnaire_id?: string | null; submission_id?: string | null }) {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
        <div className="mx-auto max-w-4xl px-6 py-8">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded mb-6"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    }>
      <FormularioContent {...props} />
    </Suspense>
  );
}