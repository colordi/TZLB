import { apiFetch, ensureApiSuccess } from "./http.js";

export async function listMapViews() {
  const response = await apiFetch("/api/map/views");
  await ensureApiSuccess(response);
  return response.json();
}

export async function fetchWhiteMothSiteCodeRules() {
  const response = await apiFetch("/api/map/white-moth-sites/code-rules");
  await ensureApiSuccess(response);
  return response.json();
}

export async function createWhiteMothSite(payload) {
  const response = await apiFetch("/api/map/white-moth-sites", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  await ensureApiSuccess(response);
  return response.json();
}

export async function fetchMapView(name, filters = {}) {
  const search = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    const values = Array.isArray(value) ? value : [value];
    values.forEach((item) => {
      if (item !== undefined && item !== null && `${item}`.trim() !== "") {
        search.append(key, `${item}`.trim());
      }
    });
  });

  const query = search.toString();
  const response = await apiFetch(
    `/api/map/views/${encodeURIComponent(name)}${query ? `?${query}` : ""}`,
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function fetchAdminBoundary() {
  const response = await apiFetch("/api/map/layers/admin-boundary");
  await ensureApiSuccess(response);
  return response.json();
}
