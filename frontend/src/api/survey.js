async function parseError(response) {
  try {
    const payload = await response.json();
    return payload.detail || payload.error || "请求失败";
  } catch {
    return "请求失败";
  }
}

export async function fetchSurveyCandidates(date) {
  const search = new URLSearchParams();
  if (date && `${date}`.trim() !== "") {
    search.set("date", date);
  }

  const query = search.toString();
  const response = await fetch(`/api/survey/candidates${query ? `?${query}` : ""}`);
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}
