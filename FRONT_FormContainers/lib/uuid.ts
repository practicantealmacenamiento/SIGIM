// lib/uuid.ts
/* eslint-disable no-bitwise */

// Generador UUID v4 tolerante a SSR y a entornos sin crypto.randomUUID
export function genUUID(): string {
  // 1) randomUUID nativo si existe (browser moderno / Node reciente con webcrypto)
  const g: any = typeof globalThis !== "undefined" ? globalThis : undefined;
  const c: any = g?.crypto;
  if (c && typeof c.randomUUID === "function") {
    try {
      return c.randomUUID();
    } catch {
      // continúa a getRandomValues
    }
  }

  // 2) WebCrypto getRandomValues (browser seguro / Node con webcrypto)
  if (c && typeof c.getRandomValues === "function") {
    const b = new Uint8Array(16);
    c.getRandomValues(b);

    // v4: 0100 xxxx en byte 6, y 10xx xxxx en byte 8
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;

    // lookup de hex para rendimiento y consistencia
    const lut = HEX_LUT;
    return (
      lut[b[0]] + lut[b[1]] + lut[b[2]] + lut[b[3]] + "-" +
      lut[b[4]] + lut[b[5]] + "-" +
      lut[b[6]] + lut[b[7]] + "-" +
      lut[b[8]] + lut[b[9]] + "-" +
      lut[b[10]] + lut[b[11]] + lut[b[12]] + lut[b[13]] + lut[b[14]] + lut[b[15]]
    );
  }

  // 3) Fallback: Math.random (no críptico, suficiente para IDs temporales en UI)
  //    Mantiene el formato v4 (bits de versión/variante forzados).
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (ch) => {
    const r = (Math.random() * 16) | 0;
    const v = ch === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Tabla de lookup hex (00..ff)
const HEX_LUT: string[] = (() => {
  const arr = new Array<string>(256);
  for (let i = 0; i < 256; i++) arr[i] = (i + 256).toString(16).slice(1);
  return arr;
})();

