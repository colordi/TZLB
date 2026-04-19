export class UnauthorizedError extends Error {
  constructor(message = "未登录或登录状态已失效") {
    super(message);
    this.name = "UnauthorizedError";
  }
}

export const LOCAL_AUTH_BYPASS_HEADER = "X-TZLB-Local-Auth-Bypass";

let redirectingToLogin = false;

function normalizeHostname(hostname) {
  return String(hostname || "")
    .trim()
    .replace(/^\[|\]$/g, "")
    .toLowerCase();
}

function getCurrentPath(locationLike) {
  if (!locationLike) {
    return "";
  }

  return `${locationLike.pathname || ""}${locationLike.search || ""}${locationLike.hash || ""}`;
}

export function buildLoginRedirectPath(locationLike) {
  const currentPath = getCurrentPath(locationLike);
  if (!currentPath || locationLike?.pathname === "/login") {
    return "/login";
  }

  const search = new URLSearchParams({
    redirect: currentPath,
  });
  return `/login?${search.toString()}`;
}

export function redirectToLogin(locationLike = globalThis.window?.location) {
  if (!locationLike || locationLike.pathname === "/login" || redirectingToLogin) {
    return;
  }

  const targetPath = buildLoginRedirectPath(locationLike);
  redirectingToLogin = true;
  locationLike.replace(targetPath);
}

export function resetUnauthorizedRedirectState() {
  redirectingToLogin = false;
}

export function isUnauthorizedError(error) {
  return error instanceof UnauthorizedError || error?.name === "UnauthorizedError";
}

export function isLocalhostHostname(hostname) {
  const normalizedHostname = normalizeHostname(hostname);
  return (
    normalizedHostname === "localhost" ||
    normalizedHostname === "127.0.0.1" ||
    normalizedHostname === "::1"
  );
}

export function shouldAttachLocalAuthBypass(locationLike = globalThis.window?.location) {
  return isLocalhostHostname(locationLike?.hostname);
}

async function parseError(response) {
  try {
    const payload = await response.json();
    return payload.detail || payload.error || "请求失败";
  } catch {
    return "请求失败";
  }
}

export async function ensureApiSuccess(response, options = {}) {
  if (response.ok) {
    return response;
  }

  const message = await parseError(response);
  if (response.status === 401) {
    if (options.redirectOnUnauthorized !== false) {
      redirectToLogin(options.locationLike);
    }
    throw new UnauthorizedError(message);
  }

  throw new Error(message);
}

export function apiFetch(input, init = {}) {
  const headers = new Headers(init.headers || {});
  if (shouldAttachLocalAuthBypass()) {
    headers.set(LOCAL_AUTH_BYPASS_HEADER, "1");
  }

  return fetch(input, {
    credentials: "same-origin",
    ...init,
    headers,
  });
}
