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

/** 列出指定日期目录下的图片；传 pointCode 时只返回该点位的图片 */
export async function fetchPointDateImages({ surveyDate, pointCode }) {
  const search = new URLSearchParams({ survey_date: surveyDate });
  if (pointCode) {
    search.set("point_code", pointCode);
  }
  const response = await apiFetch(`/api/workorder/point-date-images?${search.toString()}`);
  await ensureApiSuccess(response);
  return response.json();
}

/** 上传图片到指定点位的日期目录，后端自动按“编号-序号”重命名 */
export async function uploadPointDateImages({ surveyDate, pointCode, files }) {
  const formData = new FormData();
  formData.append("survey_date", surveyDate);
  formData.append("point_code", pointCode);
  for (const file of files) {
    formData.append("files", file);
  }

  const response = await apiFetch("/api/workorder/point-date-images", {
    method: "POST",
    body: formData,
  });
  await ensureApiSuccess(response);
  return response.json();
}

export async function deletePointDateImage({ surveyDate, pointCode, fileName }) {
  const search = new URLSearchParams({ point_code: pointCode });
  const response = await apiFetch(
    `${buildPointDateImageUrl({ surveyDate, fileName })}?${search.toString()}`,
    { method: "DELETE" },
  );
  await ensureApiSuccess(response);
  return response.json();
}

export function buildPointDateImageUrl({ surveyDate, fileName }) {
  return `/api/workorder/point-date-images/${encodeURIComponent(surveyDate)}/${encodeURIComponent(fileName)}`;
}

/** 通过 apiFetch 拉取图片并返回 Object URL（本地免登场景 <img> 无法携带 bypass 头） */
export async function fetchPointDateImageBlob({ surveyDate, fileName }) {
  const response = await apiFetch(buildPointDateImageUrl({ surveyDate, fileName }));
  await ensureApiSuccess(response);
  return URL.createObjectURL(await response.blob());
}
