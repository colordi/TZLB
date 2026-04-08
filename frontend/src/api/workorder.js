import { apiFetch, ensureApiSuccess } from "./http.js";

function extractFilename(contentDisposition) {
  if (!contentDisposition) {
    return "林业工作单.doc";
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

  return "林业工作单.doc";
}

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
    filename: extractFilename(response.headers.get("content-disposition")),
  };
}
