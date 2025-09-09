"use client";
import { memo, useId } from "react";
import { radioCls } from "@/lib/ui";
import type { Choice } from "@/types/form";

type Props = {
  choices?: Choice[];
  value: string;
  disabled: boolean;
  onSelect: (choiceId: string) => void;
  name: string;
};

function ChoiceInputBase({ choices = [], value, disabled, onSelect, name }: Props) {
  const groupId = useId();

  if (!choices.length) {
    return (
      <p className="text-sm text-slate-500 dark:text-white/60" role="status" aria-live="polite">
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
      {/* Etiqueta invisible del grupo (mejora a11y sin cambiar el layout) */}
      <span id={`${groupId}-legend`} className="sr-only">
        Opciones
      </span>

      {choices.map((c) => {
        const id = `${groupId}-${c.id}`;
        const checked = value === c.id;
        return (
          <label
            key={c.id}
            htmlFor={id}
            className={`${radioCls(checked)} ${disabled ? "opacity-60 cursor-not-allowed" : ""} focus-within:ring-2 focus-within:ring-skyBlue/60`}
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

