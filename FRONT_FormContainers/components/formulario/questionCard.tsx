"use client";
import { useCallback, useMemo, useState, useId, useEffect, useRef } from "react";
import { isImageOnly, isOcr, today, validateFiles } from "@/lib/ui";
import type { Item } from "@/types/form";

import ChoiceInput from "../inputs/choiceInput";
import TextInput from "../inputs/textInput";
import NumberInput from "../inputs/numberInput";
import DateInput from "../inputs/dateInput";
import FileInputOCR from "../inputs/fileInputOCR";
import FileInputMulti from "../inputs/fileInputMulti";
import ActorInput from "../inputs/actorInput";

type ActorLite = { id: string; nombre: string; documento?: string | null };

type ProviderRow = {
  nombre: string;
  estibas: number | null;
  orden_compra: string;
  recipientes: number | null;
  unidad: "KG" | "UN" | "";
};

type Props = {
  it: Item;
  idx: number;
  isLast: boolean;
  lastRef: React.RefObject<HTMLDivElement>;
  sending: boolean;

  setVal: (i: number, v: string) => void;
  onSelectChoice: (i: number, id: string) => void;
  onEnter: (e: React.KeyboardEvent, i: number) => void;
  onFilesChange: (i: number, files: FileList | null) => void;
  removeFile: (i: number, k: number) => void;
  submitOne: (i: number, valueOverride?: string, actorOverride?: ActorLite) => void;
  setItems: React.Dispatch<React.SetStateAction<Item[]>>;
  retryOCR: (i: number) => void;
  setActor?: (i: number, actor: ActorLite) => void;
  errorMsg?: string | null;
};

const tagOf = (q: any) => String(q?.semantic_tag || "none").toLowerCase();
const isActorTag = (t: string) => t === "proveedor" || t === "transportista" || t === "receptor";

const TIPO_BY_SLUG: Record<string, "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR"> = {
  proveedor: "PROVEEDOR",
  transportista: "TRANSPORTISTA",
  receptor: "RECEPTOR",
};

// helper: evita setState durante el render actual
const defer = (cb: () => void) => {
  if (typeof queueMicrotask === "function") queueMicrotask(cb);
  else setTimeout(cb, 0);
};

// lee param de URL (SSR-safe)
const getQueryParam = (name: string): string | null => {
  if (typeof window === "undefined") return null;
  try { return new URLSearchParams(window.location.search).get(name); } catch { return null; }
};

// ISO 6346
function isValidISO6346(code: string): boolean {
  const s = (code || "").toUpperCase();
  if (!/^[A-Z]{4}\d{7}$/.test(s)) return false;
  const values: Record<string, number> = {A:10,B:12,C:13,D:14,E:15,F:16,G:17,H:18,I:19,J:20,K:21,L:23,M:24,N:25,O:26,P:27,Q:28,R:29,S:30,T:31,U:32,V:34,W:35,X:36,Y:37,Z:38};
  const pref = s.slice(0,4), nums = s.slice(4);
  const digs: number[] = [values[pref[0]], values[pref[1]], values[pref[2]], values[pref[3]]];
  for (let i=0; i<6; i++) digs.push(parseInt(nums[i],10));
  const total = digs.reduce((acc, v, i) => acc + v * (2 ** i), 0);
  return (total % 11) % 10 === parseInt(nums[6], 10);
}

// proveedores JSON
function parseProviders(raw: string | undefined): ProviderRow[] {
  if (!raw) return [];
  try {
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return [];
    const out: ProviderRow[] = [];
    const seen = new Set<string>();
    for (const it of arr) {
      const nombre = String(it?.nombre || "").trim();
      if (!nombre) continue;
      const key = nombre.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      const unidadRaw = String(it?.unidad || "").toUpperCase();
      out.push({
        nombre,
        estibas: it?.estibas ?? null,
        orden_compra: String(it?.orden_compra || it?.oc || ""),
        recipientes: it?.recipientes ?? null,
        unidad: unidadRaw === "KG" ? "KG" : unidadRaw === "UN" ? "UN" : "",
      });
    }
    return out;
  } catch { return []; }
}

const SKIP_ENABLED_QN_ID = "75105aaa-4ec7-40e4-9334-9f08e89611ae";

// estilos de botón
const btnBase = "inline-flex items-center justify-center rounded-lg px-3.5 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-sky-400 disabled:opacity-60 disabled:cursor-not-allowed";
const btnPrimary = `${btnBase} bg-skyBlue text-white hover:bg-skyBlue/90 dark:hover:bg-skyBlue/80`;
const btnGhost = `${btnBase} border border-slate-200/70 dark:border-white/15 hover:bg-slate-50 dark:hover:bg-white/5 text-slate-700 dark:text-slate-200`;

export default function QuestionCard({
  it, idx, isLast, lastRef, sending,
  setVal, onSelectChoice, onEnter, onFilesChange, removeFile,
  submitOne, setItems, retryOCR, setActor, errorMsg,
}: Props) {
  const uid = useId();
  const q = it.q;

  // estado base
  const active = it.editing;
  const disabled = !active || sending;
  const busy = sending && active;

  // corrige corte de popovers: sin overflow hidden + z-index alto cuando activa
  const cardZ = active ? "z-30" : "z-10";

  const slug = useMemo(() => (q ? tagOf(q) : "none"), [q]);
  const isCatalog = useMemo(() => isActorTag(slug), [slug]);
  const isProveedor = slug === "proveedor";

  const [fileError, setFileError] = useState<string | null>(null);
  const fileErrorId = `file-error-${uid}`;
  const [showParentError, setShowParentError] = useState(Boolean(errorMsg));
  useEffect(() => setShowParentError(Boolean(errorMsg)), [errorMsg]);

  const [skipFirst, setSkipFirst] = useState(false);

  const questionnaireId: string = useMemo(() => {
    const a = (q as any)?.questionnaire_id;
    const b = (it as any)?.questionnaire_id;
    const c = (it as any)?.qnId;
    const d = getQueryParam("questionnaire_id") || getQueryParam("questionnaireId");
    return String(a || b || c || d || "");
  }, [q, it]);
  const canShowSkip = idx === 0 && questionnaireId.toLowerCase() === SKIP_ENABLED_QN_ID.toLowerCase();

  // archivos
  const onFilesChangeValidated = useCallback(
    (files: FileList | null) => {
      setFileError(null);
      if (files && files.length > 0) {
        const err = validateFiles(q, files);
        if (err) { setFileError(err); return; }
      }
      onFilesChange(idx, files);
    },
    [idx, onFilesChange, q]
  );

  // edición
  const openEditing = useCallback(() => {
    defer(() => {
      setItems((p) => {
        const c = [...p];
        c[idx] = { ...c[idx], editing: true };
        return c;
      });
    });
  }, [idx, setItems]);
  const closeEditing = useCallback(() => {
    defer(() => {
      setItems((p) => {
        const c = [...p];
        c[idx] = { ...c[idx], editing: false };
        return c;
      });
    });
  }, [idx, setItems]);
  const activateOnInteract = useCallback(() => {
    if (!active && !sending) openEditing();
    if (showParentError) setShowParentError(false);
  }, [active, sending, openEditing, showParentError]);

  // proveedores (multi)
  const [rows, setRows] = useState<ProviderRow[]>(
    () => (isProveedor ? parseProviders(String(it.value || "")) : [])
  );
  useEffect(() => {
    if (!isProveedor) return;
    setRows(parseProviders(String(it.value || "")));
  }, [it.value, isProveedor]);

  const addProveedorFromPick = useCallback((actor: ActorLite) => {
    if (setActor) defer(() => setActor(idx, actor));
    defer(() => {
      setItems((prev) => {
        const c = [...prev];
        c[idx] = { ...(c[idx] as any), actor, saved: false, editing: true, autoFromOCR: false, value: c[idx].value };
        return c;
      });
    });
    setRows((prev) => {
      if (prev.some(p => p.nombre.toLowerCase() === actor.nombre.toLowerCase())) return prev;
      const next = [...prev, { nombre: actor.nombre, estibas: null, orden_compra: "", recipientes: null, unidad: "" }];
      defer(() => setVal(idx, JSON.stringify(next)));
      return next;
    });
  }, [idx, setActor, setItems, setVal]);

  const updateRow = useCallback((i: number, patch: Partial<ProviderRow>) => {
    setRows((prev) => {
      const next = prev.map((r, k) => (k === i ? { ...r, ...patch } : r));
      defer(() => setVal(idx, JSON.stringify(next)));
      return next;
    });
  }, [idx, setVal]);

  const removeRow = useCallback((i: number) => {
    setRows((prev) => {
      const next = prev.filter((_, k) => i !== k);
      defer(() => setVal(idx, JSON.stringify(next)));
      return next;
    });
  }, [idx, setVal]);

  const validateRows = (list: ProviderRow[]) => {
    if (!list.length) return "Agrega al menos un proveedor.";
    for (const p of list) {
      if (!p.nombre) return "Falta el nombre del proveedor.";
      if (p.estibas == null || Number.isNaN(Number(p.estibas)) || Number(p.estibas) < 0) return `Estibas inválidas para ${p.nombre}.`;
      if (!p.orden_compra || !String(p.orden_compra).trim()) return `Orden de compra requerida para ${p.nombre}.`;
      if (p.recipientes == null || Number.isNaN(Number(p.recipientes)) || Number(p.recipientes) < 0) return `Recipientes inválidos para ${p.nombre}.`;
      if (p.unidad !== "KG" && p.unidad !== "UN") return `Selecciona unidad (Kg o Un) para ${p.nombre}.`;
    }
    return null;
  };

  const saveProveedorMulti = useCallback(() => {
    const err = validateRows(rows);
    if (err) { alert(err); return; }
    defer(() => submitOne(idx));
  }, [rows, submitOne, idx]);

  // actores (single)
  const handleActorSelectSingle = useCallback(
    (actor: ActorLite) => {
      if (setActor) defer(() => setActor(idx, actor));
      defer(() => {
        setItems((prev) => {
          const c = [...prev];
          c[idx] = { ...(c[idx] as any), value: actor.nombre, actor, saved: false, editing: true, autoFromOCR: false };
          return c;
        });
      });
      defer(() => submitOne(idx, undefined, actor));
    },
    [idx, setActor, setItems, submitOne]
  );

  // auto-avance OCR
  const autoSubmitGuard = useRef(false);
  useEffect(() => {
    if (!active || sending || !isOcr(q)) return;

    const hasFile = !!((it as any)?.files?.length);
    const autoFromOCR = !!(it as any)?.autoFromOCR;
    const valueFromOCR: string | undefined = (it as any)?.valueFromOCR;
    const sameAsOCR =
      typeof it.value === "string" && valueFromOCR && it.value === valueFromOCR;
    const valido = Boolean((it as any)?.ocr?.valido);

    const shouldAuto = hasFile && autoFromOCR && (valido || sameAsOCR);

    if (shouldAuto && !autoSubmitGuard.current) {
      autoSubmitGuard.current = true;
      defer(() => submitOne(idx));
    }
    if (!shouldAuto) autoSubmitGuard.current = false;
  }, [active, sending, idx, (it as any)?.ocr, (it as any)?.files, (it as any)?.autoFromOCR, (it as any)?.valueFromOCR, it.value, q, submitOne]);

  // Estado OCR (visual)
  const ocrStatusDisplay = useMemo(() => {
    const raw: any = (it as any)?.ocr;
    if (!raw) return undefined;
    if (typeof raw === "string") return raw;
    try {
      const chips: string[] = [];
      if (raw.placa) chips.push(`placa: ${raw.placa}`);
      if (raw.precinto) chips.push(`precinto: ${raw.precinto}`);
      if (raw.contenedor) chips.push(`contenedor: ${raw.contenedor}`);
      const meta = chips.join(" · ");
      const txt = (raw.ocr_raw as string) || (it.value as string) || "";
      return [txt, meta].filter(Boolean).join(" · ") || undefined;
    } catch { try { return JSON.stringify(raw); } catch { return String(raw); } }
  }, [it]);

  // Badge ISO 6346 (solo contenedor)
  const isoBadge = useMemo(() => {
    if (slug !== "contenedor") return null;
    const raw: any = (it as any)?.ocr;
    const current = (typeof it.value === "string" && it.value.trim()) ? String(it.value).toUpperCase() : "";
    const code = current || (raw && typeof raw !== "string" ? (raw.contenedor as string) : "");
    if (!code) return null;
    const ok = isValidISO6346(code);
    const base = "inline-flex items-center gap-2 rounded-lg px-3 py-1 text-sm font-medium border";
    const cls = ok
      ? `${base} border-emerald-500/30 text-emerald-700 bg-emerald-50 dark:bg-emerald-900/20 dark:text-emerald-300`
      : `${base} border-amber-500/30 text-amber-700 bg-amber-50 dark:bg-amber-900/20 dark:text-amber-300`;
    return (
      <div className="mt-2" aria-live="polite">
        <span className={cls}>
          <span aria-hidden className="text-base leading-none">{ok ? "✓" : "✗"}</span>
          <span className="whitespace-nowrap">{code} · {ok ? "ISO válida" : "ISO inválida"}</span>
        </span>
      </div>
    );
  }, [it, slug]);

  return (
    <section
      ref={isLast ? lastRef : null}
      aria-labelledby={`q-${q.id}-label`}
      aria-busy={busy}
      className={[
        "relative isolate",           // <-- importantísimo para stacking context correcto
        "rounded-2xl border bg-white dark:bg-slate-800 ring-1 ring-slate-200 dark:ring-white/10",
        "shadow-sm hover:shadow-md focus-within:shadow-md transition-shadow duration-200",
        "px-6 md:px-8 py-7 md:py-8 mb-6",
        "overflow-visible",           // <-- evita cortar dropdowns
        cardZ
      ].join(" ")}
      data-qid={q.id}
    >
      {busy && (
        <div
          className="absolute inset-0 grid place-items-center bg-white/40 dark:bg-slate-900/30 backdrop-blur-[1px] rounded-2xl z-50"
          role="status"
          aria-live="polite"
        >
          <div className="animate-spin h-6 w-6 rounded-full border-2 border-slate-400 border-t-transparent" />
        </div>
      )}

      <div className="relative flex items-start gap-5 md:gap-6">
        {/* Número */}
        <div
          className={[
            "h-11 w-11 md:h-12 md:w-12 shrink-0 rounded-full grid place-items-center text-white font-semibold shadow-md transition-colors duration-200",
            active ? "bg-skyBlue" : "bg-slate-400"
          ].join(" ")}
          aria-hidden="true"
        >
          <span className="text-base md:text-lg">{idx + 1}</span>
        </div>

        <div className="flex-1 min-w-0">
          <header className="flex items-start justify-between gap-4">
            <h3 id={`q-${q.id}-label`} className="text-xl md:text-2xl font-semibold leading-snug text-slate-900 dark:text-white">
              {q.text}
              {q.required && (
                <span className="ml-2 align-middle text-red-500 text-sm" title="Respuesta obligatoria" aria-label="Respuesta obligatoria">*</span>
              )}
            </h3>
            {it.saved && !it.editing && (
              <span className="inline-flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
                <span aria-hidden>✓</span> Guardada
              </span>
            )}
          </header>

          {/* Error del padre */}
          {errorMsg && showParentError && active && (
            <div className="mt-3 mb-4 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 flex items-start gap-2" role="alert" aria-live="assertive">
              <span className="mt-0.5">⚠️</span>
              <div className="flex-1">{errorMsg}</div>
              <button type="button" onClick={() => setShowParentError(false)} className="ml-2 px-2 py-1 rounded hover:bg-amber-100 text-amber-900" aria-label="Ocultar mensaje de error">✕</button>
            </div>
          )}

          {/* === ACTOR === */}
          {isCatalog && (
            <div onClickCapture={activateOnInteract} onFocusCapture={activateOnInteract} className="space-y-4">
              {isProveedor ? (
                <>
                  <div className="relative z-40"> {/* eleva el dropdown del autocompletar */}
                    <ActorInput
                      tipo={TIPO_BY_SLUG[slug]}
                      defaultValue=""
                      disabled={sending}
                      onSelect={addProveedorFromPick}
                      multiple
                      selectFirstOnEnter
                    />
                  </div>

                  <div className="mt-1 space-y-3">
                    {rows.length === 0 && (
                      <div className="px-3 py-2 text-sm text-gray-500 border rounded-lg bg-gray-50/50 dark:bg-white/5">
                        Sin proveedores. Busca y selecciona uno arriba.
                      </div>
                    )}
                    {rows.map((row, i) => (
                      <div key={`${row.nombre}-${i}`} className="border rounded-xl p-3 md:p-4 bg-white/60 dark:bg-slate-900/30">
                        <div className="flex items-center justify-between mb-3">
                          <div className="font-medium text-slate-800 dark:text-slate-100 truncate">{row.nombre}</div>
                          <button type="button" onClick={() => removeRow(i)} className={`${btnGhost} !px-2 !py-1 text-xs`} aria-label={`Eliminar ${row.nombre}`}>
                            Eliminar
                          </button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                          <div>
                            <label className="block text-xs text-slate-500 mb-1">Orden de compra</label>
                            <input
                              type="text"
                              value={row.orden_compra}
                              onChange={(e) => updateRow(i, { orden_compra: e.target.value })}
                              className="w-full rounded-md border px-3 py-2 outline-none focus:ring ring-sky-300/60 bg-white dark:bg-slate-900"
                              placeholder="OC-0001"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-slate-500 mb-1">Número de estibas</label>
                            <input
                              type="number" min={0}
                              value={row.estibas ?? ""}
                              onChange={(e) => updateRow(i, { estibas: e.target.value === "" ? null : Number(e.target.value) })}
                              className="w-full rounded-md border px-3 py-2 outline-none focus:ring ring-sky-300/60 bg-white dark:bg-slate-900"
                              placeholder="0"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-slate-500 mb-1">Número de recipientes</label>
                            <input
                              type="number" min={0}
                              value={row.recipientes ?? ""}
                              onChange={(e) => updateRow(i, { recipientes: e.target.value === "" ? null : Number(e.target.value) })}
                              className="w-full rounded-md border px-3 py-2 outline-none focus:ring ring-sky-300/60 bg-white dark:bg-slate-900"
                              placeholder="0"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-slate-500 mb-1">Unidad de medida</label>
                            <select
                              value={row.unidad}
                              onChange={(e) => updateRow(i, { unidad: (e.target.value as "KG" | "UN" | "") })}
                              className="w-full rounded-md border px-3 py-2 outline-none focus:ring ring-sky-300/60 bg-white dark:bg-slate-900"
                            >
                              <option value="">Seleccione…</option>
                              <option value="KG">Kg</option>
                              <option value="UN">Un</option>
                            </select>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center gap-3">
                    <button type="button" onClick={saveProveedorMulti} disabled={sending || !active || rows.length === 0} className={btnPrimary}>
                      Guardar y continuar
                    </button>
                    {rows.length > 0 && (
                      <span className="text-sm text-slate-500">{rows.length} proveedor{rows.length > 1 ? "es" : ""}</span>
                    )}
                  </div>
                </>
              ) : (
                <div className="relative z-40">
                  <ActorInput
                    tipo={TIPO_BY_SLUG[slug]}
                    defaultValue={(it as any)?.actor?.nombre || it.value || ""}
                    disabled={sending}
                    onSelect={handleActorSelectSingle}
                  />
                </div>
              )}
            </div>
          )}

          {/* Inputs por tipo (no-actor) */}
          {!isCatalog && q.type === "choice" && (
            <div onClickCapture={activateOnInteract} onFocusCapture={activateOnInteract}>
              <ChoiceInput
                choices={q.choices}
                value={it.value}
                disabled={disabled}
                onSelect={(id) => onSelectChoice(idx, id)}
                name={`q-${q.id}`}
              />
            </div>
          )}

          {!isCatalog && q.type === "text" && (
            <TextInput
              value={it.value}
              disabled={disabled}
              onChange={(v) => { if (showParentError) setShowParentError(false); defer(() => setVal(idx, v)); }}
              onBlur={() => defer(() => submitOne(idx))}
              onEnter={(e) => onEnter(e, idx)}
            />
          )}

          {!isCatalog && q.type === "number" && (
            <NumberInput
              value={it.value}
              disabled={disabled}
              onChange={(v) => { if (showParentError) setShowParentError(false); defer(() => setVal(idx, v)); }}
              onBlur={() => defer(() => submitOne(idx))}
              onEnter={(e) => onEnter(e, idx)}
            />
          )}

          {!isCatalog && q.type === "date" && (
            <DateInput
              value={it.value || today()}
              disabled={disabled}
              onChange={(v) => { if (showParentError) setShowParentError(false); defer(() => setVal(idx, v)); }}
              onCommit={() => defer(() => submitOne(idx, it.value || today()))}
            />
          )}

          {/* FILE + OCR */}
          {!isCatalog && q.type === "file" && isOcr(q) && (
            <>
              <FileInputOCR
                active={active && !sending}
                previews={it.previews}
                value={it.value}
                ocrStatus={ocrStatusDisplay}
                sending={sending}
                onFilesChange={onFilesChangeValidated}
                onChangeText={(v) => { if (showParentError) setShowParentError(false); defer(() => setVal(idx, v)); }}
                onSubmit={() => defer(() => submitOne(idx))}
                onRetryOCR={() => retryOCR(idx)}
                aria-describedby={fileError ? fileErrorId : undefined}
              />

              {tagOf(q) === "placa" && (
                <>
                  <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                    Puedes <strong>escribir la placa manualmente</strong> o subir una imagen para OCR. La imagen no es obligatoria.
                  </p>
                  <div className="mt-3">
                    <button type="button" onClick={() => defer(() => submitOne(idx))} disabled={sending || !String(it.value || "").trim()} className={btnPrimary}>
                      Continuar con texto
                    </button>
                  </div>
                </>
              )}
            </>
          )}

          {!isCatalog && q.type === "file" && isImageOnly(q) && (
            <>
              <FileInputMulti
                active={active && !sending}
                previews={it.previews}
                sending={sending}
                onFilesChange={onFilesChangeValidated}
                onRemove={(k) => removeFile(idx, k)}
                onSubmit={() => defer(() => submitOne(idx))}
                aria-describedby={fileError ? fileErrorId : undefined}
              />
              {fileError && (
                <p id={fileErrorId} className="mt-2 text-sm text-red-600 dark:text-red-400" role="alert" aria-live="assertive">
                  {fileError}
                </p>
              )}
            </>
          )}

          {/* Omitir (solo QN permitido) */}
          {canShowSkip && (
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <label className="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-slate-300 text-skyBlue focus:ring-sky-300"
                  checked={skipFirst}
                  onChange={(e) => {
                    const on = e.target.checked;
                    setSkipFirst(on);
                    if (on) defer(() => setVal(idx, "0"));
                  }}
                />
                <span>Omitir esta pregunta (registrar 0)</span>
              </label>

              <button
                type="button"
                onClick={() => { defer(() => setVal(idx, "0")); defer(() => submitOne(idx, "0")); }}
                className={btnGhost}
              >
                Omitir y continuar
              </button>
            </div>
          )}

          {/* Acciones */}
          <div className="mt-6 flex flex-wrap items-center gap-3 md:gap-4">
            {it.saved && it.editing && !isCatalog && (
              <button type="button" className="text-sm text-skyBlue underline underline-offset-4 hover:text-skyBlue/80 transition" onClick={() => defer(() => submitOne(idx))} disabled={sending}>
                Guardar cambios
              </button>
            )}
            {!it.editing && (
              <button type="button" className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition" onClick={closeEditing} disabled={sending}>
                Cerrar
              </button>
            )}
          </div>

          {isoBadge}
        </div>
      </div>

      {/* Overrides dark-mode de popovers/listboxes */}
      <style jsx global>{`
        .dark [role="listbox"] {
          background-color: rgb(15 23 42) !important;
          color: rgb(226 232 240) !important;
          border: 1px solid rgba(148, 163, 184, 0.35) !important;
        }
        .dark [role="option"] { color: rgb(226 232 240) !important; opacity: 1 !important; }
        .dark [role="option"][aria-selected="true"], .dark [role="option"]:hover {
          background-color: rgba(56, 189, 248, 0.18) !important;
          color: rgb(248 250 252) !important;
        }
        .dark [role="option"][aria-disabled="true"] { color: rgb(148 163 184) !important; opacity: 0.7 !important; }
        .dark input[list] {
          color-scheme: dark;
          color: rgb(226 232 240);
          background-color: rgb(2 6 23);
          border-color: rgba(148,163,184,.5);
        }
      `}</style>
    </section>
  );
}
