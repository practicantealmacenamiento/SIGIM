"use client";
import { INPUT, today } from "@/lib/ui";

type Props = {
  value: string;
  disabled: boolean;
  onChange: (v: string) => void;
  onCommit: () => void; // envía con valor actual
};

export default function DateInput({ value, disabled, onChange, onCommit }: Props) {
  return (
    <input
      type="date"
      value={value || today()}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onCommit}
      className={INPUT}
    />
  );
}
