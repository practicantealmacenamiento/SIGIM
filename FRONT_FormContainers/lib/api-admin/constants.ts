/**
 * Constantes base utilizadas por el cliente administrativo.
 */
const DEFAULT_API_PORT = 8000;

function trimEndSlash(value: string) {
  return value.replace(/\/+$/, "");
}

const API_BASE =
  (typeof window !== "undefined" &&
    (process.env.NEXT_PUBLIC_API_URL || "").toString().replace(/\/$/, "")) ||
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:${DEFAULT_API_PORT}`
    : `http://127.0.0.1:${DEFAULT_API_PORT}`);

const ADMIN_PREFIX = (process.env.NEXT_PUBLIC_ADMIN_PREFIX || "/api/v1").replace(
  /\/$/,
  ""
);

const AUTH_PREFIX = (process.env.NEXT_PUBLIC_AUTH_PREFIX || "/api/v1").replace(
  /\/$/,
  ""
);

const ADMIN_MGMT_PREFIX = (
  process.env.NEXT_PUBLIC_ADMIN_MGMT_PREFIX || "/api/v1/management"
).replace(/\/$/, "");

export {
  DEFAULT_API_PORT,
  API_BASE,
  ADMIN_PREFIX,
  AUTH_PREFIX,
  ADMIN_MGMT_PREFIX,
  trimEndSlash,
};
