import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createTableRow,
  deleteTableRow,
  fetchCatalogActors,
  getQuestionnaireGrid,
  listSubmissionTableRows,
  updateTableRow,
} from "@/lib/api.form";
import type {
  ActorLite,
  GridDefinition,
  GridColumn,
  TableRowCellsPayload,
  TableRowRecord,
} from "@/lib/api.form";

/**
 * TableForm
 * - Pinta un grid idéntico al Excel usando el layout del backend.
 * - Permite agregar/editar/eliminar filas contra los endpoints tabulares.
 *
 * Props mínimas:
 *  - questionnaireId: UUID del cuestionario (Fase 0)
 *  - submissionId: UUID de la submission activa
 *
 * Opcional:
 *  - actorSearch?: (tipo: "PROVEEDOR"|"TRANSPORTISTA"|"RECEPTOR", q: string) => Promise<Array<{id:string;nombre:string;documento?:string}>>
 */

type Column = GridColumn;
type GridDef = GridDefinition;
type RowDTO = TableRowRecord;

// Helpers

const excelWidthToPx = (w?: number | null) => {
  if (!w) return undefined;
  // 1 unidad "Excel column width" ~ 7.0~8.0 px dependiendo de fuente; usamos 8 como aproximación.
  return Math.round(w * 8);
};

const semanticIsActor = (tag?: string | null) =>
  !!tag && ["proveedor", "transportista", "receptor"].includes(tag.toLowerCase());

// Sencillo debounce hook para búsquedas
const useDebounced = (value: string, delay = 250) => {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
};

type Props = {
  questionnaireId: string;
  submissionId: string;
  actorSearch?: (
    tipo: "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR",
    q: string
  ) => Promise<Array<{ id: string; nombre: string; documento?: string }>>;
};

export default function TableForm({
  questionnaireId,
  submissionId,
  actorSearch,
}: Props) {
  const [grid, setGrid] = useState<GridDef | null>(null);
  const [rows, setRows] = useState<RowDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [savingRow, setSavingRow] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const aliveRef = useRef(true);
  useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
    };
  }, []);

  const refreshRows = useCallback(async () => {
    const payload = await listSubmissionTableRows(submissionId);
    const rowsIn = Array.isArray(payload?.rows) ? payload.rows : [];
    if (aliveRef.current) {
      setRows(rowsIn);
    }
  }, [submissionId]);

  // --- carga layout y filas ---
  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        if (!questionnaireId || !submissionId) {
          return;
        }
        const layout = await getQuestionnaireGrid(questionnaireId);
        const columns = Array.isArray(layout?.columns) ? [...layout.columns] : [];
        columns.sort((a, b) => (a.order ?? 0) - (b.order ?? 0));

        const payload = await listSubmissionTableRows(submissionId);
        const rowsIn = Array.isArray(payload?.rows) ? payload.rows : [];

        if (mounted && aliveRef.current) {
          setGrid({ ...layout, columns });
          setRows(rowsIn);
        }
      } catch (e: any) {
        if (mounted && aliveRef.current) {
          setError(typeof e?.message === "string" ? e.message : "Error cargando datos");
        }
      } finally {
        if (mounted && aliveRef.current) {
          setLoading(false);
        }
      }
    })();
    return () => {
      mounted = false;
    };
  }, [questionnaireId, submissionId]);

  const nextRowIndex = useMemo(() => {
    const indexes = rows.map((r) => r.row_index);
    return indexes.length ? Math.max(...indexes) + 1 : 1;
  }, [rows]);

  // --- edición local (UI state) ---
  type LocalCell = {
    text?: string;
    actor?: { id: string; nombre: string } | null;
  };
  type LocalRow = {
    row_index: number;
    cells: Record<string, LocalCell>; // key = question_id
    _isNew?: boolean;
  };

  const [editRows, setEditRows] = useState<Record<number, LocalRow>>({});

  // inicializa edición de una fila (desde DTO o vacía)
  const startEdit = useCallback(
    (row?: RowDTO) => {
      if (!grid) return;
      const row_index = row?.row_index ?? nextRowIndex;
      const cells: Record<string, LocalCell> = {};
      grid.columns.forEach((col) => {
        const val = row?.values?.[col.question_id];
        if (semanticIsActor(col.semantic_tag)) {
          const actorId = val?.actor_id ?? null;
          const actorName =
            typeof val?.actor_name === "string" && val.actor_name.trim()
              ? val.actor_name
              : actorId || "";
          cells[col.question_id] = {
            actor: actorId ? { id: actorId, nombre: actorName || actorId } : null,
          };
        } else {
          cells[col.question_id] = { text: val?.answer_text ?? "" };
        }
      });
      setEditRows((prev) => ({
        ...prev,
        [row_index]: { row_index, cells, _isNew: !row },
      }));
    },
    [grid, nextRowIndex]
  );

  const cancelEdit = useCallback((row_index: number) => {
    setEditRows((p) => {
      const n = { ...p };
      delete n[row_index];
      return n;
    });
  }, []);

  const addEmptyRow = useCallback(() => startEdit(undefined), [startEdit]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handler = () => addEmptyRow();
    window.addEventListener("phase0:addRow", handler);
    return () => {
      window.removeEventListener("phase0:addRow", handler);
    };
  }, [addEmptyRow]);

  // --- búsquedas de actores ---
  const defaultActorSearch = useCallback(
    async (tipo: "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR", q: string) => {
      const term = q.trim();
      if (!term) return [];
      try {
        const results = await fetchCatalogActors({ tipo, search: term, limit: 20 });
        return results.map((actor: ActorLite) => ({
          id: actor.id,
          nombre: actor.nombre,
          documento: actor.documento ?? undefined,
        }));
      } catch (err) {
        return [];
      }
    },
    []
  );

  const actorFetcher = actorSearch ?? defaultActorSearch;

  // --- guardar fila ---
  const saveRow = async (row_index: number) => {
    const lr = editRows[row_index];
    if (!grid || !lr) return;
    setSavingRow(row_index);
    setError(null);
    try {
      const cells: TableRowCellsPayload[] = grid.columns.map((col) => {
        const cell = lr.cells[col.question_id] ?? {};
        if (semanticIsActor(col.semantic_tag)) {
          const tag = (col.semantic_tag || "").toLowerCase();
          const actorId = cell.actor?.id ?? "";
          if (!actorId) throw new Error(`Falta seleccionar ${tag} en la fila ${row_index}`);
          return { question_id: col.question_id, actor_id: actorId };
        }
        return {
          question_id: col.question_id,
          answer_text: (cell.text ?? "").trim(),
        };
      });

      const basePayload = {
        submissionId: submissionId,
        rowIndex: lr.row_index,
        cells,
      };

      if (lr._isNew) {
        await createTableRow(basePayload);
      } else {
        await updateTableRow({ ...basePayload, rowIndex: row_index });
      }

      await refreshRows();
      cancelEdit(row_index);
    } catch (e: any) {
      setError(e?.message || "Error al guardar fila");
    } finally {
      setSavingRow(null);
    }
  };

  const deleteRow = async (row_index: number) => {
    if (!confirm(`¿Eliminar fila ${row_index}?`)) return;
    try {
      await deleteTableRow(submissionId, row_index);
      await refreshRows();
      cancelEdit(row_index);
    } catch (e: any) {
      setError(e?.message || "No se pudo eliminar la fila");
    }
  };

  // --- render ---
  if (loading) {
    return (
      <div className="p-4 text-sm text-slate-600">Cargando formulario…</div>
    );
  }
  if (error) {
    return (
      <div className="p-4 text-sm text-red-600">
        Error: <span className="font-mono">{error}</span>
      </div>
    );
  }
  if (!grid) return null;

  return (
    <div className="w-full">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">{grid.title}</h2>
          <p className="text-xs text-slate-500">
            Versión {grid.version} · Zona horaria {grid.timezone}
          </p>
        </div>
        <button
          onClick={addEmptyRow}
          className="px-3 py-2 rounded-md bg-indigo-600 text-white text-sm hover:bg-indigo-700 shadow"
        >
          + Añadir fila
        </button>
      </div>

      <div className="overflow-auto rounded-lg border border-slate-200 shadow-sm">
        <table className="min-w-full border-collapse">
          <thead className="bg-slate-50">
            <tr>
              <th className="sticky left-0 z-10 bg-slate-50 border-b border-r p-2 text-left text-xs text-slate-500">
                #
              </th>
              {grid.columns.map((c) => (
                <th
                  key={c.question_id}
                  className="border-b p-2 text-left text-xs text-slate-500"
                  style={{ width: excelWidthToPx(c.width) }}
                  title={c.header}
                >
                  {c.header}
                </th>
              ))}
              <th className="border-b p-2 text-left text-xs text-slate-500">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody>
            {/* filas existentes */}
            {rows.map((r) => {
              const isEditing = !!editRows[r.row_index];
              return (
                <tr key={`row-${r.row_index}`} className="even:bg-slate-50/40">
                  <td className="sticky left-0 z-10 bg-white border-t border-r p-2 text-xs text-slate-700">
                    {r.row_index}
                  </td>
                  {grid.columns.map((c) => {
                    const cellKey = c.question_id;
                    if (isEditing) {
                      const lr = editRows[r.row_index]!;
                      return (
                        <td key={cellKey} className="border-t p-0">
                          <CellEditor
                            column={c}
                            value={lr.cells[cellKey]}
                            onChange={(nv) =>
                              setEditRows((prev) => ({
                                ...prev,
                                [r.row_index]: {
                                  ...prev[r.row_index],
                                  cells: {
                                    ...prev[r.row_index].cells,
                                    [cellKey]: nv,
                                  },
                                },
                              }))
                            }
                            actorFetcher={actorFetcher}
                          />
                        </td>
                      );
                    }

                    const val = r.values[cellKey];
                    return (
                      <td key={cellKey} className="border-t p-2 text-sm">
                        {semanticIsActor(c.semantic_tag) ? (
                          val?.actor_id ? (
                            <div className="flex flex-col gap-1">
                              <span className="text-sm font-medium text-slate-700">
                                {val.actor_name ?? "Actor seleccionado"}
                              </span>
                              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                                {val.actor_document && (
                                  <span className="rounded bg-slate-100 px-1.5 py-0.5">
                                    {val.actor_document}
                                  </span>
                                )}
                                <code className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px]">
                                  {val.actor_id}
                                </code>
                              </div>
                            </div>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )
                        ) : (
                          val?.answer_text ?? <span className="text-slate-400">—</span>
                        )}
                      </td>
                    );
                  })}
                  <td className="border-t p-2">
                    {isEditing ? (
                      <div className="flex gap-2">
                        <button
                          disabled={savingRow === r.row_index}
                          onClick={() => saveRow(r.row_index)}
                          className="px-2 py-1 text-xs rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
                        >
                          {savingRow === r.row_index ? "Guardando…" : "Guardar"}
                        </button>
                        <button
                          onClick={() => cancelEdit(r.row_index)}
                          className="px-2 py-1 text-xs rounded bg-slate-200 hover:bg-slate-300"
                        >
                          Cancelar
                        </button>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        <button
                          onClick={() => startEdit(r)}
                          className="px-2 py-1 text-xs rounded bg-indigo-600 text-white hover:bg-indigo-700"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => deleteRow(r.row_index)}
                          className="px-2 py-1 text-xs rounded bg-rose-600 text-white hover:bg-rose-700"
                        >
                          Eliminar
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}

            {/* fila nueva en edición */}
            {Object.values(editRows)
              .filter((r) => r._isNew)
              .map((r) => (
                <tr key={`row-new-${r.row_index}`} className="bg-yellow-50">
                  <td className="sticky left-0 z-10 bg-yellow-50 border-t border-r p-2 text-xs text-slate-700">
                    {r.row_index}
                  </td>
                  {grid.columns.map((c) => {
                    const cellKey = c.question_id;
                    return (
                      <td key={cellKey} className="border-t p-0">
                        <CellEditor
                          column={c}
                          value={r.cells[cellKey]}
                          onChange={(nv) =>
                            setEditRows((prev) => ({
                              ...prev,
                              [r.row_index]: {
                                ...prev[r.row_index],
                                cells: { ...prev[r.row_index].cells, [cellKey]: nv },
                              },
                            }))
                          }
                          actorFetcher={actorFetcher}
                        />
                      </td>
                    );
                  })}
                  <td className="border-t p-2">
                    <div className="flex gap-2">
                      <button
                        disabled={savingRow === r.row_index}
                        onClick={() => saveRow(r.row_index)}
                        className="px-2 py-1 text-xs rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
                      >
                        {savingRow === r.row_index ? "Guardando…" : "Guardar"}
                      </button>
                      <button
                        onClick={() => cancelEdit(r.row_index)}
                        className="px-2 py-1 text-xs rounded bg-slate-200 hover:bg-slate-300"
                      >
                        Cancelar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// =================== Celdas editables ===================

function CellEditor({
  column,
  value,
  onChange,
  actorFetcher,
}: {
  column: Column;
  value?: { text?: string; actor?: { id: string; nombre: string } | null };
  onChange: (v: { text?: string; actor?: { id: string; nombre: string } | null }) => void;
  actorFetcher: (
    tipo: "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR",
    q: string
  ) => Promise<Array<{ id: string; nombre: string; documento?: string }>>;
}) {
  const tag = (column.semantic_tag || "").toLowerCase();
  if (semanticIsActor(tag)) {
    const tipo =
      tag === "proveedor"
        ? "PROVEEDOR"
        : tag === "transportista"
        ? "TRANSPORTISTA"
        : "RECEPTOR";
    return (
      <ActorAutocomplete
        tipo={tipo as any}
        value={value?.actor ?? null}
        onChange={(actor) => onChange({ ...value, actor })}
        actorFetcher={actorFetcher}
      />
    );
  }

  // inputs básicos por ui_hint
  const hint = (column.ui_hint || "text").toLowerCase();
  const inputType =
    hint === "date" ? "date" : hint === "time" ? "time" : "text";

  return (
    <input
      type={inputType}
      value={value?.text ?? ""}
      onChange={(e) => onChange({ ...value, text: e.target.value })}
      className="w-full px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-indigo-500/50"
      placeholder={column.header}
    />
  );
}

// =============== Autocomplete simple de actores ===============

function ActorAutocomplete({
  tipo,
  value,
  onChange,
  actorFetcher,
}: {
  tipo: "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR";
  value: { id: string; nombre: string } | null;
  onChange: (v: { id: string; nombre: string } | null) => void;
  actorFetcher: (
    tipo: "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR",
    q: string
  ) => Promise<Array<{ id: string; nombre: string; documento?: string }>>;
}) {
  const [q, setQ] = useState("");
  const dq = useDebounced(q, 200);
  const [opts, setOpts] = useState<Array<{ id: string; nombre: string; documento?: string }>>([]);
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      if (!dq) {
        setOpts([]);
        return;
      }
      const res = await actorFetcher(tipo, dq);
      if (mounted) setOpts(res);
    })();
    return () => {
      mounted = false;
    };
  }, [dq, tipo, actorFetcher]);

  useEffect(() => {
    if (value) {
      setQ(value.nombre);
    }
  }, [value?.id, value?.nombre]);

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="text"
        value={value?.nombre ?? q}
        onChange={(e) => {
          onChange(null); // limpiar selección si escribe
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder={`Buscar ${tipo.toLowerCase()}...`}
        className="w-full px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-indigo-500/50"
      />
      {open && opts.length > 0 && (
        <div className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-md border border-slate-200 bg-white shadow-lg">
          {opts.map((o) => (
            <button
              key={o.id}
              type="button"
              onClick={() => {
                onChange({ id: o.id, nombre: o.nombre });
                setQ("");
                setOpts([]);
                setOpen(false);
                inputRef.current?.blur();
              }}
              className="block w-full cursor-pointer px-3 py-2 text-left text-sm hover:bg-indigo-50"
            >
              <div className="font-medium">{o.nombre}</div>
              {o.documento && (
                <div className="text-xs text-slate-500">NIT: {o.documento}</div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
