"use client";

import { INPUT } from "@/lib/ui";

/**
 * NumberInput
 * -------------------------------------------------------
 * Campo numérico controlado con protecciones UX:
 * - Bloquea la notación científica (teclas "e"/"E").
 * - Dispara `onEnter` sólo cuando es Enter “puro” (sin Shift/Ctrl/Alt y sin composición IME).
 * - Evita cambios accidentales con la rueda del mouse (blur al hacer scroll).
 *
 * NOTA:
 * - El valor se maneja como string para no perder precisión/formato intermedio.
 */
type Props = {
  value: string;
  disabled: boolean;
  onChange: (v: string) => void;
  onBlur: () => void;
  onEnter: (e: React.KeyboardEvent) => void;
};

export default function NumberInput({
  value,
  disabled,
  onChange,
  onBlur,
  onEnter,
}: Props) {
  return (
    <input
      type="number"
      value={value}
      disabled={disabled}
      placeholder="0"
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
      onKeyDown={(e) => {
        // Evita notación científica en <input type="number">
        if (e.key === "e" || e.key === "E") {
          e.preventDefault();
          return;
        }
        // Ejecuta onEnter solo en Enter “puro” y sin composición
        const isComposing = (e.nativeEvent as any)?.isComposing;
        if (
          e.key === "Enter" &&
          !e.shiftKey &&
          !e.ctrlKey &&
          !e.altKey &&
          !isComposing
        ) {
          onEnter(e);
        }
      }}
      // Evita que la rueda del mouse cambie el valor por accidente
      onWheel={(e) => {
        (e.currentTarget as HTMLInputElement).blur();
      }}
      inputMode="numeric"
      pattern="[0-9]*"
      autoComplete="off"
      aria-label="Ingresar número"
      className={INPUT}
    />
  );
}


