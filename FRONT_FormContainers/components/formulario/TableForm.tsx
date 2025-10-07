import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

/**
 * TableForm
 * Modo tabla para una Submission.
 * - Lee el layout del cuestionario (columnas)
 * - Lista/crea/actualiza/elimina filas
 * - Emite/escucha eventos para añadir filas desde fuera ("phase0:addRow")
 *
 * IMPORTANTE:
 * - Todos los endpoints incluyen "/" final para evitar 301 y pérdidas de cabecera.
 * - apiBase DEBE ser el mismo usado en el wrapper de API (ej. "/api").
 */

type Column = {
  question_id: string;
  header: string;
  width?: number | null;
  order: number;
  semantic_tag?: string | null; // proveedor | transportista | receptor | placa | precinto | contenedor | ...
  ui_hint?: string | null;      // text | date | time | number | phone | file | ...
};

type GridDef = {
  questionnaire_id: string;
  title?: string;
  version?: string;
  timezone?: string;
  columns: Column[];
};

type Row = {
  row_index: number;
  values: Record<string, any>; // key = question_id -> normalizado por backend
};

type Props = {
  questionnaireId: string;
  submissionId: string;
  token: string | null;
  apiBase?: string; // "/api"
};

function ensureSlash(url: string) {
  return url.endsWith("/") ? url : url + "/";
}

function joinUrl(base: string, path: string) {
  const b = base.endsWith("/") ? base.slice(0, -1) : base;
  const p = path.startsWith("/") ? path : "/" + path;
  // limpiamos dobles
  const full = (b + p).replace(/\/{2,}/g, "/");
  return ensureSlash(full);
}

const DEFAULT_COL_WIDTH = 200;

const TableForm: React.FC<Props> = ({ questionnaireId, submissionId, token, apiBase = "/api" }) => {
  const [grid, setGrid] = useState<GridDef | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const authHeaders = useMemo<HeadersInit>(() => {
    const h: any = { "Accept": "application/json" };
    if (token) h["Authorization"] = `Bearer ${token}`;
    return h;
  }, [token]);

  const authJsonHeaders = useMemo<HeadersInit>(() => {
    const h: any = { "Accept": "application/json", "Content-Type": "application/json" };
    if (token) h["Authorization"] = `Bearer ${token}`;
    return h;
  }, [token]);

  const columns = grid?.columns ?? [];

  const colById = useMemo(() => {
    const m = new Map<string, Column>();
    columns.forEach(c => m.set(String(c.question_id), c));
    return m;
  }, [columns]);

  // Carga layout (robusta: intenta /grids y luego /grid)
  useEffect(() => {
    let cancel = false;
    async function loadLayout() {
      try {
        setError(null);
        const url1 = joinUrl(apiBase, `cuestionarios/${questionnaireId}/grids`);
        let resp = await fetch(url1, { headers: authHeaders, credentials: "include", cache: "no-store", redirect: "follow" });
        if (resp.ok) {
          const data = await resp.json();
          if (!cancel) {
            const gs = Array.isArray(data?.grids) ? data.grids : [];
            const g0 = gs.find((g: any) => Array.isArray(g?.columns) && g.columns.length > 0)
                     || (Array.isArray(data?.columns) ? { columns: data.columns } : null)
                     || data?.grid;
            if (g0 && Array.isArray(g0.columns)) {
              setGrid({
                questionnaire_id: String(data?.questionnaire_id || questionnaireId),
                title: data?.title || g0?.title || "Grid",
                version: data?.version,
                timezone: data?.timezone,
                columns: g0.columns.map((c: any, idx: number) => ({
                  question_id: String(c.question_id || c.id),
                  header: String(c.header || c.title || c.name || `Col ${idx+1}`),
                  order: Number(c.order ?? idx),
                  width: c.width ?? null,
                  semantic_tag: c.semantic_tag ?? null,
                  ui_hint: c.ui_hint ?? (c.type === "file" ? "file" : "text"),
                })),
              });
              return;
            }
          }
        }
        // fallback /grid
        const url2 = joinUrl(apiBase, `cuestionarios/${questionnaireId}/grid`);
        resp = await fetch(url2, { headers: authHeaders, credentials: "include", cache: "no-store", redirect: "follow" });
        if (resp.ok) {
          const data = await resp.json();
          if (!cancel && Array.isArray(data?.columns)) {
            setGrid({
              questionnaire_id: String(data?.questionnaire_id || questionnaireId),
              title: data?.title || "Grid",
              version: data?.version,
              timezone: data?.timezone,
              columns: data.columns.map((c: any, idx: number) => ({
                question_id: String(c.question_id || c.id),
                header: String(c.header || c.title || c.name || `Col ${idx+1}`),
                order: Number(c.order ?? idx),
                width: c.width ?? null,
                semantic_tag: c.semantic_tag ?? null,
                ui_hint: c.ui_hint ?? (c.type === "file" ? "file" : "text"),
              })),
            });
          }
        } else if (!cancel) {
          setError(`No se pudo cargar layout (${resp.status}).`);
        }
      } catch (e: any) {
        if (!cancel) setError(e?.message || "Error cargando layout.");
      }
    }
    loadLayout();
    return () => { cancel = true; };
  }, [apiBase, questionnaireId, authHeaders]);

  // Carga filas
  useEffect(() => {
    let cancel = false;
    async function loadRows() {
      try {
        setLoading(true);
        const url = joinUrl(apiBase, `submissions/${submissionId}/table-rows`) + `?as_table=1`;
        const resp = await fetch(url, { headers: authHeaders, credentials: "include", cache: "no-store", redirect: "follow" });
        if (!resp.ok) throw new Error(`No se pudo cargar filas (${resp.status}).`);
        const data = await resp.json();
        if (!cancel) {
          const rs: Row[] = Array.isArray(data?.rows) ? data.rows.map((r: any) => ({
            row_index: Number(r.row_index),
            values: r.values || {},
          })) : [];
          // ordenar por row_index asc
          rs.sort((a, b) => a.row_index - b.row_index);
          setRows(rs);
        }
      } catch (e: any) {
        if (!cancel) setError(e?.message || "Error cargando filas.");
      } finally {
        if (!cancel) setLoading(false);
      }
    }
    if (submissionId) loadRows();
    return () => { cancel = true; };
  }, [apiBase, submissionId, authHeaders]);

  // Listener para "Nueva fila" desde index.tsx
  useEffect(() => {
    const handler = () => addRow();
    window.addEventListener("phase0:addRow", handler as any);
    return () => { window.removeEventListener("phase0:addRow", handler as any); };
  }, []); // eslint-disable-line

  const addRow = useCallback(async () => {
    try {
      setSaving(true);
      const url = joinUrl(apiBase, `submissions/${submissionId}/table-rows`);
      const resp = await fetch(url, {
        method: "POST",
        headers: authJsonHeaders,
        credentials: "include",
        body: JSON.stringify({ cells: [] }),
      });
      if (!resp.ok) throw new Error(`No se pudo crear la fila (${resp.status}).`);
      const data = await resp.json();
      const newRow: Row = {
        row_index: Number(data?.row_index),
        values: data?.values || {},
      };
      setRows(prev => {
        const copy = [...prev, newRow];
        copy.sort((a, b) => a.row_index - b.row_index);
        return copy;
      });
    } catch (e: any) {
      setError(e?.message || "Error creando fila.");
    } finally {
      setSaving(false);
    }
  }, [apiBase, submissionId, authJsonHeaders]);

  const deleteRow = useCallback(async (row_index: number) => {
    if (!confirm(`¿Eliminar la fila ${row_index}?`)) return;
    try {
      setSaving(true);
      const url = joinUrl(apiBase, `submissions/${submissionId}/table-rows/${row_index}`);
      const resp = await fetch(url, { method: "DELETE", headers: authHeaders, credentials: "include" });
      if (!resp.ok && resp.status !== 204) throw new Error(`No se pudo eliminar la fila (${resp.status}).`);
      setRows(prev => prev.filter(r => r.row_index !== row_index));
    } catch (e: any) {
      setError(e?.message || "Error eliminando fila.");
    } finally {
      setSaving(false);
    }
  }, [apiBase, submissionId, authHeaders]);

  // Helpers para obtener/mostrar el valor de una celda
  const getCellValueDisplay = (r: Row, qid: string): string => {
    const v = r.values?.[qid];
    if (v == null) return "";
    if (typeof v === "string" || typeof v === "number") return String(v);
    // objetos: preferir 'text' o 'display' o 'value'
    return v.text ?? v.display ?? v.value ?? v.answer_text ?? v.actor_name ?? "";
  };

  const setLocalCell = (row_index: number, qid: string, value: any) => {
    setRows(prev => prev.map(r => {
      if (r.row_index !== row_index) return r;
      return { ...r, values: { ...r.values, [qid]: value } };
    }));
  };

  // PATCH celda (texto / choice)
  const patchCell = useCallback(async (row_index: number, qid: string, value: string) => {
    try {
      setSaving(true);
      const url = joinUrl(apiBase, `submissions/${submissionId}/table-rows/${row_index}`);
      const payload = { cells: [{ question_id: qid, answer_text: value }] };
      const resp = await fetch(url, {
        method: "PATCH",
        headers: authJsonHeaders,
        credentials: "include",
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error(`No se pudo guardar (${resp.status}).`);
      const data = await resp.json();
      // servidor devuelve fila normalizada
      const values = data?.values || {};
      setRows(prev => prev.map(r => (r.row_index === row_index ? { ...r, values } : r)));
    } catch (e: any) {
      setError(e?.message || "Error guardando celda.");
    } finally {
      setSaving(false);
    }
  }, [apiBase, submissionId, authJsonHeaders]);

  // PATCH archivo
  const uploadCellFile = useCallback(async (row_index: number, qid: string, file: File) => {
    try {
      setSaving(true);
      const url = joinUrl(apiBase, `submissions/${submissionId}/table-rows/${row_index}`);
      const fd = new FormData();
      fd.append("cells[0][question_id]", qid);
      fd.append("cells[0][file]", file);
      const headers: HeadersInit = { ...authHeaders };
      // NO pongas Content-Type: el browser arma el boundary
      const resp = await fetch(url, { method: "PATCH", headers, credentials: "include", body: fd });
      if (!resp.ok) throw new Error(`No se pudo subir el archivo (${resp.status}).`);
      const data = await resp.json();
      const values = data?.values || {};
      setRows(prev => prev.map(r => (r.row_index === row_index ? { ...r, values } : r)));
    } catch (e: any) {
      setError(e?.message || "Error subiendo archivo.");
    } finally {
      setSaving(false);
    }
  }, [apiBase, submissionId, authHeaders]);

  // Debounce para inputs
  const typingTimers = useRef<Record<string, any>>({}); // key `${row_index}:${qid}`

  const handleChange = (row_index: number, qid: string, val: string) => {
    setLocalCell(row_index, qid, { text: val });
    const key = `${row_index}:${qid}`;
    if (typingTimers.current[key]) {
      clearTimeout(typingTimers.current[key]);
    }
    typingTimers.current[key] = setTimeout(() => {
      patchCell(row_index, qid, val);
      delete typingTimers.current[key];
    }, 500);
  };

  const handleFile = (row_index: number, qid: string, file?: File | null) => {
    if (!file) return;
    uploadCellFile(row_index, qid, file);
  };

  // Render
  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-6 text-slate-500">
        Cargando tabla...
      </div>
    );
  }
  if (error) {
    return (
      <div className="rounded-xl border border-amber-300 bg-amber-50 dark:bg-amber-400/10 p-4 text-amber-800 dark:text-amber-100">
        {error}
      </div>
    );
  }
  if (!grid || columns.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-6 text-slate-500">
        No hay definición de columnas para este cuestionario.
      </div>
    );
  }

  return (
    <div className="w-full overflow-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
      <table className="min-w-full border-collapse">
        <thead className="sticky top-0 z-10 bg-slate-50 dark:bg-slate-800">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700 w-20">
              Fila
            </th>
            {columns.sort((a,b)=>a.order-b.order).map((col) => (
              <th
                key={col.question_id}
                style={{ width: (col.width ?? DEFAULT_COL_WIDTH) + "px" }}
                className="px-3 py-2 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700"
                title={col.header}
              >
                {col.header}
              </th>
            ))}
            <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700 w-16">
              Acciones
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`r-${r.row_index}`} className="even:bg-slate-50/50 dark:even:bg-slate-800/30">
              <td className="px-3 py-2 text-sm text-slate-500 dark:text-slate-300 border-b border-slate-100 dark:border-slate-800">
                {r.row_index}
              </td>
              {columns.sort((a,b)=>a.order-b.order).map(col => {
                const qid = String(col.question_id);
                const val = getCellValueDisplay(r, qid);
                const isFile = (col.ui_hint || "").toLowerCase() === "file";
                return (
                  <td key={`c-${r.row_index}-${qid}`} className="px-2 py-1 border-b border-slate-100 dark:border-slate-800">
                    {!isFile ? (
                      <input
                        type={(col.ui_hint || "text") === "number" ? "number" : "text"}
                        value={val}
                        onChange={(e) => handleChange(r.row_index, qid, e.target.value)}
                        className="w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder={col.header}
                      />
                    ) : (
                      <label className="flex items-center gap-2 text-sm text-indigo-600 hover:underline cursor-pointer">
                        <input type="file" className="hidden" onChange={(e) => handleFile(r.row_index, qid, e.target.files?.[0])} />
                        Subir archivo
                      </label>
                    )}
                  </td>
                );
              })}
              <td className="px-2 py-1 border-b border-slate-100 dark:border-slate-800 text-right">
                <button
                  onClick={() => deleteRow(r.row_index)}
                  className="rounded-md px-2 py-1 text-xs bg-rose-600 text-white hover:bg-rose-700"
                  disabled={saving}
                >
                  Eliminar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* footer */}
      <div className="flex items-center justify-between p-3">
        <div className="text-xs text-slate-500 dark:text-slate-400">
          {rows.length} filas · {columns.length} columnas {saving ? "· guardando..." : ""}
        </div>
        <button
          onClick={() => addRow()}
          className="rounded-md bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-3 py-2"
          disabled={saving}
        >
          Nueva fila
        </button>
      </div>
    </div>
  );
};

export default TableForm;
