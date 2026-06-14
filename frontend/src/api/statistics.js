import { apiFetch, ensureApiSuccess } from "./http.js";

export async function getWhiteMothDailyStatistics() {
  const response = await apiFetch("/api/statistics/white-moth/daily");
  await ensureApiSuccess(response);
  return response.json();
}
