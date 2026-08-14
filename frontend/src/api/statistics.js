import { apiFetch, ensureApiSuccess } from "./http.js";

export async function getWhiteMothDailyStatistics({ year, generation } = {}) {
  const params = new URLSearchParams();
  if (year !== undefined && year !== null && year !== "") {
    params.set("year", String(year));
  }
  if (generation !== undefined && generation !== null && generation !== "") {
    params.set("generation", generation);
  }
  const query = params.toString();
  const response = await apiFetch(`/api/statistics/white-moth/daily${query ? `?${query}` : ""}`);
  await ensureApiSuccess(response);
  return response.json();
}

export async function getWhiteMothGenerationSummary({ year } = {}) {
  const params = new URLSearchParams();
  if (year !== undefined && year !== null && year !== "") {
    params.set("year", String(year));
  }
  const query = params.toString();
  const response = await apiFetch(
    `/api/statistics/white-moth/generation-summary${query ? `?${query}` : ""}`,
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function getWhiteMothHostSummary({ year, generation, byGeneration } = {}) {
  const params = new URLSearchParams();
  if (year !== undefined && year !== null && year !== "") {
    params.set("year", String(year));
  }
  if (generation !== undefined && generation !== null && generation !== "") {
    params.set("generation", generation);
  }
  if (byGeneration) {
    params.set("by_generation", "true");
  }
  const query = params.toString();
  const response = await apiFetch(
    `/api/statistics/white-moth/host-summary${query ? `?${query}` : ""}`,
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function getWhiteMothLocalitySummary({
  year,
  generation,
  asOfDate,
  severePlantThreshold,
} = {}) {
  const params = new URLSearchParams();
  if (year !== undefined && year !== null && year !== "") {
    params.set("year", String(year));
  }
  if (generation !== undefined && generation !== null && generation !== "") {
    params.set("generation", generation);
  }
  if (asOfDate !== undefined && asOfDate !== null && asOfDate !== "") {
    params.set("as_of_date", asOfDate);
  }
  if (
    severePlantThreshold !== undefined &&
    severePlantThreshold !== null &&
    severePlantThreshold !== ""
  ) {
    params.set("severe_plant_threshold", String(severePlantThreshold));
  }
  const query = params.toString();
  const response = await apiFetch(
    `/api/statistics/white-moth/locality-summary${query ? `?${query}` : ""}`,
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function getOtherPestSummary({ year } = {}) {
  const params = new URLSearchParams();
  if (year !== undefined && year !== null && year !== "") {
    params.set("year", String(year));
  }
  const query = params.toString();
  const response = await apiFetch(
    `/api/statistics/other-pest/summary${query ? `?${query}` : ""}`,
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function getYangshuShiyeSummary({ year } = {}) {
  const params = new URLSearchParams();
  if (year !== undefined && year !== null && year !== "") {
    params.set("year", String(year));
  }
  const query = params.toString();
  const response = await apiFetch(
    `/api/statistics/yangshu-shiye/summary${query ? `?${query}` : ""}`,
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function getAshBorerSummary({ year } = {}) {
  const params = new URLSearchParams();
  if (year !== undefined && year !== null && year !== "") {
    params.set("year", String(year));
  }
  const query = params.toString();
  const response = await apiFetch(
    `/api/statistics/ash-borer/summary${query ? `?${query}` : ""}`,
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function getPoplarInchwormSummary({ year } = {}) {
  const params = new URLSearchParams();
  if (year !== undefined && year !== null && year !== "") {
    params.set("year", String(year));
  }
  const query = params.toString();
  const response = await apiFetch(
    `/api/statistics/poplar-inchworm/summary${query ? `?${query}` : ""}`,
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function getSophoraGenerationSummary({ year } = {}) {
  const params = new URLSearchParams();
  if (year !== undefined && year !== null && year !== "") {
    params.set("year", String(year));
  }
  const query = params.toString();
  const response = await apiFetch(
    `/api/statistics/sophora-inchworm/generation-summary${query ? `?${query}` : ""}`,
  );
  await ensureApiSuccess(response);
  return response.json();
}

export async function getSophoraLocalitySummary({ year, generation } = {}) {
  const params = new URLSearchParams();
  if (year !== undefined && year !== null && year !== "") {
    params.set("year", String(year));
  }
  if (generation !== undefined && generation !== null && generation !== "") {
    params.set("generation", generation);
  }
  const query = params.toString();
  const response = await apiFetch(
    `/api/statistics/sophora-inchworm/locality-summary${query ? `?${query}` : ""}`,
  );
  await ensureApiSuccess(response);
  return response.json();
}
