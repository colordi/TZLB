export class UnauthorizedError extends Error {
  constructor(message = "未登录或登录状态已失效") {
    super(message);
    this.name = "UnauthorizedError";
  }
}

let redirectingToLogin = false;

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
  return fetch(input, {
    credentials: "same-origin",
    ...init,
  });
}
