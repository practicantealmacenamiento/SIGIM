/* eslint-disable @next/next/no-img-element */
"use client";

import { useRef, useState, DragEvent } from "react";

/**
 * FileInputMulti
 * -------------------------------------------------------
 * Selector de múltiples imágenes con:
 * - Drag & drop sobre la zona punteada.
 * - Botón para abrir cámara/galería (capture="environment").
 * - Previews (máx. 2) con opción de eliminar cada una.
 * - Botón de confirmación "Guardar y continuar".
 *
 * NOTA:
 * - La validación de archivos (tipo/tamaño/cantidad) se hace en el padre.
 * - Este componente asume que `onFilesChange` ya recibe listas válidas.
 */
type Props = {
  active: boolean;
  previews?: string[];
  sending: boolean;
  onFilesChange: (files: FileList | null) => void; // validado desde QuestionCard
  onRemove: (k: number) => void;
  onSubmit: () => void;
};

export default function FileInputMulti({
  active,
  previews = [],
  sending,
  onFilesChange,
  onRemove,
  onSubmit,
}: Props) {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [dragOver, setDragOver] = useState(false);

  // Config: cantidad máxima de imágenes
  const maxImages = 2;
  const remaining = Math.max(0, maxImages - previews.length);
  const inputDisabled = !active || sending || previews.length >= maxImages;

  const inputId = "multi-file-input";
  const helperId = "multi-helper";

  const handleDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    const fl = e.dataTransfer?.files;
    if (fl && fl.length > 0) onFilesChange(fl);
  };

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
          inputDisabled ? "opacity-60 cursor-not-allowed" : "",
        ].join(" ")}
        aria-describedby={helperId}
      >
        <span className="sr-only">Seleccionar imágenes</span>

        {/* Input real (oculto). Se limpia su value para permitir re-selección del mismo archivo. */}
        <input
          id={inputId}
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          capture="environment"
          disabled={inputDisabled}
          onClick={(e) => {
            (e.currentTarget as HTMLInputElement).value = "";
          }}
          onChange={(e) => {
            const fl = (e.target as HTMLInputElement).files;
            if (fl && fl.length > 0) onFilesChange(fl);
            // Limpia para permitir repetir selección
            (e.target as HTMLInputElement).value = "";
          }}
          className="sr-only"
          aria-hidden="true"
          tabIndex={-1}
        />

        <div className="flex items-center justify-between gap-3">
          <div className="text-slate-700 dark:text-white/80">
            <strong>Subir imágenes</strong>
            <div className="text-xs mt-0.5">
              Arrastra y suelta aquí o <span className="underline">haz clic</span> para tomar/seleccionar.
            </div>
          </div>

          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={inputDisabled}
            className="min-h-[40px] px-3 py-2 rounded-lg bg-skyBlue text-white font-medium shadow hover:opacity-90 disabled:opacity-60"
            aria-label="Elegir imágenes"
          >
            Elegir imágenes
          </button>
        </div>
      </label>

      {/* Ayuda / estado de límite */}
      <p
        id={helperId}
        className="text-xs text-slate-600 dark:text-white/70"
        aria-live="polite"
      >
        Puedes subir hasta {maxImages} imágenes.{" "}
        {remaining === 0 ? "Límite alcanzado." : `Te quedan ${remaining}.`}
      </p>

      {/* Grid de previews */}
      {!!previews.length && (
        <div
          className="grid grid-cols-2 gap-2"
          role="list"
          aria-label="Imágenes seleccionadas"
        >
          {previews.map((src, k) => (
            <div
              key={k}
              role="listitem"
              className="relative rounded-lg overflow-hidden border border-slate-200 dark:border-white/10"
            >
              <img
                src={src}
                alt={`Vista previa ${k + 1}`}
                className="w-full h-28 object-cover"
              />
              {active && (
                <button
                  type="button"
                  onClick={() => onRemove(k)}
                  className="absolute top-1 right-1 rounded-full bg-black/50 text-white text-xs px-2 py-0.5 hover:bg-black/70 disabled:opacity-60"
                  aria-label={`Eliminar imagen ${k + 1}`}
                  disabled={sending}
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Acción de confirmación */}
      {active && (
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onSubmit}
            disabled={sending || previews.length === 0}
            className="inline-flex items-center px-4 py-2.5 rounded-lg bg-skyBlue text-white font-medium shadow hover:opacity-90 disabled:opacity-60"
          >
            {sending ? "Guardando…" : "Guardar y continuar"}
          </button>
          {previews.length >= maxImages && (
            <span className="text-xs text-slate-500">
              Máximo {maxImages} imágenes.
            </span>
          )}
        </div>
      )}
    </div>
  );
}



