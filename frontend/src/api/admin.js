import { apiFetch, ensureApiSuccess } from "./http.js";

/* ──────────────────────────────────────────
   Dashboard
   ────────────────────────────────────────── */

export async function fetchDashboardStats() {
  const response = await apiFetch("/api/admin/dashboard");
  await ensureApiSuccess(response);
  return response.json();
}

/* ──────────────────────────────────────────
   Layer Metadata
   ────────────────────────────────────────── */

export async function fetchLayers() {
  const response = await apiFetch("/api/admin/layers");
  await ensureApiSuccess(response);
  return response.json();
}

export async function updateLayers(items) {
  const response = await apiFetch("/api/admin/layers", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
  await ensureApiSuccess(response);
  return response.json();
}

/* ──────────────────────────────────────────
   Task View Builder — 任务图层构建器
   ────────────────────────────────────────── */

export async function fetchViewBuilderSources() {
  const response = await apiFetch("/api/admin/view-builder/sources");
  await ensureApiSuccess(response);
  return response.json();
}

export async function previewTaskView(payload) {
  const response = await apiFetch("/api/admin/view-builder/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await ensureApiSuccess(response);
  return response.json();
}

export async function createTaskView(payload) {
  const response = await apiFetch("/api/admin/view-builder/views", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await ensureApiSuccess(response);
  return response.json();
}

export async function deleteTaskView(viewName) {
  const response = await apiFetch(
    `/api/admin/view-builder/views/${encodeURIComponent(viewName)}`,
    { method: "DELETE" },
  );
  await ensureApiSuccess(response);
  return response.json();
}

/* ──────────────────────────────────────────
   User Management
   ────────────────────────────────────────── */

export async function fetchUsers() {
  const response = await apiFetch("/api/admin/users");
  await ensureApiSuccess(response);
  return response.json();
}

export async function createUser(payload) {
  const response = await apiFetch("/api/admin/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await ensureApiSuccess(response);
  return response.json();
}

export async function updateUser(userId, payload) {
  const response = await apiFetch(`/api/admin/users/${userId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await ensureApiSuccess(response);
  return response.json();
}

export async function deleteUser(userId) {
  const response = await apiFetch(`/api/admin/users/${userId}`, {
    method: "DELETE",
  });
  if (response.status === 204) {
    return;
  }
  await ensureApiSuccess(response);
}

export async function resetUserPassword(userId, newPassword) {
  const response = await apiFetch(`/api/admin/users/${userId}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_password: newPassword }),
  });
  await ensureApiSuccess(response);
  return response.json();
}

/* ──────────────────────────────────────────
   Operation Logs
   ────────────────────────────────────────── */

export async function fetchOperationLogs(params = {}) {
  const search = new URLSearchParams();
  const limit = params.limit ?? 100;
  const offset = params.offset ?? 0;
  search.set("limit", `${limit}`);
  search.set("offset", `${offset}`);
  const response = await apiFetch(`/api/admin/operation-logs?${search.toString()}`);
  await ensureApiSuccess(response);
  return response.json();
}

/* ──────────────────────────────────────────
   Storage Config — 素材存储配置
   ────────────────────────────────────────── */

export async function fetchStorageConfig() {
  const response = await apiFetch("/api/admin/storage-config");
  await ensureApiSuccess(response);
  return response.json();
}

export async function updateStorageConfig(payload) {
  const response = await apiFetch("/api/admin/storage-config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await ensureApiSuccess(response);
  return response.json();
}

export async function testStorageConnection(payload) {
  const response = await apiFetch("/api/admin/storage-config/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await ensureApiSuccess(response);
  return response.json();
}
