/* eslint-disable @next/next/no-img-element */
"use client";

import { useRef, useState, DragEvent, useId } from "react";
import { CARD, INPUT } from "@/lib/ui";

/**
 * Info opcional para validar/mostrar detalles de contenedor ISO 6346.
 */
type ContainerInfo = {
  code: string;
  checkDigit: number | null;
  providedDigit: number | null;
  validIso: boolean | null;
};

/**
 * Props
 * - `active`: habilita interacciones (cuando la tarjeta está en edición).
 * - `previews`: URLs de ObjectURL ya generadas por el padre.
 * - `value`: texto OCR editable (controlado).
 * - `ocrStatus`: "Procesando...", "Error...", etc. (solo display).
 * - `onFilesChange`: ya validado en el padre.
 * - `onChangeText`: actualiza el texto OCR manualmente.
 * - `onSubmit`: confirma guardado.
 * - `onRetryOCR`: reintenta el OCR para la imagen actual.
 * - `containerInfo`: bloque opcional con estado ISO 6346.
 */
type Props = {
  active: boolean;
  previews?: string[];
  value: string;
  ocrStatus?: string;
  sending: boolean;
  onFilesChange: (files: FileList | null) => void;
  onChangeText: (v: string) => void;
  onSubmit: () => void;
  onRetryOCR: () => void;
  containerInfo?: ContainerInfo;
};

export default function FileInputOCR({
  active,
  previews = [],
  value,
  ocrStatus,
  sending,
  onFilesChange,
  onChangeText,
  onSubmit,
  onRetryOCR,
  containerInfo,
}: Props) {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const disabled = !active || sending;

  // IDs únicos para ARIA (evita colisiones si hay varias tarjetas)
  const uid = useId();
  const inputId = `ocr-file-input-${uid}`;
  const statusId = `ocr-status-${uid}`;
  const textId = `ocr-textarea-${uid}`;

  const handleDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    const fl = e.dataTransfer?.files;
    if (fl && fl.length > 0) onFilesChange(fl);
  };

  // Badge de ISO 6346 (si se provee información del contenedor)
  const isoBadge = (() => {
    if (!containerInfo) return null;
    if (containerInfo.validIso === true) {
      return (
        <span className="inline-flex items-center gap-1.5 text-emerald-700 bg-emerald-50 dark:bg-emerald-400/10 dark:text-emerald-300 border border-emerald-200/70 dark:border-emerald-300/20 px-2 py-1 rounded-md text-xs">
          ✓ ISO 6346 válido
        </span>
      );
    }
    if (containerInfo.validIso === false) {
      return (
        <span className="inline-flex items-center gap-1.5 text-red-700 bg-red-50 dark:bg-red-400/10 dark:text-red-300 border border-red-200/70 dark:border-red-300/20 px-2 py-1 rounded-md text-xs">
          ✕ ISO 6346 no válido
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 text-slate-600 bg-slate-100 dark:bg-white/10 dark:text-white/70 border border-slate-200/70 dark:border-white/10 px-2 py-1 rounded-md text-xs">
        ISO 6346 no detectado
      </span>
    );
  })();

  return (
    <div className="space-y-4">
      {/* Zona de subida (click/cámara + drag&drop) */}
      <label
        htmlFor={inputId}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={[
          "block rounded-lg border border-dashed p-4 text-sm transition-colors cursor-pointer",
          dragOver ? "border-skyBlue bg-skyBlue/5" : "border-slate-300 dark:border-white/10",
          disabled ? "opacity-60 cursor-not-allowed" : "",
        ].join(" ")}
        aria-busy={ocrStatus === "Procesando..."}
        aria-describedby={statusId}
      >
        <span className="sr-only">Seleccionar imagen</span>
        <input
          id={inputId}
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple={false}
          capture="environment"
          disabled={disabled}
          onClick={(e) => {
            // Permite re-seleccionar el mismo archivo
            (e.currentTarget as HTMLInputElement).value = "";
          }}
          onChange={(e) => {
            const fl = (e.target as HTMLInputElement).files;
            if (fl && fl.length > 0) onFilesChange(fl);
            (e.target as HTMLInputElement).value = "";
          }}
          className="sr-only"
        />

        <div className="flex items-center justify-between gap-3">
          <div className="text-slate-700 dark:text-white/80">
            <strong>Subir imagen</strong>
            <div className="text-xs mt-0.5">
              Arrastra y suelta aquí o <span className="underline">haz clic</span> para tomar/seleccionar.
            </div>
          </div>
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={disabled}
            className="min-h-[40px] px-3 py-2 rounded-lg bg-skyBlue text-white font-medium shadow hover:opacity-90 disabled:opacity-60"
          >
            Elegir imagen
          </button>
        </div>
      </label>

      {/* Previews */}
      {!!previews.length && (
        <div className="grid grid-cols-2 gap-2">
          {previews.map((src, k) => (
            <div
              key={k}
              className="rounded-lg overflow-hidden border border-slate-200 dark:border-white/10"
            >
              <img src={src} alt={`Vista previa ${k + 1}`} className="w-full h-28 object-cover" />
            </div>
          ))}
        </div>
      )}

      {/* Estado de OCR */}
      {previews.length > 0 && (
        <p
          id={statusId}
          className="text-xs text-slate-600 dark:text-white/70"
          aria-live="polite"
        >
          {ocrStatus ? ocrStatus : "1 imagen lista para OCR."}
        </p>
      )}

      {/* Campo de texto OCR (editable) */}
      <div className={`${CARD} border-dashed`} aria-live="polite">
        <div className="text-sm font-semibold mb-2 px-3 pt-3 text-slate-600 dark:text-white/80">
          Texto detectado
        </div>
        <div className="p-3">
          <textarea
            id={textId}
            rows={3}
            value={value}
            disabled={disabled}
            onChange={(e) => onChangeText(e.target.value)}
            placeholder={
              previews.length
                ? "Extrayendo texto… (puedes editar luego)"
                : "Sube una imagen para extraer texto"
            }
            className={INPUT}
            autoComplete="off"
            spellCheck={false}
            aria-describedby={containerInfo ? `${statusId}-iso` : undefined}
          />
        </div>

        {/* Bloque de contenedor (ISO 6346) */}
        {containerInfo && (
          <div className="px-3 pb-3" id={`${statusId}-iso`}>
            <div className="flex items-center justify-between flex-wrap gap-2 mb-1">
              <div className="text-sm font-medium text-slate-700 dark:text-white/80">
                Código de contenedor:
                <span className="ml-2 font-semibold tracking-wide">
                  {containerInfo.code}
                </span>
              </div>
              {isoBadge}
            </div>
            <div className="text-xs text-slate-600 dark:text-white/70">
              Dígito verificación (calculado):{" "}
              <span className="font-medium">
                {containerInfo.checkDigit ?? "—"}
              </span>
              {typeof containerInfo.providedDigit === "number" && (
                <>
                  {" "}| impreso:{" "}
                  <span className="font-medium">{containerInfo.providedDigit}</span>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Acciones */}
      {active && (
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={onSubmit}
            disabled={sending || !previews.length || !value}
            className="inline-flex items-center min-h-[44px] px-4 py-2.5 rounded-lg bg-skyBlue text-white font-medium shadow hover:opacity-90 disabled:opacity-60"
          >
            {sending ? "Guardando…" : "Guardar y continuar"}
          </button>

          <button
            type="button"
            onClick={onRetryOCR}
            disabled={sending || !previews.length}
            className="min-h-[44px] text-sm md:text-base text-slate-600 dark:text-white/70 underline underline-offset-4 disabled:opacity-60"
          >
            Reintentar OCR
          </button>

          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={sending}
            className="min-h-[44px] text-sm md:text-base text-slate-600 dark:text-white/70 underline underline-offset-4 disabled:opacity-60"
          >
            Cambiar imagen
          </button>
        </div>
      )}
    </div>
  );
}


