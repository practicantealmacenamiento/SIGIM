// Generador UUID v4 tolerante a SSR y a navegadores sin crypto.randomUUID
export function genUUID(): string {
  // 1) randomUUID nativo si existe (browser moderno)
  if (typeof globalThis !== "undefined") {
    const anyGlobal: any = globalThis as any;
    const c = anyGlobal.crypto;
    if (c && typeof c.randomUUID === "function") {
      try { return c.randomUUID(); } catch {}
    }
    // 2) WebCrypto getRandomValues (browser seguro)
    if (c && typeof c.getRandomValues === "function") {
      const b = new Uint8Array(16);
      c.getRandomValues(b);
      b[6] = (b[6] & 0x0f) | 0x40; // version 4
      b[8] = (b[8] & 0x3f) | 0x80; // variant 10
      const h = Array.from(b, (x) => x.toString(16).padStart(2, "0"));
      return `${h.slice(0,4).join("")}-${h.slice(4,6).join("")}-${h.slice(6,8).join("")}-${h.slice(8,10).join("")}-${h.slice(10).join("")}`;
    }
    // 3) Node 18+: crypto.randomUUID vía módulo nativo (si expuesto en globalThis.crypto)
    // (si usas Node 18+ y quieres forzar, puedes importar { randomUUID } from 'crypto' del lado servidor)
  }
  // 4) Fallback puro Math.random (no críptico, suficiente para IDs temporales en UI)
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
