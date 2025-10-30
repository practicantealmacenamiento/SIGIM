import type { HistorialQuery } from "@/lib/api.historial";

export type Estado = "todos" | "completo" | "pendiente";
export type SortKey = HistorialQuery["sort"];
export type SortDir = HistorialQuery["dir"];
export type ActorTipo = "todos" | "proveedor" | "transportista";

export type ActorOption = {
  id: string;
  nombre: string;
  documento: string;
  tipo: "PROVEEDOR" | "TRANSPORTISTA" | "RECEPTOR" | string;
};

export type ViewMode = "cards" | "table";

export type HistorialFilters = {
  desde: string;
  hasta: string;
  estado: Estado;
  search: string;
  actorTipo: ActorTipo;
  actorInput: string;
  actorSel: ActorOption | null;
  sort: SortKey;
  dir: SortDir;
  page: number;
  pageSize: number;
  view: ViewMode;
  autoRefresh: boolean;
};

export const DEFAULT_FILTERS: HistorialFilters = {
  desde: "",
  hasta: "",
  estado: "completo",
  search: "",
  actorTipo: "todos",
  actorInput: "",
  actorSel: null,
  sort: "reciente",
  dir: "desc",
  page: 1,
  pageSize: 20,
  view: "cards",
  autoRefresh: false,
};

function parseActorSelection(params: URLSearchParams, actorTipo: ActorTipo): ActorOption | null {
  const id = params.get("actor_id");
  if (!id) return null;
  const tipo =
    params.get("actor_tipo_api") ||
    (actorTipo === "proveedor" ? "PROVEEDOR" : actorTipo === "transportista" ? "TRANSPORTISTA" : "");
  return {
    id,
    nombre: params.get("actor_name") || id,
    documento: "",
    tipo,
  };
}

export function createFiltersFromParams(paramsStr: string): HistorialFilters {
  const params = new URLSearchParams(paramsStr);
  const actorTipo = (params.get("actor_tipo") as ActorTipo) || "todos";
  return {
    desde: params.get("desde") || "",
    hasta: params.get("hasta") || "",
    estado: (params.get("estado") as Estado) || "completo",
    search: params.get("q") || "",
    actorTipo,
    actorInput: params.get("actor_text") || "",
    actorSel: parseActorSelection(params, actorTipo),
    sort: (params.get("sort") as SortKey) || "reciente",
    dir: (params.get("dir") as SortDir) || "desc",
    page: Math.max(1, Number(params.get("page") || 1)),
    pageSize: Math.max(1, Number(params.get("pageSize") || 20)),
    view: (params.get("view") as ViewMode) || "cards",
    autoRefresh: params.get("auto") === "1",
  };
}

export function filtersEqual(a: HistorialFilters, b: HistorialFilters) {
  const sameActor =
    (a.actorSel === null && b.actorSel === null) ||
    (a.actorSel !== null &&
      b.actorSel !== null &&
      a.actorSel.id === b.actorSel.id &&
      a.actorSel.nombre === b.actorSel.nombre &&
      a.actorSel.tipo === b.actorSel.tipo);
  return (
    a.desde === b.desde &&
    a.hasta === b.hasta &&
    a.estado === b.estado &&
    a.search === b.search &&
    a.actorTipo === b.actorTipo &&
    a.actorInput === b.actorInput &&
    sameActor &&
    a.sort === b.sort &&
    a.dir === b.dir &&
    a.page === b.page &&
    a.pageSize === b.pageSize &&
    a.view === b.view &&
    a.autoRefresh === b.autoRefresh
  );
}

export type FiltersAction =
  | { type: "merge"; patch: Partial<HistorialFilters>; resetPage?: boolean }
  | { type: "setPage"; page: number }
  | { type: "reset" }
  | { type: "hydrate"; payload: HistorialFilters };

export function filtersReducer(state: HistorialFilters, action: FiltersAction): HistorialFilters {
  switch (action.type) {
    case "merge": {
      const next: HistorialFilters = { ...state, ...action.patch };
      if (action.resetPage) next.page = 1;
      return next;
    }
    case "setPage":
      return { ...state, page: Math.max(1, action.page) };
    case "reset":
      return { ...DEFAULT_FILTERS };
    case "hydrate":
      return action.payload;
    default:
      return state;
  }
}
