import { apiFetch, ensureApiSuccess } from "./http.js";

export async function fetchSurveyCandidates(date) {
  const search = new URLSearchParams();
  if (date && `${date}`.trim() !== "") {
    search.set("date", date);
  }

  const query = search.toString();
  const response = await apiFetch(`/api/survey/candidates${query ? `?${query}` : ""}`);
  await ensureApiSuccess(response);
  return response.json();
}
