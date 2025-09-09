import { memo } from "react";

type Props = {
  respondidas: number;
  total: number;
  fase?: "entrada" | "salida";
  regulador?: string;
};

function HeaderForm({ respondidas, total, fase, regulador }: Props) {
  const pct = Math.min(Math.round((respondidas / total) * 100), 100);
  const faseLabel = fase === "entrada" ? "Fase 1: Entrada" : fase === "salida" ? "Fase 2: Salida" : null;

  return (
    <header className="sticky top-0 z-30 backdrop-blur bg-white/80 dark:bg-slate-900/80 border-b border-slate-200 dark:border-white/10 px-4 md:px-6 py-3 md:py-4 shadow-sm">
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

export default memo(HeaderForm);


