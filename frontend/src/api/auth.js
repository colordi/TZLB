import { apiFetch, ensureApiSuccess } from "./http.js";

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

export async function fetchCurrentUser() {
  const response = await apiFetch("/api/auth/me");

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
