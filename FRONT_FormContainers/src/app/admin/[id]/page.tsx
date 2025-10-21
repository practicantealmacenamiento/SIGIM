/* eslint-disable @typescript-eslint/ban-ts-comment */
"use client";

// ===============================================================
// Administración — Editor de Formulario (page.tsx)
// ---------------------------------------------------------------
// Objetivos de esta versión:
// - UI más consistente con la página general de Administración
// - Accesibilidad (roles/aria, foco en errores, atajos de teclado)
// - Mejor UX: autosave de borrador, toasts ligeros, chips de estado
// - Herramientas de edición: colapsar/expandir, duplicar, mover, bulk de opciones
// - Sin dependencias nuevas; mantiene compatibilidad con lib/api.admin
// ===============================================================

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
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
import { INPUT, radioCls } from "@/lib/ui";
import { genUUID } from "@/lib/uuid";

/* ===================== UI tokens ===================== */
const UI = {
  page: "min-h-[calc(100vh-80px)] w-full bg-gradient-to-b from-slate-50 to-white dark:from-[#0b1220] dark:to-[#0b1220]",
  container: "mx-auto max-w-[1100px] px-6 md:px-8",
  card: "rounded-2xl border border-slate-200/70 dark:border-white/10 bg-white/90 dark:bg-slate-900/90 shadow-lg backdrop-blur supports-[backdrop-filter]:bg-white/60 supports-[backdrop-filter]:dark:bg-slate-900/60",
  btn: "px-3 py-2 rounded-xl border border-slate-200/70 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 transition",
  btnPrimary: "px-4 py-2 rounded-xl bg-sky-600 text-white shadow-sm hover:bg-sky-700 transition disabled:opacity-60",
  chip: "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
  chipInfo: "bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-slate-200",
  chipReq: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200",
  railBtn: "inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200/70 dark:border-white/15 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 transition",
  railBtnDanger: "inline-flex h-8 w-8 items-center justify-center rounded-full border border-rose-200/60 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition",
  kbd: "inline-flex items-center gap-1 rounded-md px-1.5 py-[2px] text-[11px] font-medium border border-slate-200/70 dark:border-white/10 bg-slate-50 dark:bg-white/5",
};

/* ===================== Iconos (paths estables) ===================== */
function Icon({ d }: { d: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-[18px] w-[18px]"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}
const IChevronUp = () => <Icon d="M6 14l6-6 6 6" />;
const IChevronDown = () => <Icon d="M6 10l6 6 6-6" />;
const IArrowUp = () => <Icon d="M12 19V5m0 0l-5 5m5-5l5 5" />;
const IArrowDown = () => <Icon d="M12 5v14m0 0l-5-5m5 5l5-5" />;
const ICopy = () => <Icon d="M16 16H8V8h8v8zM14 4H8a2 2 0 0 0-2 2v6" />;
const ITrash = () => (
  <Icon d="M3 6h18M8 6V4h8v2m-1 0v12a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V6h10z" />
);

const TYPES: AdminQuestion["type"][] = [
  "text",
  "number",
  "date",
  "file",
  "choice",
];
const FILE_MODES = ["image_only", "image_ocr", "ocr_only"] as const;
const TAGS = [
  "none",
  "placa",
  "contenedor",
  "precinto",
  "proveedor",
  "transportista",
  "receptor",
] as const;

/* ===================== Toasts ligeros ===================== */
function useToasts() {
  const [items, setItems] = useState<
    { id: number; type: "ok" | "err"; text: string }[]
  >([]);
  const idRef = useRef(0);

  const push = useCallback((type: "ok" | "err", text: string) => {
    const id = ++idRef.current;
    setItems((xs) => [...xs, { id, type, text }]);
    setTimeout(() => {
      setItems((xs) => xs.filter((t) => t.id !== id));
    }, 3200);
  }, []);

  const view = (
    <div className="fixed z-[60] bottom-4 right-4 space-y-2">
      {items.map((t) => (
        <div
          key={t.id}
          role="status"
          className={`flex items-center gap-3 max-w-[360px] rounded-xl px-4 py-3 shadow-lg border ${
            t.type === "ok"
              ? "bg-emerald-50/90 border-emerald-200/70 text-emerald-800 dark:bg-emerald-900/25 dark:text-emerald-200 dark:border-emerald-900/40"
              : "bg-rose-50/90 border-rose-200/70 text-rose-800 dark:bg-rose-900/25 dark:text-rose-200 dark:border-rose-900/40"
          }`}
        >
          <span className="text-sm leading-snug">{t.text}</span>
        </div>
      ))}
    </div>
  );

  return { push, view } as const;
}

/* ===================== Página ===================== */
export default function AdminEditorPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { push, view } = useToasts();

  const [orig, setOrig] = useState<AdminQuestionnaire | null>(null);
  const [qn, setQn] = useState<AdminQuestionnaire | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const firstErrorRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    installGlobalAuthFetch();
  }, []);

  // load + draft
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setErr(null);
        setLoading(true);
        const draftKey = `draft:${id}`;
        const draft =
          typeof window !== "undefined"
            ? sessionStorage.getItem(draftKey)
            : null;
        const data = draft
          ? (JSON.parse(draft) as AdminQuestionnaire)
          : await getQuestionnaire(id);
        if (!alive) return;
        setOrig(data);
        setQn(data);
        sessionStorage.removeItem(draftKey);
        const c: Record<string, boolean> = {};
        data.questions.forEach((q) => (c[q.id] = false));
        setCollapsed(c);
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

  // dirty guard
  const dirty = useMemo(
    () => !!orig && !!qn && JSON.stringify(orig) !== JSON.stringify(qn),
    [orig, qn]
  );
  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!dirty) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [dirty]);

  // autosave draft
  useEffect(() => {
    if (!qn) return;
    const t = setTimeout(() => {
      sessionStorage.setItem(`draft:${id}`, JSON.stringify(qn));
      setNote("Borrador guardado");
      setTimeout(() => setNote(null), 900);
    }, 500);
    return () => clearTimeout(t);
  }, [id, qn]);

  // shortcuts
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

  /* ---------- helpers & mutations ---------- */
  const addQuestion = useCallback(() => {
    if (!qn) return;
    const q: AdminQuestion = {
      id: genUUID(),
      text: "Nueva pregunta",
      type: "text",
      required: false,
      order: qn.questions.length + 1,
      choices: null,
      // @ts-ignore
      file_mode: "image_only",
      // @ts-ignore
      semantic_tag: "none",
    };
    setQn({ ...qn, questions: [...qn.questions, q] });
    setCollapsed((s) => ({ ...s, [q.id]: false }));
  }, [qn]);

  const duplicateQuestion = useCallback(
    (qid: string) => {
      if (!qn) return;
      const src = qn.questions.find((q) => q.id === qid);
      if (!src) return;
      const clone: AdminQuestion = {
        ...src,
        id: genUUID(),
        text: src.text + " (copia)",
        order: qn.questions.length + 1,
        choices: src.choices
          ? src.choices.map((c) => ({ ...c, id: genUUID() }))
          : null,
      };
      const next = [...qn.questions, clone].map((q, i) => ({ ...q, order: i + 1 }));
      setQn({ ...qn, questions: next });
      setCollapsed((s) => ({ ...s, [clone.id]: false }));
      push("ok", "Pregunta duplicada");
    },
    [qn, push]
  );

  const removeQuestion = useCallback(
    (qid: string) => {
      if (!qn) return;
      if (!confirm("¿Eliminar esta pregunta?")) return;
      const next = qn.questions
        .filter((q) => q.id !== qid)
        .map((q, i) => ({
          ...q,
          order: i + 1,
          choices: q.choices
            ? q.choices.map((c) => ({
                ...c,
                branch_to: c.branch_to === qid ? null : c.branch_to,
              }))
            : null,
        }));
      setQn({ ...qn, questions: next });
      push("ok", "Pregunta eliminada");
    },
    [qn, push]
  );

  const move = useCallback(
    (qid: string, dir: -1 | 1) => {
      if (!qn) return;
      const idx = qn.questions.findIndex((q) => q.id === qid);
      const j = idx + dir;
      if (idx < 0 || j < 0 || j >= qn.questions.length) return;
      const arr = [...qn.questions];
      [arr[idx], arr[j]] = [arr[j], arr[idx]];
      setQn({ ...qn, questions: arr.map((q, i) => ({ ...q, order: i + 1 })) });
    },
    [qn]
  );

  const updateQuestion = useCallback(
    (qid: string, patch: Partial<AdminQuestion>) => {
      if (!qn) return;
      setQn({
        ...qn,
        questions: qn.questions.map((q) => (q.id === qid ? { ...q, ...patch } : q)),
      });
    },
    [qn]
  );

  const addChoice = useCallback(
    (qid: string) => {
      if (!qn) return;
      setQn({
        ...qn,
        questions: qn.questions.map((q) => {
          if (q.id !== qid) return q;
          const list = q.choices ? [...q.choices] : [];
          list.push({ id: genUUID(), text: "Opción", branch_to: null });
          return { ...q, choices: list };
        }),
      });
    },
    [qn]
  );

  const updateChoice = useCallback(
    (qid: string, cid: string, patch: Partial<AdminChoice>) => {
      if (!qn) return;
      setQn({
        ...qn,
        questions: qn.questions.map((q) => {
          if (q.id !== qid) return q;
          return {
            ...q,
            choices: (q.choices || []).map((c) => (c.id === cid ? { ...c, ...patch } : c)),
          };
        }),
      });
    },
    [qn]
  );

  const removeChoice = useCallback(
    (qid: string, cid: string) => {
      if (!qn) return;
      setQn({
        ...qn,
        questions: qn.questions.map((q) => {
          if (q.id !== qid) return q;
          const remain = (q.choices || []).filter((c) => c.id !== cid);
          return { ...q, choices: remain.length ? remain : null };
        }),
      });
    },
    [qn]
  );

  const bulkAddChoices = useCallback(
    (qid: string, blob: string) => {
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
          const added = lines.map((t) => ({ id: genUUID(), text: t, branch_to: null }));
          return { ...q, choices: [...base, ...added] };
        }),
      });
      push("ok", `${lines.length} opción(es) agregada(s)`);
    },
    [qn, push]
  );

  const saveAll = useCallback(async () => {
    if (!qn) return;
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
      setTimeout(() => setErr(null), 2800);
      firstErrorRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      push("err", errors[0]);
      return;
    }
    try {
      setSaving(true);
      setErr(null);
      const saved = await upsertQuestionnaire(qn);
      setQn(saved);
      setOrig(saved);
      setNote("Guardado ✅");
      setTimeout(() => setNote(null), 1200);
      push("ok", "Formulario guardado");
    } catch (e: any) {
      const msg = e?.message || "No se pudo guardar";
      setErr(msg);
      push("err", msg);
    } finally {
      setSaving(false);
    }
  }, [qn, push]);

  const saveOrderOnly = useCallback(async () => {
    if (!qn) return;
    try {
      setSaving(true);
      setErr(null);
      await reorderQuestions(
        qn.id,
        qn.questions.map((q) => q.id)
      );
      setNote("Orden actualizado");
      setTimeout(() => setNote(null), 900);
      push("ok", "Orden de preguntas actualizado");
    } catch (e: any) {
      const msg = e?.message || "No se pudo actualizar el orden";
      setErr(msg);
      push("err", msg);
    } finally {
      setSaving(false);
    }
  }, [qn, push]);

  const questionOptions = useMemo(
    () => (qn?.questions || []).map((q) => ({ id: q.id, label: `${q.order}. ${q.text.slice(0, 60)}` })),
    [qn]
  );

  if (loading) return <div className="p-8">Cargando…</div>;
  if (err) return <div className="p-8 text-rose-600">{err}</div>;
  if (!qn) return null;

  return (
    <main className={UI.page}>
      {/* ===== Topbar ===== */}
      <div className="sticky top-0 z-30 border-b bg-white/80 dark:bg-zinc-900/80 backdrop-blur supports-[backdrop-filter]:bg-white/55">
        <div className={`${UI.container} py-3 flex items-center justify-between gap-3`}>
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => router.push("/admin")} className={UI.btn}>
              ← Volver
            </button>
            <h1 className="text-lg md:text-xl font-semibold truncate">
              {qn.title || "(sin título)"} <span className="text-slate-400">· {qn.version}</span>
            </h1>
            {dirty && <span className={`${UI.chip} ${UI.chipReq} ml-1`}>Cambios sin guardar</span>}
            {note && (
              <span className={`${UI.chip} bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200 ml-1`}>
                {note}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={saveOrderOnly} disabled={saving} className={UI.btn} title="⇧+⌘/Ctrl+S">
              Guardar orden
            </button>
            <button onClick={saveAll} disabled={saving} className={UI.btnPrimary}>
              {saving ? "Guardando…" : "Guardar todo"}
            </button>
          </div>
        </div>
      </div>

      <div className={`${UI.container} py-6 space-y-6`}>
        {/* ===== Metadatos ===== */}
        <section className={`${UI.card} p-6`}>
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

        {/* ===== Preguntas ===== */}
        <section className={`${UI.card} p-6`}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">
              Preguntas <span className="text-slate-500">({qn.questions.length})</span>
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() =>
                  setCollapsed(Object.fromEntries(qn.questions.map((q) => [q.id, true])))
                }
                className={UI.btn}
              >
                Colapsar todo
              </button>
              <button
                onClick={() =>
                  setCollapsed(Object.fromEntries(qn.questions.map((q) => [q.id, false])))
                }
                className={UI.btn}
              >
                Expandir todo
              </button>
              <button onClick={addQuestion} className={UI.btnPrimary}>
                Añadir pregunta
              </button>
            </div>
          </div>

          <ol className="space-y-4">
            {qn.questions.map((q, idx) => {
              const hasEmpty =
                !q.text?.trim() || (q.type === "choice" && (!q.choices || q.choices.length === 0));
              const isCollapsed = !!collapsed[q.id];

              return (
                <li
                  key={q.id}
                  className={`group relative rounded-2xl border p-4 pr-24 bg-white dark:bg-slate-900 shadow-sm hover:shadow-md overflow-hidden transition ${
                    hasEmpty
                      ? "border-amber-300"
                      : "border-slate-200/70 dark:border-white/10"
                  }`}
                >
                  {idx === 0 && hasEmpty && <div ref={firstErrorRef} />}

                  {/* HEADER */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-3">
                        <span className="inline-grid place-items-center h-8 w-8 rounded-full bg-sky-600 text-white text-sm font-semibold">
                          {q.order}
                        </span>

                        {/* Título / resumen */}
                        {!isCollapsed ? (
                          <input
                            className={`${INPUT} !py-2 flex-1`}
                            value={q.text}
                            onChange={(e) => updateQuestion(q.id, { text: e.target.value })}
                            placeholder="Texto de la pregunta"
                          />
                        ) : (
                          <div className="flex-1 min-w-0 px-3 py-2 rounded-lg bg-slate-50 dark:bg-white/5 text-sm text-slate-800 dark:text-slate-200 truncate">
                            {q.text || <span className="opacity-60">(sin texto)</span>}
                          </div>
                        )}

                        <span className={`${UI.chip} ${UI.chipInfo}`}>{q.type}</span>
                        {q.required && (
                          <span className={`${UI.chip} ${UI.chipReq}`}>Requerida</span>
                        )}
                        {q.type === "choice" && (
                          <span className={`${UI.chip} ${UI.chipInfo}`}>
                            {q.choices?.length || 0} opciones
                          </span>
                        )}

                        {/* Toolbar colapsada (horizontal) */}
                        {isCollapsed && (
                          <div className="flex items-center gap-1 ml-auto shrink-0">
                            <button
                              onClick={() =>
                                setCollapsed((s) => ({ ...s, [q.id]: false }))
                              }
                              className={UI.railBtn}
                              title="Expandir"
                            >
                              <IChevronDown />
                            </button>
                            <button
                              onClick={() => move(q.id, -1)}
                              className={UI.railBtn}
                              title="Mover arriba"
                            >
                              <IArrowUp />
                            </button>
                            <button
                              onClick={() => move(q.id, +1)}
                              className={UI.railBtn}
                              title="Mover abajo"
                            >
                              <IArrowDown />
                            </button>
                            <button
                              onClick={() => duplicateQuestion(q.id)}
                              className={UI.railBtn}
                              title="Duplicar"
                            >
                              <ICopy />
                            </button>
                            <button
                              onClick={() => removeQuestion(q.id)}
                              className={UI.railBtnDanger}
                              title="Eliminar"
                            >
                              <ITrash />
                            </button>
                          </div>
                        )}
                      </div>

                      {/* BODY (solo expandido) */}
                      {!isCollapsed && (
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
                                    e.target.value === "choice"
                                      ? q.choices || []
                                      : null,
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

                          {q.type === "choice" && (
                            <label className="block">
                              <span className="text-xs">Opciones</span>
                              <button
                                type="button"
                                onClick={() => addChoice(q.id)}
                                className={`${UI.btn} w-full mt-1`}
                              >
                                Añadir opción
                              </button>
                            </label>
                          )}
                        </div>
                      )}

                      {/* OPCIONES (solo expandido y choice) */}
                      {q.type === "choice" && !isCollapsed && (
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
                                  .filter((o) => o.id !== q.id)
                                  .map((o) => (
                                    <option key={o.id} value={o.id}>
                                      {o.label}
                                    </option>
                                  ))}
                              </select>
                              <button
                                type="button"
                                onClick={() => removeChoice(q.id, c.id)}
                                className={UI.railBtnDanger}
                                title="Eliminar opción"
                              >
                                <ITrash />
                              </button>
                            </div>
                          ))}

                          {(q.choices?.length ?? 0) === 0 && (
                            <p className="text-sm text-slate-500">No hay opciones.</p>
                          )}

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

                      {/* Resumen en colapsado */}
                      {isCollapsed && (
                        <div className="mt-2 text-xs text-slate-500">
                          {q.type === "choice"
                            ? `Pregunta de selección con ${q.choices?.length || 0} opción(es).`
                            : `Tipo: ${q.type}.`} {q.required ? "· Requerida." : ""}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* RAIL ABSOLUTO (solo expandido >= md) */}
                  {!isCollapsed && (
                    <div className="hidden md:flex flex-col gap-2 absolute right-4 top-4 z-10">
                      <button
                        onClick={() => setCollapsed((s) => ({ ...s, [q.id]: true }))}
                        className={UI.railBtn}
                        title="Colapsar"
                      >
                        <IChevronUp />
                      </button>
                      <button
                        onClick={() => move(q.id, -1)}
                        className={UI.railBtn}
                        title="Mover arriba"
                      >
                        <IArrowUp />
                      </button>
                      <button
                        onClick={() => move(q.id, +1)}
                        className={UI.railBtn}
                        title="Mover abajo"
                      >
                        <IArrowDown />
                      </button>
                      <button
                        onClick={() => duplicateQuestion(q.id)}
                        className={UI.railBtn}
                        title="Duplicar"
                      >
                        <ICopy />
                      </button>
                      <button
                        onClick={() => removeQuestion(q.id)}
                        className={UI.railBtnDanger}
                        title="Eliminar"
                      >
                        <ITrash />
                      </button>
                    </div>
                  )}

                  {/* Acciones en móviles (expandido) */}
                  {!isCollapsed && (
                    <div className="md:hidden mt-3 ml-[-2px] flex items-center gap-2">
                      <button
                        onClick={() => setCollapsed((s) => ({ ...s, [q.id]: true }))}
                        className={UI.railBtn}
                        title="Colapsar"
                      >
                        <IChevronUp />
                      </button>
                      <button
                        onClick={() => move(q.id, -1)}
                        className={UI.railBtn}
                        title="Mover arriba"
                      >
                        <IArrowUp />
                      </button>
                      <button
                        onClick={() => move(q.id, +1)}
                        className={UI.railBtn}
                        title="Mover abajo"
                      >
                        <IArrowDown />
                      </button>
                      <button
                        onClick={() => duplicateQuestion(q.id)}
                        className={UI.railBtn}
                        title="Duplicar"
                      >
                        <ICopy />
                      </button>
                      <button
                        onClick={() => removeQuestion(q.id)}
                        className={UI.railBtnDanger}
                        title="Eliminar"
                      >
                        <ITrash />
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        </section>

        <div className="h-20" />
      </div>

      {/* ===== Footer fijo ===== */}
      <div className="fixed bottom-0 inset-x-0 z-30 border-t bg-white/90 dark:bg-zinc-900/90 backdrop-blur">
        <div className={`${UI.container} py-3 flex items-center justify-between gap-3`}>
          <div className="text-sm text-slate-600">
            {dirty ? "Cambios sin guardar" : "Todo guardado"}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={saveOrderOnly} disabled={saving} className={UI.btn} title="⇧+⌘/Ctrl+S">
              Guardar orden
            </button>
            <button onClick={saveAll} disabled={saving} className={UI.btnPrimary}>
              {saving ? "Guardando…" : "Guardar todo"}
            </button>
          </div>
        </div>
      </div>

      {/* Render toasts */}
      {view}
    </main>
  );
}
