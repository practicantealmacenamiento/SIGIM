import { memo } from "react";

type Props = {
  /** Cantidad de preguntas respondidas en el formulario. */
  respondidas: number;
  /** Cantidad total de preguntas del formulario. */
  total: number;
  /** Fase del proceso (opcional): "entrada" | "salida". */
  fase?: "entrada" | "salida";
  /** Nombre del regulador (opcional). */
  regulador?: string;
};

/** Asegura que el valor esté en el rango [min, max]. */
function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(n, max));
}

/**
 * HeaderForm — Encabezado fijo del formulario con:
 * - Título + metadatos (fase, regulador)
 * - Barra de progreso accesible
 *
 * Accesibilidad (A11y):
 * - `role="progressbar"` con `aria-valuemin|now|max`
 * - `aria-label` y `title` descriptivos
 */
function HeaderForm({ respondidas, total, fase, regulador }: Props) {
  // Evita división por cero y clamp del porcentaje a [0, 100]
  const rawPct = total > 0 ? Math.round((respondidas / total) * 100) : 0;
  const pct = clamp(rawPct, 0, 100);

  const faseLabel =
    fase === "entrada"
      ? "Fase 1: Entrada"
      : fase === "salida"
      ? "Fase 2: Salida"
      : null;

  const progressAria = `Progreso del formulario: ${pct}% completado`;
  const titleText =
    faseLabel
      ? `Formulario — ${faseLabel} — ${pct}%`
      : `Formulario — ${pct}%`;

  return (
    <header
      className="sticky top-0 z-30 backdrop-blur bg-white/80 dark:bg-slate-900/80 border-b border-slate-200 dark:border-white/10 px-4 md:px-6 py-3 md:py-4 shadow-sm"
      title={titleText}
    >
      <div className="flex items-center justify-between">
        <div className="flex flex-col">
          <h1 className="text-lg md:text-xl font-semibold text-slate-900 dark:text-white">
            Formulario
          </h1>

          {faseLabel && (
            <span className="text-xs md:text-sm text-skyBlue font-medium">
              {faseLabel}
            </span>
          )}

          {regulador && (
            <span className="text-xs text-slate-500 dark:text-white/60">
              Regulador: {regulador}
            </span>
          )}
        </div>

        <div className="text-right">
          <span className="text-sm md:text-base text-slate-700 dark:text-white/70">
            {pct}%
          </span>

          <div
            role="progressbar"
            aria-label={progressAria}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={pct}
            className="mt-1 h-1.5 w-24 md:w-32 rounded-full bg-slate-200 dark:bg-white/10 overflow-hidden"
          >
            <div
              style={{ width: `${pct}%` }}
              className="h-full bg-skyBlue transition-all duration-500 ease-out"
            />
          </div>
        </div>
      </div>
    </header>
  );
}

/** Evita renders si no cambiaron props relevantes. */
function areEqual(prev: Props, next: Props) {
  return (
    prev.respondidas === next.respondidas &&
    prev.total === next.total &&
    prev.fase === next.fase &&
    prev.regulador === next.regulador
  );
}

export default memo(HeaderForm, areEqual);

