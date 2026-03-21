async function parseError(response) {
  try {
    const payload = await response.json();
    return payload.detail || payload.error || "请求失败";
  } catch {
    return "请求失败";
  }
}

export async function listMapViews() {
  const response = await fetch("/api/map/views");
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}

export async function fetchMapView(name, filters = {}) {
  const search = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && `${value}`.trim() !== "") {
      search.set(key, value);
    }
  });

  const query = search.toString();
  const response = await fetch(`/api/map/views/${encodeURIComponent(name)}${query ? `?${query}` : ""}`);
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}

export async function fetchMapFilterOptions(name) {
  const response = await fetch(`/api/map/views/${encodeURIComponent(name)}/filter-options`);
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}

export async function fetchAdminBoundary() {
  const response = await fetch("/api/map/layers/admin-boundary");
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}
