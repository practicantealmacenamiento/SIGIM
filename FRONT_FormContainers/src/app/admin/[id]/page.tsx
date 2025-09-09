"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getQuestionnaire,
  upsertQuestionnaire,
  reorderQuestions,
  installGlobalAuthFetch,
  type AdminQuestionnaire,
  type AdminQuestion,
  type AdminChoice,
} from "@/lib/api.admin";
import { CARD, INPUT, radioCls } from "@/lib/ui";

const TYPES: AdminQuestion["type"][] = ["text", "number", "date", "file", "choice"];
const FILE_MODES = ["image_only", "image_ocr", "ocr_only"] as const;
const TAGS = ["none", "placa", "contenedor", "precinto", "proveedor", "transportista", "receptor"] as const;


export default function AdminEditorPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [orig, setOrig] = useState<AdminQuestionnaire | null>(null);
  const [qn, setQn] = useState<AdminQuestionnaire | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const firstErrorRef = useRef<HTMLDivElement | null>(null);

  // ---------- Ensure auth headers ----------
  useEffect(() => {
    installGlobalAuthFetch();
  }, []);

  // ---------- Load (with draft fallback) ----------
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setErr(null);
        setLoading(true);
        const draftKey = `draft:${id}`;
        const draft = typeof window !== "undefined" ? sessionStorage.getItem(draftKey) : null;
        const data = draft ? (JSON.parse(draft) as AdminQuestionnaire) : await getQuestionnaire(id);
        if (alive) {
          setOrig(data);
          setQn(data);
          sessionStorage.removeItem(draftKey);
          // expand everything by default
          const c: Record<string, boolean> = {};
          data.questions.forEach((q) => {
            c[q.id] = false;
          });
          setCollapsed(c);
        }
      } catch (e: any) {
        setErr(e?.message || "No se pudo cargar");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [id]);

  // ---------- Dirty state & beforeunload ----------
  const dirty = useMemo(() => {
    if (!orig || !qn) return false;
    return JSON.stringify(clean(objStripIds(orig))) !== JSON.stringify(clean(objStripIds(qn)));
  }, [orig, qn]);

  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!dirty) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [dirty]);

  // ---------- Autosave draft to sessionStorage ----------
  useEffect(() => {
    if (!qn) return;
    const t = setTimeout(() => {
      sessionStorage.setItem(`draft:${id}`, JSON.stringify(qn));
      setNote("Borrador guardado");
      setTimeout(() => setNote(null), 1200);
    }, 500);
    return () => clearTimeout(t);
  }, [id, qn]);

  // ---------- Keyboard shortcuts ----------
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        if (e.shiftKey) saveOrderOnly();
        else saveAll();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  // ---------- Helpers ----------
  function clean<T>(x: T): T {
    return JSON.parse(JSON.stringify(x));
  }
  function objStripIds(q: AdminQuestionnaire) {
    // mantener ids (necesarios para branch_to), solo limpiamos timestamps si existieran
    return q;
  }

  // ---------- Mutations ----------
  function addQuestion() {
    if (!qn) return;
    const q: AdminQuestion = {
      id: crypto.randomUUID(),
      text: "Nueva pregunta",
      type: "text",
      required: false,
      order: qn.questions.length + 1,
      choices: null,
      // @ts-ignore opcionales si existen en tu tipo
      file_mode: "image_only",
      // @ts-ignore
      semantic_tag: "none",
    };
    const next = { ...qn, questions: [...qn.questions, q] };
    setQn(next);
    setCollapsed((prev) => ({ ...prev, [q.id]: false }));
  }

  function duplicateQuestion(qid: string) {
    if (!qn) return;
    const q0 = qn.questions.find((q) => q.id === qid);
    if (!q0) return;
    const clone: AdminQuestion = {
      ...clean(q0),
      id: crypto.randomUUID(),
      text: q0.text + " (copia)",
      order: qn.questions.length + 1,
      choices: q0.choices ? q0.choices.map((c) => ({ ...c, id: crypto.randomUUID() })) : null,
    };
    setQn({ ...qn, questions: [...qn.questions, clone].map((q, i) => ({ ...q, order: i + 1 })) });
    setCollapsed((prev) => ({ ...prev, [clone.id]: false }));
  }

  function removeQuestion(qid: string) {
    if (!qn) return;
    if (!confirm("¿Eliminar esta pregunta? Esta acción no se puede deshacer.")) return;
    // limpiar branch_to que apunten a la pregunta eliminada
    const nextQ = qn.questions
      .filter((q) => q.id !== qid)
      .map((q, i) => ({
        ...q,
        order: i + 1,
        choices: q.choices
          ? q.choices.map((c) => ({ ...c, branch_to: c.branch_to === qid ? null : c.branch_to }))
          : null,
      }));
    setQn({ ...qn, questions: nextQ });
  }

  function move(qid: string, dir: -1 | 1) {
    if (!qn) return;
    const idx = qn.questions.findIndex((q) => q.id === qid);
    const j = idx + dir;
    if (idx < 0 || j < 0 || j >= qn.questions.length) return;
    const arr = [...qn.questions];
    [arr[idx], arr[j]] = [arr[j], arr[idx]];
    const re = arr.map((q, i) => ({ ...q, order: i + 1 }));
    setQn({ ...qn, questions: re });
  }

  function updateQuestion(qid: string, patch: Partial<AdminQuestion>) {
    if (!qn) return;
    setQn({
      ...qn,
      questions: qn.questions.map((q) => (q.id === qid ? { ...q, ...patch } : q)),
    });
  }

  function addChoice(qid: string) {
    if (!qn) return;
    setQn({
      ...qn,
      questions: qn.questions.map((q) => {
        if (q.id !== qid) return q;
        const list = q.choices ? [...q.choices] : [];
        list.push({ id: crypto.randomUUID(), text: "Opción", branch_to: null });
        return { ...q, choices: list };
      }),
    });
  }

  function updateChoice(qid: string, cid: string, patch: Partial<AdminChoice>) {
    if (!qn) return;
    setQn({
      ...qn,
      questions: qn.questions.map((q) => {
        if (q.id !== qid) return q;
        const list = (q.choices || []).map((c) => (c.id === cid ? { ...c, ...patch } : c));
        return { ...q, choices: list };
      }),
    });
  }

  function removeChoice(qid: string, cid: string) {
    if (!qn) return;
    setQn({
      ...qn,
      questions: qn.questions.map((q) => {
        if (q.id !== qid) return q;
        const list = (q.choices || []).filter((c) => c.id !== cid);
        return { ...q, choices: list.length ? list : null };
      }),
    });
  }

  function bulkAddChoices(qid: string, blob: string) {
    if (!qn) return;
    const lines = blob
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!lines.length) return;
    setQn({
      ...qn,
      questions: qn.questions.map((q) => {
        if (q.id !== qid) return q;
        const base = q.choices ? [...q.choices] : [];
        const added = lines.map((t) => ({ id: crypto.randomUUID(), text: t, branch_to: null }));
        return { ...q, choices: [...base, ...added] };
      }),
    });
  }

  // ---------- Save ----------
  async function saveAll() {
    if (!qn) return;
    // validaciones básicas
    const errors: string[] = [];
    if (!qn.title?.trim()) errors.push("El título no puede estar vacío.");
    qn.questions.forEach((q, idx) => {
      if (!q.text?.trim()) errors.push(`Pregunta #${idx + 1} sin texto.`);
      if (q.type === "choice" && (!q.choices || q.choices.length === 0)) {
        errors.push(`Pregunta #${idx + 1} (choice) sin opciones.`);
      }
    });
    if (errors.length) {
      setErr(errors[0]);
      setTimeout(() => setErr(null), 3000);
      // scroll al primer item problemático
      firstErrorRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    try {
      setSaving(true);
      setErr(null);
      const saved = await upsertQuestionnaire(qn);
      setQn(saved);
      setOrig(saved);
      setNote("Guardado ✅");
      setTimeout(() => setNote(null), 1500);
    } catch (e: any) {
      setErr(e?.message || "No se pudo guardar");
    } finally {
      setSaving(false);
    }
  }

  async function saveOrderOnly() {
    if (!qn) return;
    try {
      setSaving(true);
      setErr(null);
      await reorderQuestions(qn.id, qn.questions.map((q) => q.id));
      setNote("Orden actualizado");
      setTimeout(() => setNote(null), 1200);
    } catch (e: any) {
      setErr(e?.message || "No se pudo actualizar el orden");
    } finally {
      setSaving(false);
    }
  }

  // ---------- Derived ----------
  const questionOptions = useMemo(
    () => (qn?.questions || []).map((q) => ({ id: q.id, label: `${q.order}. ${q.text.slice(0, 60)}` })),
    [qn]
  );

  if (loading) return <div className="p-8">Cargando…</div>;
  if (err) return <div className="p-8 text-red-600">{err}</div>;
  if (!qn) return null;

  return (
    <main className="min-h-[calc(100vh-80px)] w-full">
      {/* Top bar sticky */}
      <div className="sticky top-0 z-20 border-b bg-white/80 dark:bg-zinc-900/80 backdrop-blur supports-[backdrop-filter]:bg-white/55">
        <div className="mx-auto max-w-[1100px] px-6 md:px-8 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/admin")}
              className="px-3 py-1.5 rounded-lg border hover:bg-slate-50 dark:hover:bg-white/5"
            >
              ← Volver
            </button>
            <h1 className="text-lg md:text-xl font-semibold truncate">
              Editando: {qn.title || "(sin título)"}
            </h1>
            {dirty && (
              <span className="ml-2 text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-700">
                Cambios sin guardar
              </span>
            )}
            {note && (
              <span className="ml-2 text-xs px-2 py-0.5 rounded bg-emerald-100 text-emerald-700">
                {note}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={saveOrderOnly}
              disabled={saving}
              className="px-3 py-1.5 rounded-lg border hover:bg-slate-50 dark:hover:bg-white/5 disabled:opacity-50"
              title="⇧+⌘/Ctrl+S"
            >
              Guardar orden
            </button>
            <button
              onClick={saveAll}
              disabled={saving}
              className="px-3 py-1.5 rounded-lg bg-skyBlue text-white disabled:opacity-50"
            >
              {saving ? "Guardando…" : "Guardar todo"}
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-[1100px] px-6 md:px-8 py-6 space-y-6">
        {/* Metadatos */}
        <section className={`${CARD} p-6`}>
          <div className="grid md:grid-cols-3 gap-4">
            <label className="block">
              <span className="text-sm">Título</span>
              <input
                className={INPUT}
                value={qn.title}
                onChange={(e) => setQn({ ...qn, title: e.target.value })}
                placeholder="Ej. Inspección de Vehículos - Fase 1"
              />
            </label>
            <label className="block">
              <span className="text-sm">Versión</span>
              <input
                className={INPUT}
                value={qn.version}
                onChange={(e) => setQn({ ...qn, version: e.target.value })}
                placeholder="v1.0"
              />
            </label>
            <label className="block">
              <span className="text-sm">Zona horaria</span>
              <input
                className={INPUT}
                value={qn.timezone}
                onChange={(e) => setQn({ ...qn, timezone: e.target.value })}
                placeholder="America/Bogota"
              />
            </label>
          </div>
        </section>

        {/* Preguntas */}
        <section className={`${CARD} p-6`}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">
              Preguntas <span className="text-slate-500">({qn.questions.length})</span>
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() =>
                  setCollapsed(Object.fromEntries(qn.questions.map((q) => [q.id, true])))
                }
                className="px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
              >
                Colapsar todo
              </button>
              <button
                onClick={() =>
                  setCollapsed(Object.fromEntries(qn.questions.map((q) => [q.id, false])))
                }
                className="px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
              >
                Expandir todo
              </button>
              <button
                onClick={addQuestion}
                className="px-4 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
              >
                Añadir pregunta
              </button>
            </div>
          </div>

          <ol className="space-y-4">
            {qn.questions.map((q, idx) => {
              const hasEmpty =
                !q.text?.trim() || (q.type === "choice" && (!q.choices || q.choices.length === 0));
              return (
                <li
                  key={q.id}
                  className={`rounded-xl border ${
                    hasEmpty
                      ? "border-amber-300"
                      : "border-slate-200/70 dark:border-white/10"
                  } p-4`}
                >
                  {idx === 0 && hasEmpty && <div ref={firstErrorRef} />}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      {/* Header */}
                      <div className="flex flex-wrap items-center gap-2 mb-3">
                        <button
                          className="inline-flex items-center justify-center h-8 w-8 rounded-full bg-skyBlue text-white font-semibold"
                          onClick={() =>
                            setCollapsed((c) => ({ ...c, [q.id]: !c[q.id] }))
                          }
                          title={collapsed[q.id] ? "Expandir" : "Colapsar"}
                        >
                          {q.order}
                        </button>
                        <input
                          className={`${INPUT} !py-2 flex-1`}
                          value={q.text}
                          onChange={(e) => updateQuestion(q.id, { text: e.target.value })}
                          placeholder="Texto de la pregunta"
                        />
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => move(q.id, -1)}
                            className="px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
                            title="Mover arriba"
                          >
                            ↑
                          </button>
                          <button
                            onClick={() => move(q.id, +1)}
                            className="px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
                            title="Mover abajo"
                          >
                            ↓
                          </button>
                          <button
                            onClick={() => duplicateQuestion(q.id)}
                            className="px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
                            title="Duplicar"
                          >
                            Duplicar
                          </button>
                          <button
                            onClick={() => removeQuestion(q.id)}
                            className="px-3 py-2 rounded-xl border hover:bg-red-50 dark:hover:bg-white/5 text-red-600"
                            title="Eliminar"
                          >
                            Eliminar
                          </button>
                        </div>
                      </div>

                      {/* Body */}
                      {!collapsed[q.id] && (
                        <div className="grid md:grid-cols-3 gap-3">
                          <label className="block">
                            <span className="text-xs">Tipo</span>
                            <select
                              className={INPUT}
                              value={q.type}
                              onChange={(e) =>
                                updateQuestion(q.id, {
                                  type: e.target.value as AdminQuestion["type"],
                                  choices:
                                    e.target.value === "choice" ? q.choices || [] : null,
                                })
                              }
                            >
                              {TYPES.map((t) => (
                                <option key={t} value={t}>
                                  {t}
                                </option>
                              ))}
                            </select>
                          </label>

                          {/* Opciones file_mode (si existen en tu tipo) */}
                          {q.type === "file" && (
                            <label className="block">
                              <span className="text-xs">Modo de archivo</span>
                              <select
                                className={INPUT}
                                value={(q as any).file_mode || "image_only"}
                                onChange={(e) =>
                                  updateQuestion(q.id, {
                                    ...(q as any),
                                    file_mode: e.target.value,
                                  } as any)
                                }
                              >
                                {FILE_MODES.map((m) => (
                                  <option key={m} value={m}>
                                    {m}
                                  </option>
                                ))}
                              </select>
                            </label>
                          )}

                          {/* Semantic tag (si existe) */}
                          <label className="block">
                            <span className="text-xs">Etiqueta semántica</span>
                            <select
                              className={INPUT}
                              value={(q as any).semantic_tag || "none"}
                              onChange={(e) =>
                                updateQuestion(q.id, {
                                  ...(q as any),
                                  semantic_tag: e.target.value,
                                } as any)
                              }
                            >
                              {TAGS.map((t) => (
                                <option key={t} value={t}>
                                  {t}
                                </option>
                              ))}
                            </select>
                          </label>

                          {/* Required */}
                          <label className="block">
                            <span className="text-xs">Obligatoria</span>
                            <div className="mt-2">
                              <label className={radioCls(q.required)}>
                                <input
                                  type="checkbox"
                                  checked={q.required}
                                  onChange={(e) =>
                                    updateQuestion(q.id, { required: e.target.checked })
                                  }
                                  className="h-4 w-4"
                                />
                                <span className="ml-2">Requerida</span>
                              </label>
                            </div>
                          </label>

                          {/* Botón añadir opción si es choice */}
                          {q.type === "choice" && (
                            <label className="block">
                              <span className="text-xs">Opciones</span>
                              <button
                                type="button"
                                onClick={() => addChoice(q.id)}
                                className="block w-full min-h-[42px] mt-1 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
                              >
                                Añadir opción
                              </button>
                            </label>
                          )}
                        </div>
                      )}

                      {/* Lista de opciones */}
                      {q.type === "choice" && !collapsed[q.id] && (
                        <div className="mt-4 grid gap-2">
                          {(q.choices || []).map((c) => (
                            <div
                              key={c.id}
                              className="flex flex-col md:flex-row items-stretch md:items-center gap-2"
                            >
                              <input
                                className={`${INPUT} !py-2 flex-1`}
                                value={c.text}
                                onChange={(e) =>
                                  updateChoice(q.id, c.id, { text: e.target.value })
                                }
                                placeholder="Texto de la opción"
                              />
                              <select
                                className={`${INPUT} !py-2 md:w-[320px]`}
                                value={c.branch_to || ""}
                                onChange={(e) =>
                                  updateChoice(q.id, c.id, {
                                    branch_to: e.target.value || null,
                                  })
                                }
                              >
                                <option value="">(sin ramificar)</option>
                                {questionOptions
                                  .filter((o) => o.id !== q.id) // evitar apuntar a sí misma
                                  .map((o) => (
                                    <option key={o.id} value={o.id}>
                                      {o.label}
                                    </option>
                                  ))}
                              </select>
                              <button
                                type="button"
                                onClick={() => removeChoice(q.id, c.id)}
                                className="px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
                              >
                                Borrar
                              </button>
                            </div>
                          ))}
                          {(q.choices?.length ?? 0) === 0 && (
                            <p className="text-sm text-slate-500">No hay opciones.</p>
                          )}

                          {/* Pegado en bloque */}
                          <details className="mt-2">
                            <summary className="text-xs text-slate-600 cursor-pointer">
                              Pegar opciones (una por línea)
                            </summary>
                            <textarea
                              className={`${INPUT} mt-2 h-28`}
                              placeholder={"Opción A\nOpción B\nOpción C"}
                              onBlur={(e) => {
                                if (e.currentTarget.value.trim()) {
                                  bulkAddChoices(q.id, e.currentTarget.value);
                                  e.currentTarget.value = "";
                                }
                              }}
                            />
                            <p className="text-xs text-slate-500 mt-1">
                              Al salir del área se agregarán las líneas no vacías.
                            </p>
                          </details>
                        </div>
                      )}
                    </div>

                    {/* Side controls compactos */}
                    <div className="flex flex-col gap-2">
                      <button
                        onClick={() =>
                          setCollapsed((s) => ({ ...s, [q.id]: !s[q.id] }))
                        }
                        className="px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
                      >
                        {collapsed[q.id] ? "Expandir" : "Colapsar"}
                      </button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        </section>

        {/* Pie para dar espacio al footer fijo */}
        <div className="h-20" />
      </div>

      {/* Footer fijo de acciones */}
      <div className="fixed bottom-0 inset-x-0 z-30 border-t bg-white/90 dark:bg-zinc-900/90 backdrop-blur">
        <div className="mx-auto max-w-[1100px] px-6 md:px-8 py-3 flex items-center justify-between gap-3">
          <div className="text-sm text-slate-600">
            {dirty ? "Cambios sin guardar" : "Todo guardado"}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={saveOrderOnly}
              disabled={saving}
              className="px-4 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5 disabled:opacity-50"
              title="⇧+⌘/Ctrl+S"
            >
              Guardar orden
            </button>
            <button
              onClick={saveAll}
              disabled={saving}
              className="px-4 py-2 rounded-xl bg-skyBlue text-white disabled:opacity-50"
            >
              {saving ? "Guardando…" : "Guardar todo"}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
