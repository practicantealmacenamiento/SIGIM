"use client";

import { INPUT, today } from "@/lib/ui";

/**
 * DateInput
 * -------------------------------------------------------
 * Campo de fecha controlado.
 * - Si `value` viene vacío, muestra `today()` como valor visual.
 * - `onChange` propaga el valor ISO (YYYY-MM-DD).
 * - `onCommit` se dispara en blur para que el padre guarde/envíe.
 *
 * Accesibilidad:
 * - type="date" ya aporta semántica; añadimos aria-label por si falta <label>.
 */
type Props = {
  value: string;
  disabled: boolean;
  onChange: (v: string) => void;
  onCommit: () => void; // envía con valor actual (se llama en blur)
};

export default function DateInput({ value, disabled, onChange, onCommit }: Props) {
  return (
    <input
      type="date"
      value={value || today()}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onCommit}
      aria-label="Seleccionar fecha"
      className={INPUT}
      // Nota: Si en el futuro necesitas límites:
      // min="1900-01-01" max="2100-12-31"
    />
  );
}

