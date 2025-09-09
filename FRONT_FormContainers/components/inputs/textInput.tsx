"use client";
import { INPUT } from "../../lib/ui";

type Props = {
  value: string;
  disabled: boolean;
  onChange: (v: string) => void;
  onBlur: () => void;
  onEnter: (e: React.KeyboardEvent) => void;
  placeholder?: string;
};

export default function TextInput({
  value,
  disabled,
  onChange,
  onBlur,
  onEnter,
  placeholder,
}: Props) {
  return (
    <input
      type="text"
      value={value}
      disabled={disabled}
      placeholder={placeholder ?? "Tu respuesta…"}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onBlur}
      onKeyDown={(e) => {
        // Ejecuta onEnter solo en Enter "puro" y sin composición (IME)
        const isComposing = (e.nativeEvent as any)?.isComposing;
        if (
          e.key === "Enter" &&
          !e.shiftKey &&
          !e.altKey &&
          !e.ctrlKey &&
          !isComposing
        ) {
          onEnter(e);
        }
      }}
      autoComplete="off"
      className={INPUT}
    />
  );
}
