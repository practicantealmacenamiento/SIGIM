"use client";

import { memo, useId } from "react";
import { radioCls } from "@/lib/ui";
import type { Choice } from "@/types/form";

/**
 * ChoiceInput
 * -------------------------------------------------------
 * Grupo de opciones tipo "radio".
 * - Ordena opciones por texto usando Intl.Collator (orden natural).
 * - A11y: usa role="radiogroup" + label invisible asociado.
 * - No incluye lógica de negocio: delega en `onSelect`.
 */
type Props = {
  choices?: Choice[];
  value: string;
  disabled: boolean;
  onSelect: (choiceId: string) => void;
  name: string; // atributo `name` del grupo de radios (controlado por el padre)
};

function ChoiceInputBase({
  choices = [],
  value,
  disabled,
  onSelect,
  name,
}: Props) {
  const groupId = useId();

  // Orden “natural” por texto (respeta números incrustados)
  const collator = new Intl.Collator(undefined, {
    numeric: true,
    sensitivity: "base",
  });
  const sortedChoices = [...choices].sort((a, b) =>
    collator.compare(a.text, b.text)
  );

  if (!sortedChoices.length) {
    return (
      <p
        className="text-sm text-slate-500 dark:text-white/60"
        role="status"
        aria-live="polite"
      >
        No hay opciones disponibles.
      </p>
    );
  }

  return (
    <div
      role="radiogroup"
      aria-disabled={disabled || undefined}
      aria-labelledby={`${groupId}-legend`}
      className="grid gap-2"
    >
      {/* Etiqueta invisible del grupo (mejora a11y sin alterar el layout) */}
      <span id={`${groupId}-legend`} className="sr-only">
        Opciones
      </span>

      {sortedChoices.map((c) => {
        const id = `${groupId}-${c.id}`;
        const checked = value === c.id;

        return (
          <label
            key={c.id}
            htmlFor={id}
            className={[
              radioCls(checked),
              disabled ? "opacity-60 cursor-not-allowed" : "",
              "focus-within:ring-2 focus-within:ring-skyBlue/60",
            ].join(" ")}
          >
            <input
              id={id}
              type="radio"
              name={name}
              value={c.id}
              disabled={disabled}
              checked={checked}
              onChange={(e) => onSelect(e.target.value)}
              className="h-4 w-4"
            />
            <span className="select-none">{c.text}</span>
          </label>
        );
      })}
    </div>
  );
}

const ChoiceInput = memo(ChoiceInputBase);
export default ChoiceInput;

