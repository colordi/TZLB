import { apiFetch, ensureApiSuccess } from "./http.js";

export async function getWhiteMothDailyStatistics({ year, generation } = {}) {
  const params = new URLSearchParams();
  if (year !== undefined && year !== null && year !== "") {
    params.set("year", String(year));
  }
  if (generation !== undefined && generation !== null && generation !== "") {
    params.set("generation", generation);
  }
  const query = params.toString();
  const response = await apiFetch(`/api/statistics/white-moth/daily${query ? `?${query}` : ""}`);
  await ensureApiSuccess(response);
  return response.json();
}

export async function getWhiteMothGenerationSummary() {
  const response = await apiFetch("/api/statistics/white-moth/generation-summary");
  await ensureApiSuccess(response);
  return response.json();
}
