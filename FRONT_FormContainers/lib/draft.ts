// lib/draft.ts

// Fallback en memoria si no hay Web Storage disponible
const memStore = new Map<string, string>();

function getStorage(kind: "local" | "session"): Storage | null {
  try {
    if (typeof window === "undefined") return null;
    const s = kind === "local" ? window.localStorage : window.sessionStorage;
    // chequeo básico de operatividad
    const k = "__draft_probe__";
    s.setItem(k, "1");
    s.removeItem(k);
    return s;
  } catch {
    return null;
  }
}

const local = () => getStorage("local");
const session = () => getStorage("session");

function writeAny(key: string, value: string) {
  const l = local();
  if (l) {
    try { l.setItem(key, value); return; } catch {}
  }
  const s = session();
  if (s) {
    try { s.setItem(key, value); return; } catch {}
  }
  // último recurso: memoria
  memStore.set(key, value);
}

function readAny(key: string): string | null {
  const l = local();
  if (l) {
    try {
      const v = l.getItem(key);
      if (v != null) return v;
    } catch {}
  }
  const s = session();
  if (s) {
    try {
      const v = s.getItem(key);
      if (v != null) return v;
    } catch {}
  }
  return memStore.get(key) ?? null;
}

function removeAny(key: string) {
  const l = local();
  if (l) { try { l.removeItem(key); } catch {} }
  const s = session();
  if (s) { try { s.removeItem(key); } catch {} }
  memStore.delete(key);
}

export function saveDraft(key: string, data: any) {
  try {
    // stringify directo (no replacer para mantener compatibilidad)
    const payload = JSON.stringify(data);
    writeAny(key, payload);
  } catch {
    // si el objeto no es serializable, ignoramos silenciosamente para no romper UI
  }
}

export function loadDraft<T = any>(key: string): T | null {
  try {
    const raw = readAny(key);
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function clearDraft(key: string) {
  try { removeAny(key); } catch {}
}

