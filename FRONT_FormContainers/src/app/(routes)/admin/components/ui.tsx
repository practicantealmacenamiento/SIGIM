import type { PropsWithChildren, ReactNode } from "react";

export const shell = {
  page:
    "min-h-[calc(100vh-80px)] w-full bg-gradient-to-b from-slate-50 to-white dark:from-[#0b1220] dark:to-[#0b1220]",
  container: "mx-auto max-w-[1200px] px-6 md:px-8 py-8",
  card:
    "rounded-2xl border border-slate-200/70 dark:border-white/10 bg-white/90 dark:bg-slate-900/90 shadow-lg backdrop-blur supports-[backdrop-filter]:bg-white/60 supports-[backdrop-filter]:dark:bg-slate-900/60",
  input:
    "w-full h-11 px-10 rounded-xl border border-slate-200/70 dark:border-white/10 bg-white dark:bg-slate-950 text-sm outline-none focus:ring-2 focus:ring-sky-300 dark:focus:ring-sky-600",
  select:
    "w-full h-11 px-3 rounded-xl border border-slate-200/70 dark:border-white/10 bg-white dark:bg-slate-950 text-sm outline-none focus:ring-2 focus:ring-sky-300 dark:focus:ring-sky-600",
  btn:
    "px-3 py-2 rounded-xl border border-slate-200/70 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 transition",
  btnPrimary:
    "px-4 py-2.5 rounded-xl bg-sky-600 text-white font-medium shadow-sm hover:bg-sky-700 transition disabled:opacity-60 disabled:cursor-not-allowed",
  iconBtn:
    "inline-flex items-center justify-center h-10 w-10 rounded-xl border border-slate-200/70 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 transition disabled:opacity-40",
  pillTabs:
    "flex gap-1 rounded-2xl p-1 border bg-white/80 dark:bg-slate-900/80 border-slate-200/70 dark:border-white/10 shadow-sm",
  pill: (active: boolean) =>
    `px-4 py-2 rounded-xl text-sm ${
      active
        ? "bg-slate-100 dark:bg-white/10 font-medium"
        : "hover:bg-slate-50 dark:hover:bg-white/5"
    }`,
  th: "px-4 py-3 font-semibold text-slate-600 dark:text-slate-300 text-xs uppercase tracking-wide",
  td: "px-4 py-3 text-sm",
  kbd:
    "inline-flex items-center gap-1 rounded-md px-1.5 py-[2px] text-[11px] font-medium border border-slate-200/70 dark:border-white/10 bg-slate-50 dark:bg-white/5",
};

export function SearchIcon() {
  return (
    <svg
      className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 opacity-60"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M15.5 14h-.79l-.28-.27A6.5 6.5 0 1 0 14 15.5l.27.28v.79l5 5 1.5-1.5-5-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z" />
    </svg>
  );
}

export function XIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M18.3 5.71a1 1 0 0 0-1.41 0L12 10.59 7.11 5.7A1 1 0 0 0 5.7 7.11L10.59 12l-4.9 4.89a1 1 0 1 0 1.41 1.41L12 13.41l4.89 4.9a1 1 0 0 0 1.41-1.42L13.41 12l4.9-4.89a1 1 0 0 0-.01-1.4z" />
    </svg>
  );
}

type SectionProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
};

export function Section({ title, subtitle, actions, children }: PropsWithChildren<SectionProps>) {
  return (
    <section className="mb-6">
      <div className="mb-3 grid gap-1 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
          {subtitle && <p className="text-sm text-slate-500 dark:text-slate-300">{subtitle}</p>}
        </div>
        {actions && <div className="w-full lg:w-auto max-w-[720px]">{actions}</div>}
      </div>
      {children}
    </section>
  );
}

export function SkeletonRows({ rows = 6 }: { rows?: number }) {
  return (
    <tbody>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i} className="border-b border-slate-100 dark:border-white/10 animate-pulse">
          <td className={shell.td} colSpan={6}>
            <div className="h-6 rounded bg-slate-100 dark:bg-white/10" />
          </td>
        </tr>
      ))}
    </tbody>
  );
}
