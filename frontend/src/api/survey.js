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

export async function uploadSurveyExcel({ file, dryRun = true }) {
  const search = new URLSearchParams({
    dry_run: dryRun ? "true" : "false",
  });
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiFetch(`/api/survey/excel-import?${search.toString()}`, {
    method: "POST",
    body: formData,
  });
  await ensureApiSuccess(response);
  return response.json();
}
