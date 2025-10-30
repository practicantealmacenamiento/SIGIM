// Reexporta todo para consumo interno.

export {
  AUTH_TOKEN_KEY,
  AUTH_USERNAME_KEY,
  AUTH_IS_STAFF_KEY,
  getAuthToken,
  setAuthToken,
  notifyAuthListeners,
  purgeLegacyAuthArtifacts,
  clearAuthToken,
  isAuthenticated,
} from "./auth-storage";

export { installGlobalAuthFetch, fetchWhoAmI, adminLogin } from "./auth";

export {
  createQuestionnaire,
  listQuestionnaires,
  getQuestionnaire,
  upsertQuestionnaire,
  duplicateQuestionnaire,
  deleteQuestionnaire,
  reorderQuestions,
} from "./questionnaires";

export {
  adminListActors,
  adminCreateActor,
  adminUpdateActor,
  adminDeleteActor,
  listActors,
} from "./actors";

export { listAdminUsers, upsertAdminUser, deleteAdminUser } from "./users";

export type {
  ActorTipo,
  AdminChoice,
  AdminQuestionType,
  AdminQuestion,
  AdminQuestionnaire,
  AdminUser,
  WhoAmI,
  Actor,
  Paginated,
} from "./types";

