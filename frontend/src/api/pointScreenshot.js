import { apiFetch, ensureApiSuccess } from "./http.js";

export async function listPointScreenshotStatus(pestType) {
  const response = await apiFetch(
    `/api/point-screenshots/status?pest_type=${encodeURIComponent(pestType)}`,
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function uploadPointScreenshot({ pestType, code, file }) {
  const formData = new FormData();
  formData.append("pest_type", pestType);
  formData.append("code", code);
  formData.append("file", file);

  const response = await apiFetch("/api/point-screenshots/upload", {
    method: "POST",
    body: formData,
  });
  await ensureApiSuccess(response);
  return response.json();
}

export async function deletePointScreenshot(pestType, code) {
  const response = await apiFetch(
    `/api/point-screenshots/?pest_type=${encodeURIComponent(pestType)}&code=${encodeURIComponent(code)}`,
    { method: "DELETE" },
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function fetchPointScreenshotBlob(pestType, code, { size = "full" } = {}) {
  const params = new URLSearchParams({
    pest_type: pestType,
    code,
    size,
  });
  const response = await apiFetch(`/api/point-screenshots/preview?${params.toString()}`);
  await ensureApiSuccess(response);
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
