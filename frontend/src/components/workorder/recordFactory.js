import { getPestConfig } from "./pestRegistry.js";
import { FIELD_DEFINITIONS } from "./fieldVisibility.js";

export function getTodayDate() {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function normalizeDate(value) {
  const raw = `${value ?? ""}`.trim();
  if (!raw) {
    return "";
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
    return raw;
  }

  let matched = raw.match(/^(\d{4})[\/.\-](\d{1,2})[\/.\-](\d{1,2})/);
  if (matched) {
    const [, year, month, day] = matched;
    return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
  }

  matched = raw.match(/^(\d{1,2})[\/.\-](\d{1,2})[\/.\-](\d{4})/);
  if (matched) {
    const [, month, day, year] = matched;
    return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
  }

  const numeric = Number(raw);
  if (Number.isFinite(numeric) && numeric > 30000 && numeric < 60000) {
    const excelEpoch = new Date(1899, 11, 30);
    const date = new Date(excelEpoch.getTime() + numeric * 24 * 60 * 60 * 1000);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  }

  const parsed = new Date(raw);
  if (!Number.isNaN(parsed.getTime())) {
    return `${parsed.getFullYear()}-${String(parsed.getMonth() + 1).padStart(2, "0")}-${String(parsed.getDate()).padStart(2, "0")}`;
  }

  return raw;
}

export function normalizeInputValue(field, value) {
  const raw = `${value ?? ""}`.trim();
  if (field.type === "date") {
    return normalizeDate(raw);
  }
  if (field.type === "number") {
    if (!raw) {
      return "";
    }
    const numeric = Number(raw);
    return Number.isFinite(numeric) ? `${numeric}` : raw;
  }
  return raw;
}

let recordUidSeed = 0;

export function createRecordUid() {
  recordUidSeed += 1;
  return `rec-${recordUidSeed}`;
}

export function createEmptyRecord(pestType) {
  return normalizeRecordForPest(
    {
      __uid: createRecordUid(),
      survey_date: getTodayDate(),
      region: "",
      locality: "",
      location_id: "",
      location_name: "",
      occurrence_position: "",
      total_insect_count: "",
      damage_level: "",
      pest_name: "",
      host_plant: "",
      green_space_type: "",
      pest_hosts: "",
      damaged_plant_count: "",
      web_nest_count: "",
      description: "",
      note: "",
      plot_type: "",
      report_time: getTodayDate(),
      images: [],
    },
    pestType,
  );
}

export function normalizeRecordForPest(record, pestType) {
  const config = getPestConfig(pestType);
  const next = {
    __uid: record.__uid || createRecordUid(),
    survey_date: record.survey_date || getTodayDate(),
    region: record.region || config.defaultRegion,
    locality: record.locality || record.town_or_street || "",
    location_id: record.location_id || "",
    location_name: record.location_name || "",
    occurrence_position: record.occurrence_position || "",
    total_insect_count: record.total_insect_count ?? "",
    damage_level: record.damage_level || "",
    pest_name: record.pest_name || "",
    host_plant: record.host_plant || "",
    green_space_type: record.green_space_type || "",
    pest_hosts: record.pest_hosts || "",
    damaged_plant_count: record.damaged_plant_count ?? "",
    web_nest_count: record.web_nest_count ?? "",
    description: record.description || "",
    note: record.note || "",
    plot_type: record.plot_type || "",
    report_time: record.report_time || getTodayDate(),
    images: Array.isArray(record.images) ? record.images.slice(0, 4) : [],
  };

  Object.entries(config.recordDefaults || {}).forEach(([key, value]) => {
    if (!`${next[key] ?? ""}`.trim()) {
      next[key] = value;
    }
  });
  Object.assign(next, config.recordOverrides || {});

  return next;
}

function normalizeOptionalInteger(value) {
  const raw = `${value ?? ""}`.trim();
  if (!raw) {
    return null;
  }

  const numeric = Number(raw);
  return Number.isFinite(numeric) ? numeric : raw;
}

function normalizePayloadValue(key, value, config) {
  if (key === "images") {
    return Array.isArray(value) ? value.slice(0, 4) : [];
  }
  if (key === "survey_date" || FIELD_DEFINITIONS[key]?.type === "date") {
    return normalizeDate(value);
  }
  if ((config.numberFieldKeys || []).includes(key)) {
    return normalizeOptionalInteger(value);
  }
  return `${value ?? ""}`.trim();
}

export function toPayloadRecord(record, pestType) {
  const config = getPestConfig(pestType);
  const normalized = normalizeRecordForPest(record, pestType);

  return Object.fromEntries(
    config.payloadFieldKeys.map((key) => [
      key,
      normalizePayloadValue(key, normalized[key], config),
    ]),
  );
}
