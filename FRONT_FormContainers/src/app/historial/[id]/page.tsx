"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  fetchSubmissionDetail,
  type SubmissionDetail,
  type AnswerDetail,
} from "@/lib/api.historial";

/* ================== Config media segura ================== */
const BACKEND_ORIGIN = (process.env.NEXT_PUBLIC_BACKEND_ORIGIN || "").replace(/\/+$/, "");

function resolveAnswerFileUrl(a: any): string | null {
  // 1) tomar la "materia prima": path crudo > url del back
  let raw: string | null = a?.answer_file_path || a?.answer_file || a?.file || null;
  if (!raw) return null;

  // 2) sacar un "resto" neutro SIN prefijos (ni api/, ni secure-media/, ni media/)
  let path = "";
  try {
    const abs = new URL(raw, typeof window !== "undefined" ? window.location.origin : "http://localhost");
    path = abs.pathname || "";
  } catch {
    path = String(raw || "");
  }
  path = path.replace(/\\/g, "/").replace(/\/{2,}/g, "/").replace(/^[./]+/, "");

  // cortar donde aparezca secure-media/ o media/
  let rest = path;
  const iSecure = rest.indexOf("secure-media/");
  if (iSecure !== -1) {
    rest = rest.slice(iSecure + "secure-media/".length);
  } else {
    const iMedia = rest.indexOf("media/");
    if (iMedia !== -1) {
      rest = rest.slice(iMedia + "media/".length);
    } else {
      // quitar prefijos "api/(v1/)?..." si los hubiera
      rest = rest
        .replace(/^api\/v\d+\//, "")
        .replace(/^api\//, "");
    }
  }
  rest = rest.replace(/^\/+/, "");

  // 3) construir la URL final en una sola forma (sin duplicar v1)
  if (BACKEND_ORIGIN) {
    return `${BACKEND_ORIGIN}/api/v1/secure-media/${rest}`;
  }
  return `/api/secure-media/${rest}`; // el proxy añadirá /v1/ una sola vez
}

/* ================== Helpers de formato ================== */
const tz = "America/Bogota";
const dt = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString("es-CO", { timeZone: tz }) : "—";
const norm = (s?: string | null) =>
  (s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

const isImage = (url: string) => {
  const u = url?.split("?")[0].toLowerCase();
  return (
    !!u &&
    [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"].some((ext) =>
      u.endsWith(ext)
    )
  );
};
const qidOf = (a: AnswerDetail) =>
  String(
    (a as any).question_id ??
      (a as any).questionId ??
      (a as any).question?.id ??
      ""
  );

/* ========== Index de preguntas (por si no vienen planas) ========== */
const buildQuestionIndex = (detail: any) => {
  const map = new Map<
    string,
    { text?: string | null; type?: string | null }
  >();
  const add = (arr?: any[]) => {
    if (!Array.isArray(arr)) return;
    for (const q of arr) {
      const idStr = String(q?.id ?? q?.uuid ?? q?.pk ?? "");
      if (!idStr) continue;
      const text = q?.text ?? q?.label ?? q?.title ?? q?.name ?? null;
      const type = q?.type ?? q?.question_type ?? null;
      map.set(idStr, { text, type });
    }
  };
  add(detail?.questionnaire?.questions);
  add(detail?.questions);
  add(detail?.questionnaire_questions);
  add(detail?.schema?.questions);
  add(detail?.questionnaireSchema?.questions);
  return map;
};

const getQText = (a: AnswerDetail, idx: Map<string, any>) =>
  (a as any).question_text ??
  a?.question?.text ??
  (a as any)?.question?.label ??
  (qidOf(a) && idx.get(qidOf(a))?.text) ??
  "(Pregunta eliminada)";

const getQType = (a: AnswerDetail, idx: Map<string, any>) =>
  (a as any).question_type ??
  a?.question?.type ??
  (qidOf(a) && idx.get(qidOf(a))?.type) ??
  "";

const hasAnswer = (a: AnswerDetail) =>
  Boolean(a.answer_text) ||
  Boolean(a.answer_choice?.text || (a as any).answer_choice_id) ||
  Boolean(resolveAnswerFileUrl(a));

/* ================== Skeleton ================== */
function Skeleton() {
  return (
    <main className="min-h-[60vh] px-6 md:px-8 py-10">
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="h-7 w-64 bg-slate-200 dark:bg-white/10 rounded animate-pulse" />
        <div className="h-4 w-96 bg-slate-200 dark:bg-white/10 rounded animate-pulse" />
        <div className="h-[1px] bg-slate-200 dark:bg-white/10" />
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="p-4 border rounded-xl border-slate-200 dark:border-white/10"
            >
              <div className="h-5 w-2/3 bg-slate-200 dark:bg-white/10 rounded animate-pulse" />
              <div className="mt-2 h-4 w-1/2 bg-slate-200 dark:bg-white/10 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}

/* ================== Página ================== */
export default function SubmissionDetailPage() {
  const router = useRouter();
  const params = useParams<{ id?: string | string[] }>();
  const id = Array.isArray(params?.id) ? params?.id?.[0] : params?.id;

  const [detail, setDetail] = useState<SubmissionDetail | null>(null);
  const [answers, setAnswers] = useState<AnswerDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // filtros (sin etiquetas)
  const [q, setQ] = useState("");
  const [typeFilter, setTypeFilter] = useState<
    "all" | "text" | "number" | "date" | "file" | "choice"
  >("all");
  const [answeredFilter, setAnsweredFilter] = useState<
    "all" | "answered" | "empty"
  >("all");
  const [sort, setSort] = useState<
    "original" | "qaz" | "time_desc" | "time_asc"
  >("original");

  // preview por Blob (para media protegida)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null); // Object URL
  const [previewOrig, setPreviewOrig] = useState<string | null>(null); // URL protegida original
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  async function openPreview(rawUrl: string) {
    console.log("[preview-url]", rawUrl); // ← depuración
    try {
      setPreviewError(null);
      setPreviewLoading(true);
      setPreviewOrig(rawUrl);
      const res = await fetch(rawUrl, { credentials: "include" });
      if (!res.ok) throw new Error(`No se pudo cargar la imagen (${res.status})`);
      const blob = await res.blob();
      const obj = URL.createObjectURL(blob);
      setPreviewUrl(obj);
    } catch (e: any) {
      setPreviewUrl(null);
      setPreviewError(e?.message || "No se pudo cargar la imagen");
    } finally {
      setPreviewLoading(false);
    }
  }
  function closePreview() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setPreviewOrig(null);
    setPreviewError(null);
    setPreviewLoading(false);
  }

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

    const bySearch = (a: AnswerDetail) => {
      if (!needle) return true;
      const fileUrl = resolveAnswerFileUrl(a);
      const blob =
        `${getQText(a, qIndex) || ""} ${a.answer_choice?.text || ""} ${a.answer_text || ""} ${fileUrl}`;
      return norm(blob).includes(needle);
    };

    const out = arr.filter((a) => byType(a) && byAnswered(a) && bySearch(a));

    const cmp =
      sort === "original"
        ? undefined
        : sort === "qaz"
        ? (a: AnswerDetail, b: AnswerDetail) =>
            (getQText(a, qIndex) || "").localeCompare(getQText(b, qIndex) || "")
        : sort === "time_desc"
        ? (a: AnswerDetail, b: AnswerDetail) =>
            Date.parse((b as any).timestamp || 0) -
            Date.parse((a as any).timestamp || 0)
        : (a: AnswerDetail, b: AnswerDetail) =>
            Date.parse((a as any).timestamp || 0) -
            Date.parse((b as any).timestamp || 0);

    if (cmp) out.sort(cmp as any);
    return out;
  }, [answers, q, typeFilter, answeredFilter, sort, qIndex]);

  if (!id || loading) return <Skeleton />;
  if (err)
    return (
      <main className="px-6 md:px-8 py-10">
        <div className="max-w-3xl mx-auto text-red-600">{err}</div>
      </main>
    );
  if (!detail) return null;

  const placa = (detail as any)?.placa_vehiculo
    ? String((detail as any).placa_vehiculo).toUpperCase()
    : "SIN PLACA";
  const estado = (detail as any)?.finalizado ? "Finalizado" : "En progreso";
  const total = answers.length;
  const shown = filtered.length;

  return (
    <main className="px-6 md:px-8 py-10">
      <div className="mx-auto max-w-4xl">
        {/* ENCABEZADO LIMPIO */}
        <div className="space-y-2">
          <button
            onClick={() => router.back()}
            className="text-sm text-slate-500 hover:text-slate-700 dark:text-white/60 dark:hover:text-white transition"
          >
            ← Volver
          </button>
          <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">
            {(detail as any).questionnaire_title || "Formulario"} ·{" "}
            {(detail as any).tipo_fase === "entrada" ? "Fase 1" : "Fase 2"}
          </h1>
          <p className="text-sm text-slate-600 dark:text-white/70">
            Placa <span className="font-medium">{placa}</span> · {estado} · ID{" "}
            <span className="font-mono">{String((detail as any).id)}</span>
            {(detail as any).fecha_cierre ? (
              <> · Cierre {dt((detail as any).fecha_cierre)}</>
            ) : null}
          </p>
        </div>

        <div className="mt-6 h-[1px] bg-slate-200 dark:bg-white/10" />

        {/* FILTROS */}
        <section className="mt-6">
          <div className="grid md:grid-cols-4 gap-3">
            <div className="md:col-span-2">
              <input
                type="search"
                placeholder="Buscar en preguntas y respuestas…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-white/15 bg-white dark:bg-slate-900 px-3 py-2 outline-none focus:ring-2 focus:ring-sky-300/40"
              />
            </div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as any)}
              className="rounded-lg border border-slate-300 dark:border-white/15 bg-white dark:bg-slate-900 px-3 py-2"
            >
              <option value="all">Tipo: todos</option>
              <option value="text">Texto</option>
              <option value="number">Número</option>
              <option value="date">Fecha</option>
              <option value="file">Archivo</option>
              <option value="choice">Opción</option>
            </select>
            <select
              value={answeredFilter}
              onChange={(e) => setAnsweredFilter(e.target.value as any)}
              className="rounded-lg border border-slate-300 dark:border-white/15 bg-white dark:bg-slate-900 px-3 py-2"
            >
              <option value="all">Respuestas: todas</option>
              <option value="answered">Solo contestadas</option>
              <option value="empty">Solo vacías</option>
            </select>
          </div>

          <div className="mt-3 flex items-center justify-between text-sm text-slate-600 dark:text-white/70">
            <div className="flex flex-wrap gap-3">
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as any)}
                className="rounded-lg border border-slate-300 dark:border-white/15 bg-white dark:bg-slate-900 px-3 py-2"
              >
                <option value="original">Orden original</option>
                <option value="qaz">Pregunta A–Z</option>
                <option value="time_desc">Más recientes primero</option>
                <option value="time_asc">Más antiguas primero</option>
              </select>
            </div>
            <div>
              Mostrando {shown} de {total}
            </div>
          </div>
        </section>

        {/* LISTA DE RESPUESTAS */}
        <section className="mt-8 space-y-3">
          {filtered.length === 0 ? (
            <div className="text-sm text-slate-600 dark:text-white/70">
              (Sin resultados)
            </div>
          ) : (
            filtered.map((a, idx) => {
              const qtext = getQText(a, qIndex);
              const typ = getQType(a, qIndex);
              const fileUrl = resolveAnswerFileUrl(a);
              const ans = a.answer_choice?.text ?? a.answer_text ?? "";
              const rawMeta = (a as any)?.meta;
              const metaEntries =
                rawMeta && typeof rawMeta === "object" && !Array.isArray(rawMeta)
                  ? Object.entries(rawMeta).filter(([_, v]) => v !== null && v !== "" && v !== undefined)
                  : [];

              return (
                <article
                  key={`${a.id || "ans"}-${idx}`}
                  className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white dark:bg-slate-900 shadow-sm"
                >
                  {/* Cabezal */}
                  <header className="px-4 md:px-5 pt-4 md:pt-5">
                    <h3 className="text-[15px] md:text-base font-semibold leading-6 text-slate-900 dark:text-white">
                      {qtext}
                    </h3>
                    <p className="mt-1 text-xs text-slate-500 dark:text-white/60">
                      {typ ? <>Tipo: {typ} · </> : null}
                      {(a as any).timestamp ? (
                        <>Enviado: {dt((a as any).timestamp)}</>
                      ) : null}
                    </p>
                  </header>

                  {/* Contenido */}
                  <div className="px-4 md:px-5 pb-4 md:pb-5">
                    {ans ? (
                      <div className="mt-3 rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/60 dark:bg-white/5 px-3 py-2.5 text-[15px] text-slate-800 dark:text-white/80 whitespace-pre-wrap break-words">
                        {ans}
                      </div>
                    ) : (
                      <div className="mt-3 text-sm text-slate-500 dark:text-white/60">
                        (Sin respuesta)
                      </div>
                    )}

                    {metaEntries.length > 0 && (
                      <div className="mt-3 rounded-xl border border-slate-200 dark:border-white/10 bg-white/70 dark:bg-white/5 px-3 py-3 text-sm text-slate-700 dark:text-white/70">
                        <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-white/50 mb-2">
                          Datos adicionales
                        </div>
                        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {metaEntries.map(([key, value]) => (
                            <div key={key} className="flex flex-col">
                              <dt className="text-xs text-slate-500 dark:text-white/50">
                                {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                              </dt>
                              <dd className="text-[15px] font-medium text-slate-800 dark:text-white/80">
                                {typeof value === "number" ? value : String(value)}
                              </dd>
                            </div>
                          ))}
                        </dl>
                      </div>
                    )}

                    {fileUrl && (
                      <div className="mt-3">
                        {isImage(fileUrl) ? (
                          <button
                            className="px-3 py-2 rounded-lg border border-slate-300 dark:border-white/15 hover:bg-slate-50 dark:hover:bg-white/5 text-sm"
                            onClick={() => openPreview(fileUrl)}
                          >
                            Ver imagen
                          </button>
                        ) : (
                          <a
                            href={fileUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-300 dark:border-white/15 hover:bg-slate-50 dark:hover:bg-white/5 text-sm"
                          >
                            Ver archivo
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                </article>
              );
            })
          )}
        </section>

        {/* MODAL PREVIEW */}
        {(previewUrl || previewLoading || previewError) && (
          <div
            className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
            onClick={closePreview}
          >
            <div
              className="bg-white dark:bg-slate-900 rounded-2xl overflow-hidden shadow-xl max-w-4xl w-full"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-4 py-2 border-b dark:border-white/10">
                <div className="font-medium">Vista previa</div>
                <button
                  className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-white/15 hover:bg-slate-50 dark:hover:bg-white/5 text-sm"
                  onClick={closePreview}
                >
                  Cerrar
                </button>
              </div>

              <div className="p-2 min-h-[50vh] flex items-center justify-center">
                {previewLoading && (
                  <div className="text-sm text-slate-600 dark:text-white/70">
                    Cargando imagen…
                  </div>
                )}
                {previewError && (
                  <div className="text-sm text-rose-600">{previewError}</div>
                )}
                {!previewLoading && !previewError && previewUrl && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={previewUrl}
                    alt="preview"
                    className="max-h-[70vh] w-full object-contain rounded-xl"
                  />
                )}
              </div>

              <div className="px-4 pb-3 flex gap-2">
                {previewUrl && (
                  <a
                    href={previewUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-300 dark:border-white/15 hover:bg-slate-50 dark:hover:bg-white/5 text-sm"
                  >
                    Abrir en pestaña
                  </a>
                )}
                {previewOrig && (
                  <a
                    href={previewOrig}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-300 dark:border-white/15 hover:bg-slate-50 dark:hover:bg-white/5 text-sm"
                    title="Abrir URL protegida directamente (requiere sesión)"
                  >
                    Abrir URL protegida
                  </a>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
