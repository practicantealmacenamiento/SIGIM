"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  fetchSubmissionDetail,
  type SubmissionDetail,
  type AnswerDetail,
} from "@/lib/api.historial";

/* ——— tokens UI ——— */
const CARD =
  "rounded-2xl border border-slate-200/70 dark:border-white/10 bg-white dark:bg-slate-900 shadow-sm";
const INPUT =
  "rounded-xl border px-3 py-2 outline-none focus:ring-2 focus:ring-sky-300/40 bg-white dark:bg-slate-900";
const BTN =
  "min-h-[40px] px-4 py-2 rounded-xl border border-slate-300 dark:border-white/20 hover:bg-slate-50 dark:hover:bg-white/5 transition disabled:opacity-50 disabled:cursor-not-allowed";
const ICONBTN =
  "h-9 w-9 inline-flex items-center justify-center rounded-xl border border-slate-300 dark:border-white/20 hover:bg-slate-50 dark:hover:bg-white/5";

const tz = "America/Bogota";
const dt = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString("es-CO", { timeZone: tz }) : "—";

/* ——— helpers ——— */
const norm = (s?: string | null) =>
  (s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

const isImage = (url: string) => {
  const u = url.split("?")[0].toLowerCase();
  return [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"].some((ext) => u.endsWith(ext));
};

const fileFromAnswer = (a: AnswerDetail) =>
  (a as any).answer_file_path ?? (a as any).answer_file ?? (a as any).file ?? null;

const qidOf = (a: AnswerDetail) =>
  String((a as any).question_id ?? (a as any).questionId ?? (a as any).question?.id ?? "");

/* ——— Badge simple sin imports ——— */
function Badge({
  children,
  title,
  tone = "slate",
}: {
  children: React.ReactNode;
  title?: string;
  tone?: "slate" | "emerald" | "indigo" | "sky" | "amber";
}) {
  const tones: Record<string, string> = {
    slate:
      "text-slate-700 dark:text-slate-200 bg-slate-50 dark:bg-white/5 border border-slate-200/70 dark:border-white/10",
    emerald:
      "text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-400/10 border border-emerald-200/70 dark:border-emerald-300/20",
    indigo:
      "text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-400/10 border border-indigo-200/70 dark:border-indigo-300/20",
    sky: "text-sky-700 dark:text-sky-300 bg-sky-50 dark:bg-sky-400/10 border border-sky-200/70 dark:border-sky-300/20",
    amber:
      "text-slate-900 dark:text-amber-200 bg-amber-100 dark:bg-amber-400/10 border border-amber-300/70 dark:border-amber-300/20",
  };
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-sm font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

/* ——— reconstrucción de preguntas (si no vienen planas) ——— */
const buildQuestionIndex = (detail: any) => {
  const map = new Map<string, { text?: string | null; type?: string | null; tag?: string | null }>();
  const add = (arr?: any[]) => {
    if (!Array.isArray(arr)) return;
    for (const q of arr) {
      const idStr = String(q?.id ?? q?.uuid ?? q?.pk ?? "");
      if (!idStr) continue;
      const text = q?.text ?? q?.label ?? q?.title ?? q?.name ?? null;
      const type = q?.type ?? q?.question_type ?? null;
      const tag = q?.semantic_tag ?? q?.tag ?? q?.section ?? null;
      map.set(idStr, { text, type, tag });
    }
  };
  add(detail?.questionnaire?.questions);
  add(detail?.questions);
  add(detail?.questionnaire_questions);
  add(detail?.schema?.questions);
  add(detail?.questionnaireSchema?.questions);
  return map;
};

const getQText = (a: AnswerDetail, idx: Map<string, any>) => {
  const flat = (a as any).question_text ?? a?.question?.text ?? (a?.question as any)?.label ?? null;
  if (flat) return flat;
  const qid = qidOf(a);
  return qid ? idx.get(qid)?.text ?? null : null;
};
const getQType = (a: AnswerDetail, idx: Map<string, any>) => {
  const flat = (a as any).question_type ?? a?.question?.type ?? null;
  if (flat) return flat;
  const qid = qidOf(a);
  return qid ? idx.get(qid)?.type ?? null : null;
};
const getQTag = (a: AnswerDetail, idx: Map<string, any>) => {
  const flat = (a as any).question_tag ?? a?.question?.semantic_tag ?? null;
  if (flat) return flat;
  const qid = qidOf(a);
  return qid ? idx.get(qid)?.tag ?? null : null;
};

const hasAnswer = (a: AnswerDetail) =>
  Boolean(a.answer_text) ||
  Boolean(a.answer_choice?.text || (a as any).answer_choice_id) ||
  Boolean(fileFromAnswer(a));

/* ——— CSV inline (sin imports extra) ——— */
function exportCSV(detail: SubmissionDetail, rows: AnswerDetail[], qIndex: Map<string, any>) {
  const header = [
    "Submission ID",
    "Cuestionario",
    "Fase",
    "Placa",
    "Cierre",
    "Pregunta",
    "Tipo",
    "Etiqueta",
    "Respuesta (texto/opción)",
    "Archivo",
    "Timestamp",
  ];
  const lines = [header.join(",")];
  for (const a of rows) {
    const file = fileFromAnswer(a) || "";
    const txt = getQText(a, qIndex) || "(eliminada)";
    const typ = getQType(a, qIndex) || "";
    const tag = getQTag(a, qIndex) || "";
    const ans = a.answer_choice?.text ?? a.answer_text ?? (file ? "" : "(vacío)");
    const row = [
      (detail as any).id,
      (detail as any).questionnaire_title || "",
      (detail as any).tipo_fase || "",
      String((detail as any).placa_vehiculo || "").toUpperCase(),
      (detail as any).fecha_cierre || "",
      txt,
      typ,
      tag,
      ans,
      file,
      (a as any).timestamp || "",
    ].map((cell) => {
      const s = String(cell ?? "");
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    });
    lines.push(row.join(","));
  }
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `submission_${(detail as any).id}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/* ——— PAGE ——— */
export default function SubmissionDetailPage() {
  const router = useRouter();
  const params = useParams<{ id?: string | string[] }>();
  const id = Array.isArray(params?.id) ? params?.id?.[0] : params?.id;

  const [detail, setDetail] = useState<SubmissionDetail | null>(null);
  const [answers, setAnswers] = useState<AnswerDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // UI state (restaurado)
  const [q, setQ] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | "text" | "number" | "date" | "file" | "choice">("all");
  const [answeredFilter, setAnsweredFilter] = useState<"all" | "answered" | "empty">("all");
  const [tagFilter, setTagFilter] = useState<string>("");
  const [sort, setSort] = useState<"original" | "qaz" | "time_desc" | "time_asc">("original");
  const [groupByTag, setGroupByTag] = useState<boolean>(true);
  const [showRaw, setShowRaw] = useState<boolean>(false);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        setLoading(true);
        setErr(null);
        const d = await fetchSubmissionDetail(id);
        const sub = (d as any).submission ?? d;
        const ans: AnswerDetail[] =
          (Array.isArray((d as any).answers) && (d as any).answers) ||
          (Array.isArray((sub as any).answers) && (sub as any).answers) ||
          [];
        setDetail(sub);
        setAnswers(ans);
      } catch (e: any) {
        setErr(e?.message || "Error al cargar el detalle");
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const qIndex = useMemo(() => buildQuestionIndex(detail as any), [detail]);

  const tags = useMemo(() => {
    const s = new Set<string>();
    for (const a of answers) {
      const t = getQTag(a, qIndex)?.trim();
      if (t) s.add(t);
    }
    return Array.from(s).sort((a, b) => a.localeCompare(b));
  }, [answers, qIndex]);

  const filtered = useMemo(() => {
    const arr = answers.slice();
    const needle = norm(q);

    const byType = (a: AnswerDetail) =>
      typeFilter === "all" ? true : (getQType(a, qIndex) as string) === typeFilter;
    const byAnswered = (a: AnswerDetail) =>
      answeredFilter === "all"
        ? true
        : answeredFilter === "answered"
        ? hasAnswer(a)
        : !hasAnswer(a);
    const byTag = (a: AnswerDetail) => (!tagFilter ? true : (getQTag(a, qIndex) || "") === tagFilter);
    const bySearch = (a: AnswerDetail) => {
      if (!needle) return true;
      const blob = `${getQText(a, qIndex) || ""} ${a.answer_choice?.text || ""} ${a.answer_text || ""} ${fileFromAnswer(a) || ""}`;
      return norm(blob).includes(needle);
    };

    const out = arr.filter((a) => byType(a) && byAnswered(a) && byTag(a) && bySearch(a));

    const cmp =
      sort === "original"
        ? undefined
        : sort === "qaz"
        ? (a: AnswerDetail, b: AnswerDetail) =>
            (getQText(a, qIndex) || "").localeCompare(getQText(b, qIndex) || "")
        : sort === "time_desc"
        ? (a: AnswerDetail, b: AnswerDetail) =>
            Date.parse((b as any).timestamp || 0) - Date.parse((a as any).timestamp || 0)
        : (a: AnswerDetail, b: AnswerDetail) =>
            Date.parse((a as any).timestamp || 0) - Date.parse((b as any).timestamp || 0);

    if (cmp) out.sort(cmp as any);
    return out;
  }, [answers, q, typeFilter, answeredFilter, tagFilter, sort, qIndex]);

  const grouped = useMemo(() => {
    if (!groupByTag) return { "": filtered };
    const map = new Map<string, AnswerDetail[]>();
    for (const a of filtered) {
      const key = getQTag(a, qIndex)?.trim() || "Sin sección";
      const slot = map.get(key) || [];
      slot.push(a);
      map.set(key, slot);
    }
    return Object.fromEntries(Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0])));
  }, [filtered, groupByTag, qIndex]);

  if (!id) return <div className="p-8">Cargando…</div>;
  if (loading) return <div className="p-8">Cargando…</div>;
  if (err) return <div className="p-8 text-red-600">{err}</div>;
  if (!detail) return null;

  const placa = (detail as any)?.placa_vehiculo ? String((detail as any).placa_vehiculo).toUpperCase() : "SIN PLACA";
  const statusColor = (detail as any)?.finalizado ? "bg-emerald-500" : "bg-slate-400";
  const total = answers.length;
  const shown = filtered.length;

  return (
    <main className="min-h-[calc(100vh-80px)] px-6 md:px-8 py-6 md:py-8">
      <div className="mx-auto max-w-[1100px]">
        {/* Topbar sticky compacta (restaurada) */}
        <div className="sticky top-16 z-30 mb-3">
          <div className="h-14 rounded-xl border border-slate-200/70 dark:border-white/10 bg-white/80 dark:bg-slate-900/80 backdrop-blur px-3 md:px-4 flex items-center justify-between shadow-sm">
            <div className="min-w-0 flex items-center gap-3">
              <button className={ICONBTN} onClick={() => router.back()} title="Volver">←</button>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`inline-block h-2.5 w-2.5 rounded-full ${statusColor}`} />
                  <h1 className="text-base md:text-lg font-semibold truncate">
                    {(detail as any).questionnaire_title || "Formulario"} ·{" "}
                    {(detail as any).tipo_fase === "entrada" ? "Fase 1" : "Fase 2"}
                  </h1>
                </div>
                <div className="text-xs text-slate-600 dark:text-white/70 truncate">🚗 {placa}</div>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                className={ICONBTN}
                title="Copiar enlace"
                aria-label="Copiar enlace"
                onClick={() => navigator.clipboard.writeText(window.location.href).then(() => alert("Enlace copiado"))}
              >🔗</button>
              <button
                className={ICONBTN}
                title="Copiar ID"
                aria-label="Copiar ID"
                onClick={() => navigator.clipboard.writeText(String((detail as any).id)).then(() => alert("ID copiado"))}
              >🆔</button>
              <button
                className={ICONBTN}
                title="Exportar CSV"
                aria-label="Exportar CSV"
                disabled={shown === 0}
                onClick={() => exportCSV(detail, filtered, qIndex)}
              >⤓</button>
              <button className={ICONBTN} title="Imprimir" aria-label="Imprimir" onClick={() => window.print()}>🖨️</button>
            </div>
          </div>
        </div>

        {/* Panel de meta (restaurado, colapsable) */}
        <details className={`${CARD} p-3 md:p-4 mb-4`} open={false}>
          <summary className="cursor-pointer list-none flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Detalles</span>
              <span className="text-xs text-slate-500 dark:text-white/60">({String((detail as any).id).slice(0, 8)}…)</span>
            </div>
            <span className="text-slate-500 dark:text-white/60">▼</span>
          </summary>
          <div className="mt-3 grid gap-2 text-sm text-slate-700 dark:text-white/80">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge tone="indigo">📅 Cierre: {dt((detail as any).fecha_cierre)}</Badge>
              <Badge tone={(detail as any).finalizado ? "emerald" : "slate"}>
                {(detail as any).finalizado ? "✅ Finalizado" : "⏳ En progreso"}
              </Badge>
              <Badge tone="sky">ID: <span className="font-mono">{(detail as any).id}</span></Badge>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {(detail as any).proveedor && (
                <Badge title={`Proveedor: ${(detail as any).proveedor?.nombre || ""}`}>
                  🏭 {(detail as any).proveedor?.nombre || (detail as any).proveedor?.documento || (detail as any).proveedor?.id}
                </Badge>
              )}
              {(detail as any).transportista && (
                <Badge title={`Transportista: ${(detail as any).transportista?.nombre || ""}`}>
                  🚚 {(detail as any).transportista?.nombre || (detail as any).transportista?.documento || (detail as any).transportista?.id}
                </Badge>
              )}
              {(detail as any).receptor && (
                <Badge title={`Receptor: ${(detail as any).receptor?.nombre || ""}`}>
                  🧾 {(detail as any).receptor?.nombre || (detail as any).receptor?.documento || (detail as any).receptor?.id}
                </Badge>
              )}
            </div>
          </div>
        </details>

        {/* Filtros (restaurados) */}
        <div className={`${CARD} p-4 md:p-5 mb-4`}>
          <div className="grid md:grid-cols-4 gap-3">
            <div className="md:col-span-2">
              <input
                type="search"
                placeholder="Buscar en preguntas y respuestas…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="w-full rounded-xl border px-4 py-3 outline-none focus:ring-2 focus:ring-sky-300/40 tracking-wide"
              />
            </div>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as any)} className={INPUT} title="Tipo de pregunta">
              <option value="all">Tipo (todos)</option>
              <option value="text">Texto</option>
              <option value="number">Número</option>
              <option value="date">Fecha</option>
              <option value="file">Archivo</option>
              <option value="choice">Opción</option>
            </select>
            <select value={answeredFilter} onChange={(e) => setAnsweredFilter(e.target.value as any)} className={INPUT} title="Estado de respuesta">
              <option value="all">Respuestas (todas)</option>
              <option value="answered">Solo contestadas</option>
              <option value="empty">Solo vacías</option>
            </select>
            <select value={sort} onChange={(e) => setSort(e.target.value as any)} className={INPUT} title="Ordenar por">
              <option value="original">Orden original</option>
              <option value="qaz">Pregunta A–Z</option>
              <option value="time_desc">Más recientes primero</option>
              <option value="time_asc">Más antiguas primero</option>
            </select>

            <div className="md:col-span-2 flex items-center gap-2 flex-wrap">
              <select value={tagFilter} onChange={(e) => setTagFilter(e.target.value)} className={INPUT} title="Filtrar por etiqueta">
                <option value="">Etiqueta (todas)</option>
                {tags.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <label className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border">
                <input type="checkbox" checked={groupByTag} onChange={(e) => setGroupByTag(e.target.checked)} />
                Agrupar por etiqueta
              </label>
              <label className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border">
                <input type="checkbox" checked={showRaw} onChange={(e) => setShowRaw(e.target.checked)} />
                Mostrar JSON
              </label>
            </div>
          </div>

          <div className="mt-2 text-sm text-slate-600 dark:text-white/70">
            Mostrando {shown} de {total} respuestas.
          </div>
        </div>

        {/* Lista / Agrupación (restaurado) */}
        <div className="grid gap-3">
          {Object.entries(grouped).map(([section, group]) => (
            <div key={section}>
              {groupByTag && (
                <div className="sticky top-[calc(4rem+44px)] z-10">
                  <div className="px-1 py-1.5 text-sm font-semibold text-slate-600 dark:text-white/70 bg-slate-50/70 dark:bg-white/5 backdrop-blur rounded-md inline-block mb-1">
                    {section}
                  </div>
                </div>
              )}
              <ul className="grid gap-3">
                {group.length === 0 ? (
                  <li className={`${CARD} p-5 text-sm text-slate-600 dark:text-white/70`}>
                    (Sin resultados para esta sección)
                  </li>
                ) : (
                  group.map((a, idx) => {
                    const txt = getQText(a, qIndex) || "(Pregunta eliminada)";
                    const typ = getQType(a, qIndex) || "—";
                    const tag = getQTag(a, qIndex) || "";
                    const f = fileFromAnswer(a);

                    return (
                      <li key={`${a.id || "ans"}-${idx}`} className={`${CARD} p-4 md:p-5`}>
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-white/50">
                                {typ}
                              </div>
                              {tag && (
                                <Badge tone="slate" title="Sección / etiqueta">
                                  {tag}
                                </Badge>
                              )}
                            </div>

                            <div className="mt-1 font-medium text-base md:text-lg">
                              {txt}
                            </div>

                            {/* Respuesta */}
                            <div className="mt-2 text-sm md:text-base text-slate-800 dark:text-white/80 whitespace-pre-wrap break-words">
                              {a.answer_choice?.text ??
                                a.answer_text ??
                                (f ? "" : <span className="opacity-60">(vacío)</span>)}
                            </div>

                            {/* Archivo / Vista previa */}
                            {f && (
                              <div className="mt-3">
                                {isImage(f) ? (
                                  <button className={`${BTN} !px-3`} onClick={() => setPreview(f)} title="Vista previa">
                                    🖼️ Ver imagen
                                  </button>
                                ) : (
                                  <a
                                    href={f}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
                                  >
                                    📄 Ver archivo
                                  </a>
                                )}
                              </div>
                            )}

                            <div className="mt-2 text-xs text-slate-500 dark:text-white/60">
                              Enviado: {dt((a as any).timestamp)}
                            </div>

                            {showRaw && (
                              <pre className="mt-3 text-xs p-3 rounded-xl bg-slate-50 dark:bg-white/5 overflow-auto">
                                {JSON.stringify(a, null, 2)}
                              </pre>
                            )}
                          </div>
                        </div>
                      </li>
                    );
                  })
                )}
              </ul>
            </div>
          ))}
        </div>

        {/* Modal de imagen (restaurado) */}
        {preview && (
          <div
            className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
            onClick={() => setPreview(null)}
          >
            <div
              className="bg-white dark:bg-slate-900 rounded-2xl overflow-hidden shadow-xl max-w-4xl w-full"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-4 py-2 border-b dark:border-white/10">
                <div className="font-medium">Vista previa</div>
                <button className={BTN} onClick={() => setPreview(null)}>✕ Cerrar</button>
              </div>
              <div className="p-2">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={preview} alt="preview" className="max-h-[70vh] w-full object-contain rounded-xl" />
              </div>
              <div className="px-4 pb-3">
                <a
                  href={preview}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border hover:bg-slate-50 dark:hover:bg-white/5"
                >
                  ↗ Abrir en pestaña
                </a>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
