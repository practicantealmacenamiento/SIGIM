export type ActorTipo = "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR";

export type AdminChoice = {
  id: string;
  text: string;
  branch_to: string | null;
};

export type AdminQuestionType = "text" | "number" | "date" | "file" | "choice";

export type AdminQuestion = {
  id: string;
  text: string;
  type: AdminQuestionType;
  required: boolean;
  order: number;
  choices: AdminChoice[] | null;
  file_mode?: "image_only" | "image_ocr" | "ocr_only";
  semantic_tag?: string;
};

export type AdminQuestionnaire = {
  id: string;
  title: string;
  version: string;
  timezone: string;
  questions: AdminQuestion[];
};

export type AdminUser = {
  id?: number;
  username: string;
  email?: string;
  is_staff: boolean;
  is_superuser: boolean;
  is_active: boolean;
  password?: string;
};

export type WhoAmI = {
  id?: number | string;
  username: string;
  email?: string;
  is_staff: boolean;
};

export type Actor = {
  id: string;
  nombre: string;
  tipo: ActorTipo;
  documento?: string | null;
  activo: boolean;
};

export type Paginated<T> = {
  results: T[];
  count: number;
  page: number;
  page_size: number;
  next?: string | null;
  prev?: string | null;
};

