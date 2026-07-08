import { apiFetch, ensureApiSuccess } from "./http.js";
import { extractFilename } from "./filename.js";

export async function fetchSurveyCandidates({ date, pestType, year, generation }) {
  const search = new URLSearchParams();
  if (date && `${date}`.trim() !== "") {
    search.set("date", date);
  }
  if (pestType && `${pestType}`.trim() !== "") {
    search.set("pest_type", pestType);
  }
  if (year) {
    search.set("year", year);
  }
  if (generation) {
    search.set("generation", generation);
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

export async function downloadImportTemplate() {
  const response = await apiFetch("/api/survey/import-template");
  await ensureApiSuccess(response);

  return {
    blob: await response.blob(),
    filename: extractFilename(
      response.headers.get("content-disposition"),
      "林业调查数据导入模板.xlsx",
    ),
  };
}
