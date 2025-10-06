import React, { useEffect, useMemo, useRef, useState } from "react";

/**
 * TableForm
 * - Pinta un grid idéntico al Excel usando el layout del backend.
 * - Permite agregar/editar/eliminar filas contra los endpoints tabulares.
 *
 * Props mínimas:
 *  - questionnaireId: UUID del cuestionario (Fase 0)
 *  - submissionId: UUID de la submission activa
 *  - token: JWT/Bearer
 *
 * Opcionales:
 *  - apiBase: string (default "/api/v1")
 *  - actorSearch?: (tipo: "PROVEEDOR"|"TRANSPORTISTA"|"RECEPTOR", q: string) => Promise<Array<{id:string;nombre:string;documento?:string}>>
 */

type Column = {
  question_id: string;
  header: string;
  width?: number | null;
  order: number;
  semantic_tag?: string | null; // "proveedor" | "transportista" | "receptor" | "placa" | ...
  ui_hint?: string | null;      // "text" | "date" | "time" | "phone" | ...
};

type GridDef = {
  questionnaire_id: string;
  title: string;
  version: string;
  timezone: string;
  columns: Column[];
};

type RowDTO = {
  submission_id: string;
  row_index: number;
  values: Record<
    string, // question_id
    {
      answer_text?: string | null;
      answer_choice_id?: string | null;
      answer_file_path?: string | null;
      actor_id?: string | null;
    }
  >;
};

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
  token: string;
  apiBase?: string;
  actorSearch?: (
    tipo: "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR",
    q: string
  ) => Promise<Array<{ id: string; nombre: string; documento?: string }>>;
};

export default function TableForm({
  questionnaireId,
  submissionId,
  token,
  apiBase = "/api/v1",
  actorSearch,
}: Props) {
  const [grid, setGrid] = useState<GridDef | null>(null);
  const [rows, setRows] = useState<RowDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [savingRow, setSavingRow] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // --- carga layout y filas ---
  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        // layout
        const resL = await fetch(
          `${apiBase}/cuestionarios/${questionnaireId}/grid/`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (!resL.ok) throw new Error(`Grid ${resL.status}`);
        const layout: GridDef = await resL.json();
        // ordenar columnas por order (defensivo)
        layout.columns.sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
        // filas existentes
        const resR = await fetch(
          `${apiBase}/submissions/${submissionId}/table-rows`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (!resR.ok) throw new Error(`Rows ${resR.status}`);
        const payload = await resR.json();
        const rowsIn: RowDTO[] = payload?.rows ?? [];
        if (mounted) {
          setGrid(layout);
          setRows(rowsIn);
        }
      } catch (e: any) {
        if (mounted) setError(e?.message || "Error cargando datos");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [apiBase, questionnaireId, submissionId, token]);

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
  const startEdit = (row?: RowDTO) => {
    const row_index = row?.row_index ?? nextRowIndex;
    const cells: Record<string, LocalCell> = {};
    (grid?.columns ?? []).forEach((col) => {
      const val = row?.values?.[col.question_id];
      if (semanticIsActor(col.semantic_tag)) {
        cells[col.question_id] = {
          actor: val?.actor_id
            ? { id: val.actor_id, nombre: "" } // label lazy (se rellenará tras búsqueda si hace falta)
            : null,
        };
      } else {
        cells[col.question_id] = { text: val?.answer_text ?? "" };
      }
    });
    setEditRows((prev) => ({
      ...prev,
      [row_index]: { row_index, cells, _isNew: !row },
    }));
  };

  const cancelEdit = (row_index: number) => {
    setEditRows((p) => {
      const n = { ...p };
      delete n[row_index];
      return n;
    });
  };

  const addEmptyRow = () => startEdit(undefined);

  // --- búsquedas de actores ---
  const defaultActorSearch = async (
    tipo: "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR",
    q: string
  ) => {
    // Ajusta este endpoint si tu catálogo público difiere
    // AdminActorViewSet en tu backend acepta ?search=&tipo=
    const res = await fetch(
      `${apiBase}/admin/actores/?tipo=${encodeURIComponent(
        tipo
      )}&search=${encodeURIComponent(q)}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (!res.ok) return [];
    const data = await res.json();
    const items = Array.isArray(data?.results) ? data.results : data;
    return (items ?? []).map((a: any) => ({
      id: a.id,
      nombre: a.nombre,
      documento: a.documento,
    }));
  };

  const actorFetcher = actorSearch ?? defaultActorSearch;

  // --- guardar fila ---
  const saveRow = async (row_index: number) => {
    const lr = editRows[row_index];
    if (!grid || !lr) return;
    setSavingRow(row_index);
    setError(null);
    try {
      // Construir FormData con cells[]
      const fd = new FormData();
      const cells = grid.columns.map((col, i) => {
        fd.append(`cells[${i}][question_id]`, col.question_id);
        const cell = lr.cells[col.question_id] ?? {};
        if (semanticIsActor(col.semantic_tag)) {
          const tag = (col.semantic_tag || "").toLowerCase();
          // actor_id requerido
          const actorId = cell.actor?.id ?? "";
          if (!actorId) throw new Error(`Falta seleccionar ${tag} en la fila ${row_index}`);
          fd.append(`cells[${i}][actor_id]`, actorId);
        } else {
          fd.append(`cells[${i}][answer_text]`, (cell.text ?? "").trim());
        }
        return true;
      });

      const isNew = !!lr._isNew;
      const url = isNew
        ? `${apiBase}/submissions/${submissionId}/table-rows`
        : `${apiBase}/submissions/${submissionId}/table-rows/${row_index}`;
      const method = isNew ? "POST" : "PUT";

      const res = await fetch(url, {
        method,
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`Error ${res.status}: ${txt}`);
      }
      // refrescar filas
      const resR = await fetch(
        `${apiBase}/submissions/${submissionId}/table-rows`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const payload = await resR.json();
      setRows(payload?.rows ?? []);
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
      const res = await fetch(
        `${apiBase}/submissions/${submissionId}/table-rows/${row_index}`,
        { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok && res.status !== 204) throw new Error(`Error ${res.status}`);
      // Quitar localmente
      setRows((rs) => rs.filter((r) => r.row_index !== row_index));
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
                            token={token}
                            apiBase={apiBase}
                            actorFetcher={actorFetcher}
                          />
                        </td>
                      );
                    }

                    const val = r.values[cellKey];
                    return (
                      <td key={cellKey} className="border-t p-2 text-sm">
                        {semanticIsActor(c.semantic_tag)
                          ? val?.actor_id
                            ? <span className="inline-flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                                <code className="text-xs">{val.actor_id}</code>
                              </span>
                            : <span className="text-slate-400">—</span>
                          : (val?.answer_text ?? <span className="text-slate-400">—</span>)}
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
                          token={token}
                          apiBase={apiBase}
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
  token,
  apiBase,
  actorFetcher,
}: {
  column: Column;
  value?: { text?: string; actor?: { id: string; nombre: string } | null };
  onChange: (v: { text?: string; actor?: { id: string; nombre: string } | null }) => void;
  token: string;
  apiBase: string;
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

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="text"
        value={value?.nombre ?? q}
        onChange={(e) => {
          onChange(value ? null : null); // limpiar selección si escribe
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
