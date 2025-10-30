import { apiFetch } from "@/lib/http";
import type { UUID } from "@/types/form";

export type SubmissionRow = {
  id: UUID;
  placa_vehiculo: string | null;
  regulador_id: UUID | null;
  fecha_cierre: string | null;
  muelle: string | null;
};

function extraerMuelle(answers: any[] | undefined | null): string | null {
  if (!Array.isArray(answers)) return null;

  const norm = (s: string) =>
    (s || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();

  const ts = (a: any) => {
    const t =
      Date.parse(a?.timestamp ?? "") ||
      Date.parse(a?.created_at ?? "") ||
      Date.parse(a?.updated_at ?? "");
    return Number.isFinite(t) ? t : 0;
  };

  const ordenadas = [...answers].sort((a, b) => ts(b) - ts(a));

  for (const a of ordenadas) {
    const q = a?.question || a?.question_data || {};
    const tag = String(q?.semantic_tag ?? "").toLowerCase().trim();
    const qtext = norm(String(q?.text ?? q?.label ?? ""));

    const contieneMuelle = tag === "muelle" || qtext.includes("muelle");
    if (contieneMuelle) {
      const choiceText =
        a?.answer_choice?.text ??
        a?.answer_choice?.label ??
        a?.choice?.text ??
        a?.choice_label ??
        null;

      const text = a?.answer_text ?? a?.text ?? null;
      const respuesta = (choiceText ?? text ?? "").toString().trim();
      return respuesta || null;
    }
  }
  return null;
}

export async function listarFase1Finalizados(params: {
  search?: string;
  page?: number;
  pageSize?: number;
}): Promise<{ results: SubmissionRow[]; count: number }> {
  const { search = "", page = 1, pageSize = 20 } = params;

  const query = new URLSearchParams({
    tipo_fase: "entrada",
    solo_finalizados: "1",
    solo_pendientes_fase2: "1",
  });
  if (search.trim()) query.set("placa_vehiculo", search.trim());

  const endpoint = `submissions/${(() => {
    const qs = query.toString();
    return qs ? `?${qs}` : "";
  })()}`;

  const data = await apiFetch<any>(endpoint, { timeoutMs: 25000 });
  const list = Array.isArray(data) ? data : data.results ?? [];
  const count =
    typeof data?.count === "number" ? data.count : Array.isArray(list) ? list.length : 0;

  const mapped: SubmissionRow[] = list.map((s: any) => ({
    id: s.id,
    placa_vehiculo: s.placa_vehiculo ?? null,
    regulador_id: s.regulador_id ?? null,
    fecha_cierre: s.fecha_cierre ?? null,
    muelle: extraerMuelle(s.answers),
  }));

  const start = Math.max(0, (page - 1) * pageSize);
  const end = start + pageSize;
  return { results: mapped.slice(start, end), count };
}

export async function buscarFase2PorPlaca(placa: string): Promise<SubmissionRow | null> {
  const params = new URLSearchParams({
    tipo_fase: "salida",
    incluir_borradores: "1",
  });
  if (placa.trim()) params.set("placa_vehiculo", placa.trim());

  const endpoint = `submissions/${(() => {
    const qs = params.toString();
    return qs ? `?${qs}` : "";
  })()}`;

  const data = await apiFetch<any>(endpoint, { timeoutMs: 25000 });
  const list = Array.isArray(data) ? data : data.results ?? [];
  const draft = list.find((s: any) => s.finalizado === false) || null;

  return draft
    ? {
        id: draft.id,
        placa_vehiculo: draft.placa_vehiculo ?? null,
        regulador_id: draft.regulador_id ?? null,
        fecha_cierre: draft.fecha_cierre ?? null,
        muelle: extraerMuelle(draft.answers) ?? null,
      }
    : null;
}

export async function crearSubmissionFase2(payload: {
  questionnaire_id_fase2: UUID;
  placa_vehiculo: string;
  regulador_id?: UUID | null;
}): Promise<SubmissionRow> {
  const body = {
    questionnaire_id: payload.questionnaire_id_fase2,
    tipo_fase: "salida",
    placa_vehiculo: payload.placa_vehiculo,
    regulador_id: payload.regulador_id ?? null,
  };

  const data = await apiFetch<any>("submissions/", {
    method: "POST",
    json: body,
    timeoutMs: 25000,
  });

  return {
    id: data.id,
    placa_vehiculo: data.placa_vehiculo ?? null,
    regulador_id: data.regulador_id ?? null,
    fecha_cierre: data.fecha_cierre ?? null,
    muelle: null,
  };
}

