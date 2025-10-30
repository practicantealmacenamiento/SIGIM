import { useCallback, useRef, useState } from "react";
import { XIcon } from "./ui";

type ToastType = "ok" | "err";

type Toast = {
  id: number;
  type: ToastType;
  text: string;
};

export function useToasts() {
  const [items, setItems] = useState<Toast[]>([]);
  const idRef = useRef(0);

  const remove = useCallback((id: number) => {
    setItems((xs) => xs.filter((t) => t.id !== id));
  }, []);

  const push = useCallback((type: ToastType, text: string) => {
    const id = ++idRef.current;
    setItems((xs) => [...xs, { id, type, text }]);
    setTimeout(() => remove(id), 3500);
  }, [remove]);

  const view = (
    <div className="fixed z-[60] bottom-4 right-4 space-y-2">
      {items.map((t) => (
        <ToastItem key={t.id} toast={t} onClose={() => remove(t.id)} />
      ))}
    </div>
  );

  return { push, view } as const;
}

export type ToastPush = ReturnType<typeof useToasts>["push"];

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  return (
    <div
      role="status"
      className={`flex items-center gap-3 max-w-[360px] rounded-xl px-4 py-3 shadow-lg border ${
        toast.type === "ok"
          ? "bg-emerald-50/90 border-emerald-200/70 text-emerald-800 dark:bg-emerald-900/25 dark:text-emerald-200 dark:border-emerald-900/40"
          : "bg-rose-50/90 border-rose-200/70 text-rose-800 dark:bg-rose-900/25 dark:text-rose-200 dark:border-rose-900/40"
      }`}
    >
      <span className="text-sm leading-snug">{toast.text}</span>
      <button
        onClick={onClose}
        aria-label="Cerrar notificación"
        className="ml-auto inline-flex h-6 w-6 items-center justify-center rounded-md hover:bg-black/5 dark:hover:bg-white/10"
      >
        <XIcon />
      </button>
    </div>
  );
}
