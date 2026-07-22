import { apiFetch, ensureApiSuccess } from "./http.js";

const BASE = "/api/data-manager";

function encodeTablePath(schemaName, tableName) {
  return `${BASE}/tables/${encodeURIComponent(schemaName)}/${encodeURIComponent(tableName)}`;
}

export async function fetchManageableTables() {
  const response = await apiFetch(`${BASE}/tables`);
  await ensureApiSuccess(response);
  return response.json();
}

export async function fetchTableColumns(schemaName, tableName) {
  const response = await apiFetch(`${encodeTablePath(schemaName, tableName)}/columns`);
  await ensureApiSuccess(response);
  return response.json();
}

export async function fetchTableRows(schemaName, tableName, params = {}) {
  const search = new URLSearchParams();
  search.set("page", `${params.page ?? 1}`);
  search.set("page_size", `${params.pageSize ?? 20}`);
  if (params.sort) {
    search.set("sort", params.sort);
  }
  if (params.filters && Object.keys(params.filters).length > 0) {
    search.set("filters", JSON.stringify(params.filters));
  }
  const response = await apiFetch(
    `${encodeTablePath(schemaName, tableName)}/rows?${search.toString()}`,
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function createTableRow(schemaName, tableName, values) {
  const response = await apiFetch(`${encodeTablePath(schemaName, tableName)}/rows`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ values }),
  });
  await ensureApiSuccess(response);
  return response.json();
}

export async function updateTableRow(schemaName, tableName, pk, values) {
  const response = await apiFetch(`${encodeTablePath(schemaName, tableName)}/rows`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pk, values }),
  });
  await ensureApiSuccess(response);
  return response.json();
}

export async function deleteTableRow(schemaName, tableName, pk) {
  const response = await apiFetch(`${encodeTablePath(schemaName, tableName)}/rows`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pk }),
  });
  await ensureApiSuccess(response);
  return response.json();
}

export async function fetchChangeLogs(params = {}) {
  const search = new URLSearchParams();
  search.set("limit", `${params.limit ?? 50}`);
  search.set("offset", `${params.offset ?? 0}`);
  if (params.schemaName) {
    search.set("schema_name", params.schemaName);
  }
  if (params.tableName) {
    search.set("table_name", params.tableName);
  }
  const response = await apiFetch(`${BASE}/change-logs?${search.toString()}`);
  await ensureApiSuccess(response);
  return response.json();
}
