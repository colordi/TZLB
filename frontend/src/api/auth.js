import { apiFetch, ensureApiSuccess, shouldUseLocalDevAuthBypass } from "./http.js";

const LOCAL_DEV_USER = {
  id: 0,
  username: "local-dev",
  display_name: "本机测试用户",
  is_active: true,
  last_login_at: null,
};

function buildLocalDevUser() {
  return { ...LOCAL_DEV_USER };
}

export async function login(payload) {
  const response = await apiFetch("/api/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  await ensureApiSuccess(response, { redirectOnUnauthorized: false });

  return response.json();
}

export async function fetchCurrentUser(options = {}) {
  let response;
  try {
    response = await apiFetch("/api/auth/me");
  } catch (requestError) {
    if (shouldUseLocalDevAuthBypass(options.locationLike, options.env)) {
      return buildLocalDevUser();
    }
    throw requestError;
  }

  if (!response.ok && shouldUseLocalDevAuthBypass(options.locationLike, options.env)) {
    return buildLocalDevUser();
  }

  if (response.status === 401) {
    return null;
  }

  await ensureApiSuccess(response, { redirectOnUnauthorized: false });

  const payload = await response.json();
  return payload.user || null;
}

export async function logout() {
  const response = await apiFetch("/api/auth/logout", {
    method: "POST",
  });

  if (response.status === 401 || response.status === 204) {
    return;
  }

  await ensureApiSuccess(response, { redirectOnUnauthorized: false });
}
