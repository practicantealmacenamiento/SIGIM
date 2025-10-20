// Fecha YYYY-MM-DD en hora local (sin el desfase de toISOString/UTC)
export const today = () => {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
};

type QLike = { type: string; file_mode?: string | null };

// Normaliza el modo del file input a nuestro formato esperado
const normMode = (m?: string | null) =>
  String(m ?? "").toLowerCase().replace(/-/g, "_").trim();

// OCR si el modo contiene "image_ocr" o "ocr_only"
export const isOcr = (q: QLike) =>
  q.type === "file" && ["image_ocr", "ocr_only"].includes(normMode(q.file_mode));

// Image-only es explícitamente "image_only"
export const isImageOnly = (q: QLike) =>
  q.type === "file" && normMode(q.file_mode) === "image_only";

// === Reglas de subida alineadas con el backend ===
export const MAX_FILE_MB = 10 as const;

export const maxFiles = (q: QLike) => {
  if (q.type !== "file") return 0;
  if (isOcr(q)) return 1;       // OCR: exactamente 1 imagen
  if (isImageOnly(q)) return 2; // image_only: 1 o 2 imágenes
  return 0;
};

// Aceptar solo imágenes (el backend para múltiples exige imágenes)
export const fileAccept = (q: QLike) =>
  q.type === "file" ? "image/*" : "";

// Validaciones en cliente (tipo y tamaño, mismas reglas del back)
export const validateFiles = (
  q: QLike,
  files: File[] | FileList
): string | null => {
  const list = Array.from(files ?? []);
  if (q.type !== "file") return null;
  if (list.length === 0) return null; // nada que validar

  const limit = MAX_FILE_MB * 1024 * 1024;

  if (isOcr(q)) {
    if (list.length !== 1) return "Adjunta exactamente 1 imagen.";
    const f = list[0];
    if (!f.type.startsWith("image/")) return "Solo se permiten imágenes (JPG/PNG).";
    if (f.size > limit) return `La imagen no debe superar los ${MAX_FILE_MB}MB.`;
    return null;
  }

  if (isImageOnly(q)) {
    if (list.length < 1 || list.length > 2) return "Adjunta 1 o 2 imágenes.";
    for (const f of list) {
      if (!f.type.startsWith("image/")) return "Solo se permiten imágenes (JPG/PNG).";
      if (f.size > limit) return `Cada imagen no debe superar los ${MAX_FILE_MB}MB.`;
    }
    return null;
  }

  return null;
};

// === Estilos ===
export const CARD =
  "rounded-2xl border shadow transition-all duration-200 bg-white text-[#202020] border-slate-200 " +
  "dark:bg-[#121417] dark:text-bone dark:border-white/10";

export const INPUT =
  "w-full px-4 py-3 md:py-3.5 rounded-xl border outline-none border-slate-300 bg-white text-[#202020] " +
  "focus:ring-2 focus:ring-skyBlue/60 dark:border-white/10 dark:bg-[#0f131a] dark:text-bone";

export const radioCls = (active: boolean) =>
  `flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-colors ${
    active
      ? "bg-skyBlue/10 border-skyBlue"
      : "bg-white border-slate-200 hover:border-slate-300 dark:bg-[#121417] dark:border-white/10"
  }`;



