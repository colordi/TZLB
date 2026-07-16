import { apiFetch, ensureApiSuccess } from "./http.js";

export async function listMapViews() {
  const response = await apiFetch("/api/map/views");
  await ensureApiSuccess(response);
  return response.json();
}

export async function listReferenceLayers() {
  const response = await apiFetch("/api/map/reference-layers");
  await ensureApiSuccess(response);
  return response.json();
}

export async function fetchReferenceLayer(name, options = {}) {
  const search = buildMapQueryParams({}, options);
  const query = search.toString();
  const response = await apiFetch(
    `/api/map/reference-layers/${encodeURIComponent(name)}${query ? `?${query}` : ""}`,
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function fetchWhiteMothSiteCodeRules() {
  const response = await apiFetch("/api/map/white-moth-sites/code-rules");
  await ensureApiSuccess(response);
  return response.json();
}

export async function fetchWhiteMothSiteCodeHint(prefix) {
  const search = new URLSearchParams();
  search.set("prefix", `${prefix || ""}`.trim().toUpperCase());
  const response = await apiFetch(
    `/api/map/white-moth-sites/code-hint?${search.toString()}`,
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function fetchMapFilterOptions(name) {
  const response = await apiFetch(
    `/api/map/views/${encodeURIComponent(name)}/filter-options`,
  );
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

export async function deleteWhiteMothSiteCheck(code) {
  const response = await apiFetch(
    `/api/map/white-moth-sites/${encodeURIComponent(code)}/delete-check`,
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function deleteWhiteMothSite(code) {
  const response = await apiFetch(
    `/api/map/white-moth-sites/${encodeURIComponent(code)}`,
    {
      method: "DELETE",
    },
  );
  await ensureApiSuccess(response);
  return response.json();
}

function appendBbox(search, bbox) {
  if (!bbox) {
    return;
  }

  const values = Array.isArray(bbox)
    ? bbox
    : [bbox.minLng, bbox.minLat, bbox.maxLng, bbox.maxLat];
  if (
    values.length === 4 &&
    values.every((item) => Number.isFinite(Number(item)))
  ) {
    search.set("bbox", values.map((item) => `${Number(item)}`).join(","));
  }
}

function buildMapQueryParams(filters = {}, options = {}) {
  const search = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    const values = Array.isArray(value) ? value : [value];
    values.forEach((item) => {
      if (item !== undefined && item !== null && `${item}`.trim() !== "") {
        search.append(key, `${item}`.trim());
      }
    });
  });
  appendBbox(search, options.bbox);
  if (options.limit !== undefined && options.limit !== null) {
    search.set("limit", `${options.limit}`);
  }
  return search;
}

export async function fetchMapView(name, filters = {}, options = {}) {
  const search = buildMapQueryParams(filters, options);
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
