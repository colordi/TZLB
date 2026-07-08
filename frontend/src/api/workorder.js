import { apiFetch, ensureApiSuccess } from "./http.js";
import { extractFilename } from "./filename.js";

export async function generateWorkorder(payload) {
  const response = await apiFetch("/api/workorder/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  await ensureApiSuccess(response);

  return {
    blob: await response.blob(),
    filename: extractFilename(response.headers.get("content-disposition"), "林业工作单.doc"),
  };
}

export async function generateWorkorderBatch(payload) {
  const response = await apiFetch("/api/workorder/generate-batch", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  await ensureApiSuccess(response);

  return {
    blob: await response.blob(),
    filename: extractFilename(response.headers.get("content-disposition"), "林业工作单.doc"),
  };
}

export async function uploadDateImageFolder({ folderName, files }) {
  const formData = new FormData();
  formData.append("folder_name", folderName);

  for (const file of files) {
    formData.append("files", file);
    formData.append("relative_paths", file.webkitRelativePath || `${folderName}/${file.name}`);
  }

  const response = await apiFetch("/api/workorder/date-image-folder", {
    method: "POST",
    body: formData,
  });
  await ensureApiSuccess(response);
  return response.json();
}
