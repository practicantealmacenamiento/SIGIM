// src/types/form.ts
export type UUID = string;

export type Choice = {
  id: UUID;
  text: string;
  branch_to: UUID | null; // el backend siempre lo manda (o null)
};

export type Question = {
  id: UUID;
  text: string;
  type: "text" | "number" | "date" | "file" | "choice";
  required: boolean;
  order: number;
  choices?: Choice[];
  file_mode?: "image_ocr" | "ocr_only" | "image_only" | null; // puede venir ausente/null
};

export type NextResponse = Question | { mensaje: "Cuestionario finalizado." };

// Para el flow en UI
export type Item = {
  q: Question;
  value: string;           // texto libre / id de choice / OCR
  saved: boolean;
  editing: boolean;
  files?: File[];          // imágenes subidas
  previews?: string[];     // object URLs
  ocr?: string | null;     // texto OCR (display)
  autoSubmitted?: boolean; // fecha autoguardada
};

// Útiles si consultas selector/panel desde el front
export type QuestionnaireListItem = {
  id: UUID;
  title: string;
  version: string;
};

export type Submission = {
  id: UUID;
  questionnaire: UUID;
  questionnaire_title: string;
  tipo_fase: "entrada" | "salida";
  placa_vehiculo: string | null;
  regulador_id: UUID | null;
  fecha_creacion: string;      // ISO
  finalizado: boolean;
  fecha_cierre: string | null; // ISO
  answers: any[];              // puedes tipar si lo necesitas
};



