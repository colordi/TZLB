import { apiFetch, ensureApiSuccess } from "./http.js";

function extractFilename(contentDisposition, fallback) {
  if (!contentDisposition) {
    return fallback;
  }

  const starred = /filename\*\s*=\s*([^;]+)/i.exec(contentDisposition);
  if (starred?.[1]) {
    const rawValue = starred[1].trim().replace(/^["']|["']$/g, "");
    const matched = /^([^']*)'[^']*'(.*)$/.exec(rawValue);
    const encodedPart = matched ? matched[2] : rawValue;
    try {
      return decodeURIComponent(encodedPart);
    } catch {
      return encodedPart;
    }
  }

  const plain = /filename\s*=\s*([^;]+)/i.exec(contentDisposition);
  if (plain?.[1]) {
    return plain[1].trim().replace(/^["']|["']$/g, "");
  }

  return fallback;
}

async function buildDownloadResult(response, fallbackFilename) {
  await ensureApiSuccess(response);
  return {
    blob: await response.blob(),
    filename: extractFilename(response.headers.get("content-disposition"), fallbackFilename),
  };
}

export async function listPestExportTypes() {
  const response = await apiFetch("/api/data-export/pest-types");
  await ensureApiSuccess(response);
  return response.json();
}

export async function downloadPestTypeExport(pestType, { year, generation } = {}) {
  const params = new URLSearchParams();
  if (year) params.set("year", year);
  if (generation) params.set("generation", generation);
  const query = params.toString();
  const response = await apiFetch(
    `/api/data-export/pest/${encodeURIComponent(pestType)}/download${query ? "?" + query : ""}`,
  );
  return buildDownloadResult(response, `${pestType}数据导出.xlsx`);
}
