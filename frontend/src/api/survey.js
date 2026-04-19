import { apiFetch, ensureApiSuccess } from "./http.js";

export async function fetchSurveyCandidates({ date, pestType }) {
  const search = new URLSearchParams();
  if (date && `${date}`.trim() !== "") {
    search.set("date", date);
  }
  if (pestType && `${pestType}`.trim() !== "") {
    search.set("pest_type", pestType);
  }

  const query = search.toString();
  const response = await apiFetch(`/api/survey/candidates${query ? `?${query}` : ""}`);
  await ensureApiSuccess(response);
  return response.json();
}
