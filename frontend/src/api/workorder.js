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

/** 创建批量导出任务，返回 job_id 供进度轮询 */
export async function startWorkorderBatchJob(payload) {
  const response = await apiFetch("/api/workorder/generate-batch-jobs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  await ensureApiSuccess(response);
  return response.json();
}

/** 查询批量导出任务真实进度 */
export async function getWorkorderBatchJobStatus(jobId) {
  const response = await apiFetch(`/api/workorder/generate-batch-jobs/${encodeURIComponent(jobId)}`);
  await ensureApiSuccess(response);
  return response.json();
}

/** 下载已完成的批量导出文件 */
export async function downloadWorkorderBatchJob(jobId) {
  const response = await apiFetch(
    `/api/workorder/generate-batch-jobs/${encodeURIComponent(jobId)}/download`,
  );
  await ensureApiSuccess(response);

  return {
    blob: await response.blob(),
    filename: extractFilename(response.headers.get("content-disposition"), "批量导出.zip"),
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
