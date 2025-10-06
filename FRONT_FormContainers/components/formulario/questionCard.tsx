"use client";
import { useCallback, useMemo, useState, useId, useEffect, useRef } from "react";
import { CARD, isImageOnly, isOcr, today, validateFiles } from "@/lib/ui";
import type { Item } from "@/types/form";

import ChoiceInput from "../inputs/choiceInput";
import TextInput from "../inputs/textInput";
import NumberInput from "../inputs/numberInput";
import DateInput from "../inputs/dateInput";
import FileInputOCR from "../inputs/fileInputOCR";
import FileInputMulti from "../inputs/fileInputMulti";
import ActorInput from "../inputs/actorInput";

type ActorLite = { id: string; nombre: string; documento?: string | null };

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

// === Validación ISO 6346 (igual que backend) ===
function isValidISO6346(code: string): boolean {
  const s = (code || "").toUpperCase();
  if (!/^[A-Z]{4}\d{7}$/.test(s)) return false;

  const values: Record<string, number> = {
    A:10,B:12,C:13,D:14,E:15,F:16,G:17,H:18,I:19,J:20,K:21,L:23,M:24,N:25,O:26,P:27,
    Q:28,R:29,S:30,T:31,U:32,V:34,W:35,X:36,Y:37,Z:38
  };
  const pref = s.slice(0,4);
  const nums = s.slice(4);
  const digs: number[] = [];
  for (let i=0; i<3; i++) digs.push(values[pref[i]]);
  digs.push(values[pref[3]]);
  for (let i=0; i<6; i++) digs.push(parseInt(nums[i],10));

  const weights = digs.map((_, i) => 2 ** i);
  const total = digs.reduce((acc, v, i) => acc + v * weights[i], 0);
  const check = (total % 11) % 10;
  return check === parseInt(nums[6], 10);
}

export default function QuestionCard({
  it, idx, isLast, lastRef, sending,
  setVal, onSelectChoice, onEnter, onFilesChange, removeFile,
  submitOne, setItems, retryOCR, setActor, errorMsg,
}: Props) {
  const uid = useId();
  const q = it.q;

  // Básicos
  const active = it.editing;
  const disabled = !active || sending;
  const busy = sending && active;

  const slug = useMemo(() => (q ? tagOf(q) : "none"), [q]);
  const isCatalog = useMemo(() => isActorTag(slug), [slug]);

  const sectionClass = useMemo(
    () =>
      `${CARD} relative p-7 md:p-9 mb-5 md:mb-6 transition-shadow duration-200 ${
        active ? "ring-2 ring-skyBlue/60 shadow-xl" : "shadow"
      }`,
    [active]
  );

  const [fileError, setFileError] = useState<string | null>(null);
  const fileErrorId = `file-error-${uid}`;

  // Error del padre con dismiss local (no afecta al estado global)
  const [showParentError, setShowParentError] = useState<boolean>(Boolean(errorMsg));
  useEffect(() => setShowParentError(Boolean(errorMsg)), [errorMsg]);

  // Omitir primera
  const [skipFirst, setSkipFirst] = useState(false);

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

  const openEditing = useCallback(() => {
    setItems((p) => {
      const c = [...p];
      c[idx] = { ...c[idx], editing: true };
      return c;
    });
  }, [idx, setItems]);

  const closeEditing = useCallback(() => {
    setItems((p) => {
      const c = [...p];
      c[idx] = { ...c[idx], editing: false };
      return c;
    });
  }, [idx, setItems]);

  // Activa edición al interactuar + oculta el error del padre
  const activateOnInteract = useCallback(() => {
    if (!active && !sending) openEditing();
    if (showParentError) setShowParentError(false);
  }, [active, sending, openEditing, showParentError]);

  // Catálogo → persistir y enviar
  const handleActorSelect = useCallback(
    (actor: ActorLite) => {
      setActor?.(idx, actor);
      setItems((prev) => {
        const c = [...prev];
        c[idx] = { ...(c[idx] as any), value: actor.nombre, actor, saved: false, editing: true, autoFromOCR: false };
        return c;
      });
      submitOne(idx, undefined, actor);
    },
    [idx, setItems, submitOne, setActor]
  );

  // Auto-avance OCR sólo si hubo archivo y el texto vino del OCR
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
      submitOne(idx);
    }
    if (!shouldAuto) autoSubmitGuard.current = false;
  }, [
    active,
    sending,
    idx,
    (it as any)?.ocr,
    (it as any)?.files,
    (it as any)?.autoFromOCR,
    (it as any)?.valueFromOCR,
    it.value,
    q,
    submitOne,
  ]);

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
    } catch {
      try { return JSON.stringify(raw); } catch { return String(raw); }
    }
  }, [it]);

  // Badge ISO 6346 (solo para contenedor)
  const isoBadge = useMemo(() => {
    if (slug !== "contenedor") return null;

    const raw: any = (it as any)?.ocr;
    const current = (typeof it.value === "string" && it.value.trim()) ? String(it.value).toUpperCase() : "";
    const code = current || (raw && typeof raw !== "string" ? (raw.contenedor as string) : "");

    if (!code) return null;

    const ok = isValidISO6346(code);
    const baseCls = "inline-flex items-center gap-2 rounded-lg px-3 py-1 text-sm font-medium border";
    const cls = ok
      ? `${baseCls} border-emerald-500/30 text-emerald-700 bg-emerald-50 dark:bg-emerald-900/20 dark:text-emerald-300`
      : `${baseCls} border-amber-500/30 text-amber-700 bg-amber-50 dark:bg-amber-900/20 dark:text-amber-300`;

    return (
      <div className="mt-2" aria-live="polite">
        <span className={cls}>
          <span aria-hidden="true" className="text-base leading-none">{ok ? "✓" : "✗"}</span>
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
      className={`group rounded-2xl border bg-white dark:bg-slate-800 transition-all duration-200 shadow-sm hover:shadow-md focus-within:shadow-md px-6 md:px-8 py-7 md:py-8 mb-6 ring-1 ring-slate-200 dark:ring-white/10 ${active ? "ring-2 ring-skyBlue/60 shadow-xl" : ""} relative`}
      data-qid={q.id}
    >
      {/* Overlay de carga no intrusivo */}
      {busy && (
        <div
          className="absolute inset-0 grid place-items-center bg-white/40 dark:bg-slate-900/30 backdrop-blur-[1px] rounded-2xl z-10"
          role="status"
          aria-live="polite"
        >
          <div className="animate-spin h-6 w-6 rounded-full border-2 border-slate-400 border-t-transparent" />
        </div>
      )}

      <div className="flex items-start gap-5 md:gap-6">
        <div
          className={`h-11 w-11 md:h-12 md:w-12 shrink-0 rounded-full grid place-items-center text-white font-semibold shadow-md transition-colors duration-200 ${active ? "bg-skyBlue" : "bg-slate-400"}`}
          aria-hidden="true"
        >
          <span className="text-base md:text-lg">{idx + 1}</span>
        </div>

        <div className="flex-1">
          <h3
            id={`q-${q.id}-label`}
            className="text-xl md:text-2xl font-semibold leading-snug text-slate-900 dark:text-white mb-3 md:mb-4"
          >
            {q.text}
            {q.required ? (
              <span className="ml-2 inline-flex items-center gap-1 text-red-500 text-sm align-middle" title="Respuesta obligatoria" aria-label="Respuesta obligatoria">
                *
              </span>
            ) : null}
          </h3>

          {/* Alerta de error del padre (con dismiss local) */}
          {errorMsg && showParentError && active && (
            <div
              className="mb-3 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 flex items-start gap-2"
              role="alert"
              aria-live="assertive"
            >
              <span className="mt-0.5">⚠️</span>
              <div className="flex-1">{errorMsg}</div>
              <button
                type="button"
                onClick={() => setShowParentError(false)}
                className="ml-2 px-2 py-1 rounded hover:bg-amber-100 text-amber-900"
                aria-label="Ocultar mensaje de error"
              >
                ✕
              </button>
            </div>
          )}

          {/* Catálogo (actor) */}
          {isCatalog && (
            <div onClickCapture={activateOnInteract} onFocusCapture={activateOnInteract}>
              <ActorInput
                tipo={TIPO_BY_SLUG[slug]}
                defaultValue={(it as any)?.actor?.nombre || it.value || ""}
                disabled={sending}
                onSelect={handleActorSelect}
              />
            </div>
          )}

          {/* Inputs por tipo */}
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
              onChange={(v) => { if (showParentError) setShowParentError(false); setVal(idx, v); }}
              onBlur={() => submitOne(idx)}
              onEnter={(e) => onEnter(e, idx)}
            />
          )}

          {!isCatalog && q.type === "number" && (
            <NumberInput
              value={it.value}
              disabled={disabled}
              onChange={(v) => { if (showParentError) setShowParentError(false); setVal(idx, v); }}
              onBlur={() => submitOne(idx)}
              onEnter={(e) => onEnter(e, idx)}
            />
          )}

          {!isCatalog && q.type === "date" && (
            <DateInput
              value={it.value || today()}
              disabled={disabled}
              onChange={(v) => { if (showParentError) setShowParentError(false); setVal(idx, v); }}
              onCommit={() => submitOne(idx, it.value || today())}
            />
          )}

          {!isCatalog && q.type === "file" && isOcr(q) && (
            <>
              <FileInputOCR
                active={active && !sending}
                previews={it.previews}
                value={it.value}
                ocrStatus={ocrStatusDisplay}
                sending={sending}
                onFilesChange={onFilesChangeValidated}
                onChangeText={(v) => { if (showParentError) setShowParentError(false); setVal(idx, v); }}
                onSubmit={() => submitOne(idx)}
                onRetryOCR={() => retryOCR(idx)}
                aria-describedby={fileError ? fileErrorId : undefined}
              />

              {isoBadge}

              {slug === "placa" && (
                <>
                  <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                    Puedes <strong>escribir la placa manualmente</strong> o subir una imagen para OCR. La imagen no es obligatoria.
                  </p>
                  <div className="mt-3">
                    <button
                      type="button"
                      onClick={() => submitOne(idx)}
                      disabled={sending || !String(it.value || "").trim()}
                      className="px-3 py-2 rounded-lg bg-skyBlue text-white disabled:opacity-60"
                    >
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
                onSubmit={() => submitOne(idx)}
                aria-describedby={fileError ? fileErrorId : undefined}
              />
              {fileError && (
                <p id={fileErrorId} className="mt-2 text-sm text-red-600 dark:text-red-400" role="alert" aria-live="assertive">
                  {fileError}
                </p>
              )}
            </>
          )}

          {/* Omitir solo la PRIMERA pregunta */}
          {idx === 0 && (
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <label className="inline-flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  className="h-4 w-4"
                  checked={skipFirst}
                  onChange={(e) => {
                    const on = e.target.checked;
                    setSkipFirst(on);
                    if (on) setVal(idx, "0");
                  }}
                />
                <span>Omitir esta pregunta (registrar 0)</span>
              </label>

              <button
                type="button"
                onClick={() => { setVal(idx, "0"); submitOne(idx, "0"); }}
                className="px-3 py-2 rounded-lg border border-slate-200 dark:border-white/15 hover:bg-slate-50 dark:hover:bg-white/5 text-sm"
              >
                Omitir y continuar
              </button>
            </div>
          )}

          {/* Acciones */}
          <div className="mt-5 flex flex-wrap items-center gap-3 md:gap-4">
            {it.saved && !it.editing && (
              <>
                <span className="text-sm text-emerald-600 dark:text-emerald-400" role="status" aria-live="polite">
                  ✓ Respuesta guardada
                </span>
                <button
                  type="button"
                  className="text-sm text-skyBlue underline underline-offset-4 hover:text-skyBlue/80 transition"
                  onClick={openEditing}
                  disabled={sending}
                >
                  Editar respuesta
                </button>
              </>
            )}

            {it.saved && it.editing && (
              <>
                <button
                  type="button"
                  className="text-sm text-slate-600 dark:text-white/70 underline underline-offset-4 hover:text-white transition"
                  onClick={closeEditing}
                  disabled={sending}
                >
                  Cancelar
                </button>
                {!isCatalog && q.type !== "file" && (
                  <button
                    type="button"
                    className="text-sm text-skyBlue underline underline-offset-4 hover:text-skyBlue/80 transition"
                    onClick={() => submitOne(idx)}
                    disabled={sending}
                  >
                    Guardar cambios
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Overrides de contraste para dark-mode en listbox/opciones */}
      <style jsx global>{`
        .dark [role="listbox"] {
          background-color: rgb(15 23 42) !important;
          color: rgb(226 232 240) !important;
          border: 1px solid rgba(148, 163, 184, 0.35) !important;
        }
        .dark [role="option"] { color: rgb(226 232 240) !important; opacity: 1 !important; }
        .dark [role="option"][aria-selected="true"],
        .dark [role="option"]:hover {
          background-color: rgba(56, 189, 248, 0.18) !important;
          color: rgb(248 250 252) !important;
        }
        .dark [role="option"][aria-disabled="true"] {
          color: rgb(148 163 184) !important;
          opacity: 0.7 !important;
        }
        .dark .react-select__menu {
          background-color: rgb(15 23 42) !important;
          color: rgb(226 232 240) !important;
          border: 1px solid rgba(148,163,184,.35) !important;
        }
        .dark .react-select__option { color: rgb(226 232 240) !important; }
        .dark .react-select__option--is-focused,
        .dark .react-select__option--is-selected {
          background-color: rgba(56,189,248,.18) !important;
          color: rgb(248 250 252) !important;
        }
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
