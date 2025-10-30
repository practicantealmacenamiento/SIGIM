/**
 * Operaciones de cuestionarios (listar, obtener, guardar, duplicar y reordenar).
 */
import { ADMIN_MGMT_PREFIX, ADMIN_PREFIX } from "./constants";
import { apiFetch, apiTry } from "./client";
import type {
  AdminChoice,
  AdminQuestion,
  AdminQuestionType,
  AdminQuestionnaire,
} from "./types";

export async function createQuestionnaire(input: {
  title: string;
  version?: string;
  timezone?: string;
  questions?: Array<{
    text: string;
    type?: string;
    required?: boolean;
    order?: number;
    file_mode?: string;
    semantic_tag?: string | null;
    choices?: Array<{ text: string; branch_to?: string | null }>;
  }>;
}) {
  const body = {
    title: input.title,
    version: input.version ?? "v1",
    timezone: input.timezone ?? "America/Bogota",
    ...(Array.isArray(input.questions) ? { questions: input.questions } : {}),
  };
  return apiFetch(`${ADMIN_MGMT_PREFIX}/questionnaires/`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

function normalizeQuestion(raw: any, idx: number): AdminQuestion {
  const id = String(raw?.id ?? raw?.uuid ?? raw?.pk ?? `${idx + 1}`);
  const type = (raw?.type ?? raw?.tipo ?? "text") as AdminQuestionType;

  const rawChoices: any[] | null = Array.isArray(raw?.choices)
    ? raw.choices
    : Array.isArray(raw?.opciones)
    ? raw.opciones
    : null;

  const choices: AdminChoice[] | null = rawChoices
    ? rawChoices.map((choice, j) => ({
        id: String(choice?.id ?? choice?.uuid ?? choice?.pk ?? `${id}-c${j + 1}`),
        text: String(choice?.text ?? choice?.label ?? choice?.texto ?? ""),
        branch_to: choice?.branch_to ?? choice?.rama_a ?? null,
      }))
    : null;

  return {
    id,
    text: String(raw?.text ?? raw?.titulo ?? raw?.pregunta ?? ""),
    type,
    required: !!(raw?.required ?? raw?.obligatoria ?? false),
    order: Number(raw?.order ?? raw?.orden ?? idx + 1),
    choices,
    file_mode: raw?.file_mode,
    semantic_tag: raw?.semantic_tag ?? raw?.etiqueta ?? undefined,
  };
}

export async function listQuestionnaires(): Promise<
  { id: string; title: string; version: string; questions: number }[]
> {
  const data = await apiTry<any>([
    `${ADMIN_MGMT_PREFIX}/questionnaires/`,
    `${ADMIN_PREFIX}/cuestionarios/`,
    `${ADMIN_PREFIX}/questionnaires/`,
  ]);

  const rows: { id: string; title: string; version: string }[] = (
    Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : []
  ).map((item: any) => ({
    id: String(item.id ?? item.uuid ?? item.pk),
    title: String(item.title ?? item.nombre ?? "Sin título"),
    version: String(item.version ?? item.vers ?? "v1"),
  }));

  const limit = 4;
  let index = 0;
  const enriched: {
    id: string;
    title: string;
    version: string;
    questions: number;
  }[] = [];

  async function hydrate() {
    const current = index++;
    if (current >= rows.length) return;
    const row = rows[current];
    try {
      const detail = await apiTry<any>([
        `${ADMIN_MGMT_PREFIX}/questionnaires/${row.id}/`,
        `${ADMIN_PREFIX}/cuestionarios/${row.id}/`,
        `${ADMIN_PREFIX}/questionnaires/${row.id}/`,
      ]);
      const questions = Array.isArray(detail?.questions)
        ? detail.questions
        : detail?.preguntas ?? [];
      enriched[current] = { ...row, questions: Array.isArray(questions) ? questions.length : 0 };
    } catch {
      enriched[current] = { ...row, questions: 0 };
    }
    await hydrate();
  }

  await Promise.all(
    Array.from({ length: Math.min(limit, rows.length) }, () => hydrate())
  );

  return enriched;
}

export async function getQuestionnaire(id: string): Promise<AdminQuestionnaire> {
  const raw = await apiTry<any>([
    `${ADMIN_MGMT_PREFIX}/questionnaires/${id}/`,
    `${ADMIN_PREFIX}/cuestionarios/${id}/`,
    `${ADMIN_PREFIX}/questionnaires/${id}/`,
  ]);
  const rawQuestions: any[] = Array.isArray(raw?.questions)
    ? raw.questions
    : raw?.preguntas ?? [];
  return {
    id: String(raw.id ?? id),
    title: raw.title ?? raw.nombre ?? "Sin título",
    version: raw.version ?? raw.vers ?? "v1",
    timezone: raw.timezone ?? raw.zona_horaria ?? "America/Bogota",
    questions: rawQuestions.map(normalizeQuestion),
  };
}

export async function upsertQuestionnaire(
  questionnaire: AdminQuestionnaire
): Promise<AdminQuestionnaire> {
  const payload = {
    id: questionnaire.id,
    title: questionnaire.title,
    version: questionnaire.version,
    timezone: questionnaire.timezone,
    questions: questionnaire.questions.map((q) => ({
      id: q.id,
      text: q.text,
      type: q.type,
      required: q.required,
      order: q.order,
      choices: q.choices
        ? q.choices.map((choice) => ({
            id: choice.id,
            text: choice.text,
            branch_to: choice.branch_to,
          }))
        : null,
      ...(q.file_mode ? { file_mode: q.file_mode } : {}),
      ...(q.semantic_tag ? { semantic_tag: q.semantic_tag } : {}),
    })),
  };

  const hasId = !!questionnaire.id;
  const paths = hasId
    ? [
        `${ADMIN_MGMT_PREFIX}/questionnaires/${questionnaire.id}/`,
        `${ADMIN_PREFIX}/cuestionarios/${questionnaire.id}/`,
        `${ADMIN_PREFIX}/questionnaires/${questionnaire.id}/`,
      ]
    : [
        `${ADMIN_MGMT_PREFIX}/questionnaires/`,
        `${ADMIN_PREFIX}/cuestionarios/`,
        `${ADMIN_PREFIX}/questionnaires/`,
      ];
  const method = hasId ? "PUT" : "POST";

  const saved = await apiTry<any>(paths, {
    method,
    body: JSON.stringify(payload),
  });

  return getQuestionnaire(String(saved?.id ?? questionnaire.id));
}

export async function duplicateQuestionnaire(id: string, newVersion?: string) {
  const body = newVersion ? { version: newVersion } : undefined;
  const res = await apiTry<any>(
    [
      `${ADMIN_MGMT_PREFIX}/questionnaires/${id}/duplicate/`,
      `${ADMIN_PREFIX}/cuestionarios/${id}/duplicar/`,
      `${ADMIN_PREFIX}/cuestionarios/${id}/duplicate/`,
      `${ADMIN_PREFIX}/questionnaires/${id}/duplicate/`,
    ],
    body
      ? { method: "POST", body: JSON.stringify(body) }
      : { method: "POST" }
  );
  return { id: String(res?.id ?? res?.uuid ?? id) };
}

export async function deleteQuestionnaire(id: string) {
  await apiTry<void>(
    [
      `${ADMIN_MGMT_PREFIX}/questionnaires/${id}/`,
      `${ADMIN_PREFIX}/cuestionarios/${id}/`,
      `${ADMIN_PREFIX}/questionnaires/${id}/`,
    ],
    { method: "DELETE" }
  );
}

export async function reorderQuestions(
  questionnaireId: string,
  orderedIds: string[]
): Promise<void> {
  const urls = [
    `${ADMIN_MGMT_PREFIX}/questionnaires/${questionnaireId}/reorder/`,
    `${ADMIN_MGMT_PREFIX}/questionnaires/${questionnaireId}/orden/`,
    `${ADMIN_PREFIX}/cuestionarios/${questionnaireId}/reorder/`,
    `${ADMIN_PREFIX}/cuestionarios/${questionnaireId}/orden/`,
    `${ADMIN_PREFIX}/questionnaires/${questionnaireId}/reorder/`,
  ];

  const payloads = [{ order: orderedIds }, { questions: orderedIds }, { ids: orderedIds }];

  let lastErr: unknown = null;
  for (const url of urls) {
    for (const payload of payloads) {
      try {
        await apiFetch<void>(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        return;
      } catch (err) {
        lastErr = err;
      }
    }
  }
  throw lastErr || new Error("No se pudo reordenar las preguntas");
}



