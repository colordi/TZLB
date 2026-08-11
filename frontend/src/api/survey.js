import { apiFetch, ensureApiSuccess } from "./http.js";
import { extractFilename } from "./filename.js";

export async function fetchSurveyCandidates({ date, pestType, year, generation, includeImages }) {
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
  if (includeImages === false) {
    search.set("include_images", "false");
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

export async function fetchPestTypes() {
  const response = await apiFetch("/api/survey/pest-types");
  await ensureApiSuccess(response);
  return response.json();
}

export async function downloadImportTemplate(pestType) {
  const search = new URLSearchParams({ pest_type: pestType });
  const response = await apiFetch(`/api/survey/import-template?${search.toString()}`);
  await ensureApiSuccess(response);

  return {
    blob: await response.blob(),
    filename: extractFilename(
      response.headers.get("content-disposition"),
      `${pestType}数据导入模板.xlsx`,
    ),
  };
}
