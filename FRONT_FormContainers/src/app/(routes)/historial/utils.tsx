import { type ReactNode } from "react";

import type { HistorialRow } from "@/lib/api.historial";

const tz = "America/Bogota";

const iconBase = "h-5 w-5";

const outline = (paths: ReactNode, viewBox = "0 0 24 24") => (
  <svg
    aria-hidden
    viewBox={viewBox}
    className={`${iconBase} text-slate-500 dark:text-slate-300`}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    {paths}
  </svg>
);

const solid = (paths: ReactNode, viewBox = "0 0 24 24") => (
  <svg aria-hidden viewBox={viewBox} className={`${iconBase} text-slate-500 dark:text-slate-300`} fill="currentColor">
    {paths}
  </svg>
);

export const ICONS = {
  statusComplete: outline(
    <>
      <path d="M9 12l2 2 4-4" />
      <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z" />
    </>
  ),
  statusPending: outline(
    <>
      <path d="M12 6v6l3 1.5" />
      <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z" />
    </>
  ),
  truck: outline(
    <>
      <path d="M2.25 15.75V6a1.5 1.5 0 0 1 1.5-1.5h8.25V15" />
      <path d="M12 9h3.38a1.5 1.5 0 0 1 1.23.64l2.64 3.72a2 2 0 0 1 .37 1.17V15" />
      <path d="M5.25 18.75a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" />
      <path d="M16.5 18.75a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" />
      <path d="M7.5 18.75h7.5" />
    </>
  ),
  provider: outline(
    <>
      <path d="M3.75 20.25h16.5" />
      <path d="M4.5 9.75h15" />
      <path d="M6 3.75h3v6H6zM10.5 3.75h3v6h-3zM15 3.75h3v6h-3z" />
      <path d="M6 12v8.25M12 12v8.25M18 12v8.25" />
    </>
  ),
  transport: outline(
    <>
      <path d="M15 19.5v-2.25A2.25 2.25 0 0 0 12.75 15h-1.5A2.25 2.25 0 0 0 9 17.25V19.5" />
      <path d="M12 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
      <path d="M19.5 19.5v-2.25a2.25 2.25 0 0 0-2.25-2.25h-.462" />
      <path d="M18 11.25a2.25 2.25 0 1 0-1.5-4.26" />
      <path d="M4.5 19.5v-2.25A2.25 2.25 0 0 1 6.75 15h.462" />
      <path d="M6 11.25a2.25 2.25 0 1 1 1.5-4.26" />
    </>
  ),
  empty: outline(
    <>
      <path d="M3 7.5c0-.621.252-1.215.7-1.652a2.35 2.35 0 0 1 1.65-.698h13.3c.62 0 1.215.251 1.653.699.445.44.697 1.035.697 1.651v9.75a2.35 2.35 0 0 1-.697 1.651 2.35 2.35 0 0 1-1.653.699H5.35a2.35 2.35 0 0 1-1.65-.699A2.35 2.35 0 0 1 3 17.25V7.5Z" />
      <path d="M3 7.5h18" />
      <path d="M8.25 7.5V6A1.5 1.5 0 0 1 9.75 4.5h4.5A1.5 1.5 0 0 1 15.75 6v1.5" />
    </>
  ),
  search: outline(<path d="m21 21-4.35-4.35M11.25 18a6.75 6.75 0 1 0 0-13.5 6.75 6.75 0 0 0 0 13.5Z" />),
  calendar: outline(
    <>
      <path d="M8 3.75V6" />
      <path d="M16 3.75V6" />
      <path d="M3.75 9.75h16.5" />
      <path d="M5.25 5.25h13.5a1.5 1.5 0 0 1 1.5 1.5v11.25a1.5 1.5 0 0 1-1.5 1.5H5.25a1.5 1.5 0 0 1-1.5-1.5V6.75a1.5 1.5 0 0 1 1.5-1.5Z" />
    </>
  ),
  menu: outline(<path d="M4 8h16M4 12h16M4 16h16" />),
  link: outline(
    <>
      <path d="M9.172 14.828a4 4 0 0 1 0-5.656l3.536-3.536a4 4 0 0 1 5.657 5.656l-1.415 1.415" />
      <path d="M14.828 9.172a4 4 0 0 1 0 5.656l-3.536 3.536a4 4 0 1 1-5.657-5.656l1.415-1.415" />
    </>
  ),
  download: outline(
    <>
      <path d="M12 4v10.5" />
      <path d="m8.25 11.25 3.75 3.75 3.75-3.75" />
      <path d="M4.5 19.5h15" />
    </>
  ),
  clear: outline(<path d="M6 18 18 6M6 6l12 12" />),
  refresh: outline(
    <>
      <path d="M3 12a9 9 0 1 1 9 9" />
      <path d="M3 12h4.5" />
      <path d="M7.5 12 5 14.5" />
    </>
  ),
  filter: outline(
    <>
      <path d="M4.5 5.25h15" />
      <path d="M7.5 12h9" />
      <path d="M10.5 18.75h3" />
    </>
  ),
  plus: outline(
    <>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </>
  ),
  minus: outline(<path d="M5 12h14" />),
  chevronLeft: solid(
    <path
      fillRule="evenodd"
      d="M12.53 7.22a.75.75 0 0 0-1.06 0L7.72 11a.75.75 0 0 0 0 1.06l3.75 3.75a.75.75 0 0 0 1.06-1.06L9.81 12l2.72-2.72a.75.75 0 0 0 0-1.06Z"
      clipRule="evenodd"
    />,
    "0 0 24 24"
  ),
  chevronRight: solid(
    <path
      fillRule="evenodd"
      d="M11.47 7.22a.75.75 0 0 1 1.06 0l3.75 3.75a.75.75 0 0 1 0 1.06l-3.75 3.75a.75.75 0 1 1-1.06-1.06L14.19 12l-2.72-2.72a.75.75 0 0 1 0-1.06Z"
      clipRule="evenodd"
    />,
    "0 0 24 24"
  ),
};

export const fmtDateTime = (iso?: string | null) =>
  iso
    ? new Intl.DateTimeFormat("es-CO", { timeZone: tz, dateStyle: "medium", timeStyle: "short" }).format(new Date(iso))
    : "-";

export const fmtShortDate = (iso?: string) => {
  if (!iso) return "";
  const d = new Date(iso);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
};

export function statusVisual(state: "completo" | "pendiente") {
  if (state === "completo") {
    return {
      icon: ICONS.statusComplete,
      label: "Completo",
      bar: "bg-emerald-600",
      badge:
        "bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-200 dark:border-emerald-800/60",
      dot: "bg-emerald-500",
    };
  }
  return {
    icon: ICONS.statusPending,
    label: "Pendiente",
    bar: "bg-amber-500",
    badge:
      "bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/40 dark:text-amber-200 dark:border-amber-800/60",
    dot: "bg-amber-400",
  };
}

function mergeActors(primary: HistorialRow, secondary?: HistorialRow): HistorialRow {
  if (!secondary) return primary;
  return {
    ...primary,
    proveedor: primary.proveedor ?? secondary.proveedor ?? null,
    transportista: primary.transportista ?? secondary.transportista ?? null,
  };
}

function pickBetter(a: HistorialRow, b: HistorialRow) {
  const score = (x: HistorialRow) => (x.fase1_id ? 1 : 0) + (x.fase2_id ? 1 : 0);
  const ts = (x: HistorialRow) =>
    new Date(x.ultima_fecha_cierre || x.fecha_salida || x.fecha_entrada || 0).getTime();
  const better = score(a) !== score(b) ? (score(a) > score(b) ? a : b) : ts(a) >= ts(b) ? a : b;
  const other = better === a ? b : a;
  return mergeActors(better, other);
}

export function normalizeRows(input: HistorialRow[]): HistorialRow[] {
  const map = new Map<string, HistorialRow>();
  for (const r of input) {
    const k = r.regulador_id || `${r.fase1_id ?? ""}/${r.fase2_id ?? ""}/${r.placa ?? ""}`;
    const prev = map.get(k);
    map.set(k, prev ? pickBetter(prev, r) : r);
  }
  return Array.from(map.values());
}

export function rowKey(r: HistorialRow, index?: number) {
  const baseKey = `${r.regulador_id ?? "reg"}::${r.fase1_id ?? "_"}::${r.fase2_id ?? "_"}::${r.placa ?? "_"}`;
  return index !== undefined ? `${baseKey}::${index}` : baseKey;
}
