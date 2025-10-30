/**
 * Utilidades de almacenamiento para autenticación.
 */
export const AUTH_TOKEN_KEY =
  process.env.NEXT_PUBLIC_AUTH_TOKEN_KEY || "auth:access_token";
const USERNAME_KEY =
  process.env.NEXT_PUBLIC_AUTH_USERNAME_KEY || "auth:username";
const STAFF_KEY =
  process.env.NEXT_PUBLIC_AUTH_IS_STAFF_KEY || "auth:is_staff";

export const AUTH_USERNAME_KEY = USERNAME_KEY;
export const AUTH_IS_STAFF_KEY = STAFF_KEY;

export function notifyAuthListeners() {
  if (typeof window === "undefined") return;
  try {
    window.dispatchEvent(new CustomEvent("auth:changed"));
  } catch {
    /* ignore */
  }
}

export function getAuthToken(): string | undefined {
  if (typeof localStorage === "undefined") return undefined;
  return localStorage.getItem(AUTH_TOKEN_KEY) || undefined;
}

export function setAuthToken(token: string) {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(AUTH_TOKEN_KEY, token);
  notifyAuthListeners();
}

export function purgeLegacyAuthArtifacts() {
  if (typeof document === "undefined") return;
  const kill = (name: string) =>
    (document.cookie = `${name}=; Path=/; Max-Age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax`);
  ["is_staff", "auth_username", "sessionid", "csrftoken", "auth_token"].forEach(
    kill
  );
}

export function clearAuthToken() {
  if (typeof localStorage !== "undefined") {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
    localStorage.removeItem(STAFF_KEY);
  }
  purgeLegacyAuthArtifacts();
  notifyAuthListeners();
}

export function isAuthenticated() {
  return !!getAuthToken();
}
