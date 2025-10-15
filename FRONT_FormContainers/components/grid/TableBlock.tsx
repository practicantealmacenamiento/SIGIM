"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { QuestionnaireGridLayout, TableRow, TableRowValue } from "@/lib/api.form";
import ActorInput from "../inputs/actorInput";

const DEFAULT_COLUMN_WIDTH = 220;
const MIN_COLUMN_WIDTH = 140;
const UUID_RE = /^[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[1-5][0-9a-fA-F]{3}\-[89abAB][0-9a-fA-F]{3}\-[0-9a-fA-F]{12}$/;

const ACTOR_TIPO: Record<string, "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR"> = {
  proveedor: "PROVEEDOR",
  transportista: "TRANSPORTISTA",
  receptor: "RECEPTOR",
};

type GridCellPatch = {
  answer_text?: string | null;
  answer_choice_id?: string | null;
  actor_id?: string | null;
};

type GridState = {
  rows: TableRow[];
  loading: boolean;
  error: string | null;
};

type Props = {
  table: QuestionnaireGridLayout["grids"][number];
  submissionId: string | null;
  state: GridState;
  onReload: () => Promise<void | TableRow[]>;
  onAddRow: () => Promise<number>;
  onUpdateCell: (rowIndex: number, questionId: string, patch: GridCellPatch) => Promise<void>;
  onDeleteRow: (rowIndex: number) => Promise<void>;
  onUploadFile: (rowIndex: number, questionId: string, file: File, answerText?: string | null) => Promise<void>;
};

type LocalRow = TableRow & { values: Record<string, TableRowValue & GridCellPatch> };

const emptyState: GridState = { rows: [], loading: false, error: null };

function makeCellKey(rowIndex: number, questionId: string) {
  return `${rowIndex}:${questionId}`;
}
function normalizeSemantic(raw?: string | null) {
  return String(raw ?? "").trim().toLowerCase();
}
function normalizeHint(column: any) {
  return normalizeSemantic(column?.ui_hint ?? column?.uiHint ?? column?.type);
}

export default function TableBlock({
  table,
  submissionId,
  state = emptyState,
  onReload,
  onAddRow,
  onUpdateCell,
  onDeleteRow,
  onUploadFile,
}: Props) {
  const tableId = String(table?.id ?? "");
  const isUUID = UUID_RE.test(tableId);

  const columns = useMemo(() => {
    const cols = Array.isArray(table?.columns) ? table.columns.slice() : [];
    return cols.sort((a: any, b: any) => {
      const ao = Number(a?.order ?? 0);
      const bo = Number(b?.order ?? 0);
      return ao - bo;
    });
  }, [table?.columns]);

  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
  const resizeContext = useRef<{ colId: string; startX: number; startWidth: number } | null>(null);

  const [draftRows, setDraftRows] = useState<LocalRow[]>([]);
  const [localError, setLocalError] = useState<string | null>(null);
  const [, forceRender] = useState(0);

  const dirtyCells = useRef<Set<string>>(new Set());
  const dirtyValues = useRef<Map<string, GridCellPatch>>(new Map());
  const savingCells = useRef<Set<string>>(new Set());
  const uploadingCells = useRef<Set<string>>(new Set());

  useEffect(() => {
    const nextRows: LocalRow[] = (state?.rows ?? []).map((row) => ({
      ...row,
      values: { ...row.values },
    }));
    setDraftRows(nextRows);
  }, [state?.rows]);

  useEffect(() => {
    function onMouseMove(event: MouseEvent) {
      const ctx = resizeContext.current;
      if (!ctx) return;
      const delta = event.clientX - ctx.startX;
      const nextWidth = Math.max(MIN_COLUMN_WIDTH, ctx.startWidth + delta);
      setColumnWidths((prev) => ({ ...prev, [ctx.colId]: nextWidth }));
    }
    function onMouseUp() {
      resizeContext.current = null;
    }
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  const resolveColumnWidth = useCallback(
    (colId: string) => {
      const stateWidth = columnWidths[colId];
      if (typeof stateWidth === "number" && Number.isFinite(stateWidth)) {
        return Math.max(MIN_COLUMN_WIDTH, stateWidth);
      }
      const original = columns.find((c) => String(c?.question_id) === String(colId))?.width;
      const originalNumber = Number(original);
      if (Number.isFinite(originalNumber)) {
        return Math.max(MIN_COLUMN_WIDTH, originalNumber);
      }
      return DEFAULT_COLUMN_WIDTH;
    },
    [columnWidths, columns]
  );

  const handleResizeStart = useCallback(
    (event: React.MouseEvent<HTMLButtonElement>, colId: string) => {
      event.preventDefault();
      event.stopPropagation();
      const width = resolveColumnWidth(colId);
      resizeContext.current = { colId, startX: event.clientX, startWidth: width };
    },
    [resolveColumnWidth]
  );

  const markDirty = useCallback((key: string, patch: GridCellPatch) => {
    dirtyCells.current.add(key);
    const current = dirtyValues.current.get(key) ?? {};
    dirtyValues.current.set(key, { ...current, ...patch });
  }, []);

  const submitCell = useCallback(
    async (rowIndex: number, questionId: string, patchOverride?: GridCellPatch) => {
      const key = makeCellKey(rowIndex, questionId);
      const patch = patchOverride ?? dirtyValues.current.get(key);
      if (!patch) return;
      savingCells.current.add(key);
      setLocalError(null);
      forceRender((v) => v + 1);
      try {
        await onUpdateCell(rowIndex, questionId, patch);
        dirtyCells.current.delete(key);
        dirtyValues.current.delete(key);
      } catch (error: any) {
        const msg = error?.message || "No se pudo guardar la celda.";
        setLocalError(msg);
        await onReload();
      } finally {
        savingCells.current.delete(key);
        forceRender((v) => v + 1);
      }
    },
    [onUpdateCell, onReload]
  );

  const handleBlur = useCallback(
    async (rowIndex: number, questionId: string) => {
      const key = makeCellKey(rowIndex, questionId);
      if (!dirtyCells.current.has(key)) return;
      await submitCell(rowIndex, questionId);
    },
    [submitCell]
  );

  const handleKeyDown = useCallback(
    async (event: React.KeyboardEvent<HTMLInputElement | HTMLSelectElement>, rowIndex: number, questionId: string) => {
      if (event.key === "Enter") {
        event.preventDefault();
        await submitCell(rowIndex, questionId);
      }
    },
    [submitCell]
  );

  const handleTextChange = useCallback(
    (rowIndex: number, questionId: string, value: string) => {
      setDraftRows((prev) => {
        return prev.map((row) => {
          if (row.row_index !== rowIndex) return row;
          return {
            ...row,
            values: {
              ...row.values,
              [questionId]: {
                ...(row.values[questionId] ?? {}),
                answer_text: value,
              },
            },
          };
        });
      });
      markDirty(makeCellKey(rowIndex, questionId), { answer_text: value });
    },
    [markDirty]
  );

  const handleReload = useCallback(async () => {
    try {
      await onReload();
      setLocalError(null);
    } catch (error: any) {
      const msg = error?.message || "No se pudo recargar la tabla.";
      setLocalError(msg);
    }
  }, [onReload]);

  const handleChoiceChange = useCallback(
    async (rowIndex: number, questionId: string, value: string, label: string) => {
      setDraftRows((prev) =>
        prev.map((row) => {
          if (row.row_index !== rowIndex) return row;
          return {
            ...row,
            values: {
              ...row.values,
              [questionId]: {
                ...(row.values[questionId] ?? {}),
                answer_choice_id: value || null,
                answer_text: label,
              },
            },
          };
        })
      );
      await submitCell(rowIndex, questionId, { answer_choice_id: value || null, answer_text: label || null });
    },
    [submitCell]
  );

  const handleActorSelect = useCallback(
    async (rowIndex: number, questionId: string, actor: { id: string; nombre: string }) => {
      setDraftRows((prev) =>
        prev.map((row) => {
          if (row.row_index !== rowIndex) return row;
          return {
            ...row,
            values: {
              ...row.values,
              [questionId]: {
                ...(row.values[questionId] ?? {}),
                answer_text: actor.nombre,
              },
            },
          };
        })
      );
      await submitCell(rowIndex, questionId, { answer_text: actor.nombre, actor_id: actor.id });
    },
    [submitCell]
  );

  const handleFileChange = useCallback(
    async (rowIndex: number, questionId: string, fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return;
      const file = fileList[0];
      const key = makeCellKey(rowIndex, questionId);
      uploadingCells.current.add(key);
      setLocalError(null);
      forceRender((v) => v + 1);
      try {
        // Adjuntamos también el answer_text actual de la celda (si existe) por consistencia
        const currentText =
          draftRows.find((r) => r.row_index === rowIndex)?.values[questionId]?.answer_text ?? null;
        await onUploadFile(rowIndex, questionId, file, currentText);
        await onReload();
      } catch (error: any) {
        const msg = error?.message || "No se pudo subir el archivo.";
        setLocalError(msg);
      } finally {
        uploadingCells.current.delete(key);
        forceRender((v) => v + 1);
      }
    },
    [onUploadFile, onReload, draftRows]
  );

  const handleAddRow = useCallback(async () => {
    if (!submissionId) {
      setLocalError("Debes iniciar la submission antes de agregar filas.");
      return;
    }
    try {
      await onAddRow();
      setLocalError(null);
    } catch (error: any) {
      const msg = error?.message || "No se pudo crear la fila.";
      setLocalError(msg);
    }
  }, [onAddRow, submissionId]);

  const handleDeleteRow = useCallback(
    async (rowIndex: number) => {
      try {
        await onDeleteRow(rowIndex);
        setLocalError(null);
      } catch (error: any) {
        const msg = error?.message || "No se pudo eliminar la fila.";
        setLocalError(msg);
      }
    },
    [onDeleteRow]
  );

  const isSaving = useCallback(
    (rowIndex: number, questionId: string) => savingCells.current.has(makeCellKey(rowIndex, questionId)),
    []
  );
  const isUploading = useCallback(
    (rowIndex: number, questionId: string) => uploadingCells.current.has(makeCellKey(rowIndex, questionId)),
    []
  );

  const effectiveState = state ?? emptyState;
  const rows = draftRows;

  return (
    <div className="space-y-3">
      {(table?.title || table?.subtitle) && (
        <header className="flex items-center justify-between">
          <div>
            {table?.title && (
              <h3 className="text-lg font-semibold text-slate-800 dark:text-white">{table.title}</h3>
            )}
            {table?.subtitle && (
              <p className="text-sm text-slate-500 dark:text-slate-300">{table.subtitle}</p>
            )}
          </div>
          <div className="flex gap-2 text-sm text-slate-500 dark:text-slate-300">
            <button
              type="button"
              onClick={handleReload}
              className="rounded-lg border border-slate-200 dark:border-white/10 px-3 py-1.5 hover:bg-slate-50 dark:hover:bg-white/5"
              disabled={effectiveState.loading}
            >
              Recargar
            </button>
            <button
              type="button"
              onClick={handleAddRow}
              className="rounded-lg bg-skyBlue px-3 py-1.5 text-white hover:bg-skyBlue/90 disabled:opacity-60"
              disabled={effectiveState.loading || !submissionId}
            >
              Nueva fila
            </button>
          </div>
        </header>
      )}

      {/* Diagnóstico del ID de la tabla */}
      {!tableId ? (
        <div className="rounded-xl border border-slate-300/60 bg-slate-50/80 dark:bg-slate-900/40 dark:border-white/15 px-4 py-3 text-sm text-slate-700 dark:text-slate-200">
          Este grid no trae <strong>ID</strong> desde el layout. Operaremos sin <code>table_id</code> en la API
          (válido si este cuestionario tiene un único grid). Si el backend requiere un identificador, expón
          <code> tabular_group_id</code> (UUID) en <code>/grids/</code>.
        </div>
      ) : (
        !isUUID && (
          <div className="rounded-xl border border-amber-300/60 bg-amber-50/70 dark:bg-amber-400/10 dark:border-amber-300/20 px-4 py-3 text-sm text-amber-900 dark:text-amber-200">
            El ID del grid no parece UUID (<code>{tableId}</code>). Intentaremos usarlo; si el backend exige UUID, expón
            <code> tabular_group_id</code> en <code>/grids/</code>.
          </div>
        )
      )}

      {effectiveState.loading && (
        <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/60 dark:bg-white/5 px-4 py-3 text-sm">
          Cargando filas...
        </div>
      )}

      {effectiveState.error && (
        <div className="rounded-xl border border-amber-300/60 bg-amber-50/70 dark:bg-amber-400/10 dark:border-amber-300/20 px-4 py-3 text-sm text-amber-900 dark:text-amber-200">
          {effectiveState.error}
        </div>
      )}

      {localError && (
        <div className="rounded-xl border border-rose-300/60 bg-rose-50/80 dark:bg-rose-950/30 px-4 py-3 text-sm text-rose-700 dark:text-rose-200">
          {localError}
        </div>
      )}

      <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 shadow-sm">
        <table className="min-w-full table-fixed divide-y divide-slate-200 dark:divide-white/10">
          <colgroup>
            <col style={{ width: 80 }} />
            {columns.map((column) => (
              <col
                key={`col-${column.question_id}`}
                style={{ width: resolveColumnWidth(String(column.question_id)) }}
              />
            ))}
            <col style={{ width: 110 }} />
          </colgroup>
          <thead className="bg-slate-50/80 dark:bg-slate-900/40">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-300">
                Fila
              </th>
              {columns.map((column) => {
                const width = resolveColumnWidth(String(column.question_id));
                return (
                  <th
                    key={column.question_id}
                    scope="col"
                    className="relative px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300"
                    style={{ width, minWidth: MIN_COLUMN_WIDTH }}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span>{column.header || column.question_id}</span>
                      <button
                        type="button"
                        onMouseDown={(event) => handleResizeStart(event, String(column.question_id))}
                        className="h-6 w-1.5 cursor-col-resize rounded-full bg-slate-300/70 dark:bg-white/20"
                        aria-label="Ajustar ancho"
                      />
                    </div>
                  </th>
                );
              })}
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-300">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-white/5">
            {rows.length === 0 && !effectiveState.loading ? (
              <tr>
                <td
                  colSpan={columns.length + 2}
                  className="px-4 py-6 text-center text-sm text-slate-500 dark:text-slate-400"
                >
                  No hay filas registradas aún.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={`row-${row.row_index}`} className="align-top">
                  <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-300">{row.row_index}</td>
                  {columns.map((column) => {
                    const qid = String(column.question_id);
                    const cellKey = makeCellKey(row.row_index, qid);
                    const value = row.values[qid] || {};
                    const semantic = normalizeSemantic(column.semantic_tag ?? column.semanticTag);
                    const hint = normalizeHint(column);
                    const saving = isSaving(row.row_index, qid);
                    const uploading = isUploading(row.row_index, qid);

                    let content: ReactNode;

                    if (semantic in ACTOR_TIPO) {
                      content = (
                        <ActorInput
                          tipo={ACTOR_TIPO[semantic]}
                          defaultValue={value.answer_text || ""}
                          disabled={saving || uploading}
                          onSelect={(actor) => handleActorSelect(row.row_index, qid, actor)}
                          className="text-sm"
                        />
                      );
                    } else if (hint === "select" && Array.isArray(column.options) && column.options.length > 0) {
                      content = (
                        <select
                          value={value.answer_choice_id || ""}
                          onChange={(event) => {
                            const opt = column.options?.find((o) => o.value === event.target.value);
                            handleChoiceChange(row.row_index, qid, event.target.value, opt?.label || "");
                          }}
                          onKeyDown={(event) => handleKeyDown(event, row.row_index, qid)}
                          className="w-full rounded-lg border border-slate-300 dark:border-white/15 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
                        >
                          <option value="">Seleccione una opción</option>
                          {column.options?.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      );
                    } else if (hint === "file") {
                      content = (
                        <div className="space-y-2 text-sm">
                          <input
                            type="file"
                            accept="image/*"
                            onChange={(event) => handleFileChange(row.row_index, qid, event.target.files)}
                            disabled={uploading || saving}
                            className="block w-full text-sm"
                          />
                          {value.answer_file_path && (
                            <a
                              href={value.answer_file_path}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-skyBlue underline"
                            >
                              Ver archivo
                            </a>
                          )}
                        </div>
                      );
                    } else {
                      const type = hint === "number" ? "number" : hint === "date" ? "date" : "text";
                      content = (
                        <input
                          type={type}
                          value={value.answer_text ?? ""}
                          onChange={(event) => handleTextChange(row.row_index, qid, event.target.value)}
                          onBlur={() => handleBlur(row.row_index, qid)}
                          onKeyDown={(event) => handleKeyDown(event, row.row_index, qid)}
                          disabled={saving}
                          className="w-full rounded-lg border border-slate-300 dark:border-white/15 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
                        />
                      );
                    }

                    return (
                      <td
                        key={cellKey}
                        className="px-4 py-3 align-top"
                        style={{ width: resolveColumnWidth(String(column.question_id)), minWidth: MIN_COLUMN_WIDTH }}
                      >
                        <div className="flex flex-col gap-1 text-sm text-slate-700 dark:text-slate-200">
                          {content}
                          {(saving || uploading) && (
                            <span className="text-xs text-slate-400" aria-live="polite">
                              {uploading ? "Subiendo archivo..." : "Guardando..."}
                            </span>
                          )}
                        </div>
                      </td>
                    );
                  })}
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => handleDeleteRow(row.row_index)}
                      className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-100 dark:border-rose-500/40 dark:bg-rose-900/40 dark:text-rose-200"
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
