function extractFilename(contentDisposition) {
  if (!contentDisposition) {
    return "林业工作单.docx";
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

  return "林业工作单.docx";
}

async function parseError(response) {
  try {
    const payload = await response.json();
    return payload.detail || payload.error || "请求失败";
  } catch {
    return "请求失败";
  }
}

export async function generateWorkorder(payload) {
  const response = await fetch("/api/workorder/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return {
    blob: await response.blob(),
    filename: extractFilename(response.headers.get("content-disposition")),
  };
}
