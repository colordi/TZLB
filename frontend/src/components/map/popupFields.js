const HOVER_PRIORITY_KEYS = [
  "点位名称",
  "位置名称",
  "location_name",
  "locationName",
  "名称",
  "name",
  "编号",
  "location_id",
];

const SURVEY_DATE_KEYS = ["调查日期", "survey_date", "report_time"];

export function buildPopupRows(columns = [], properties = {}) {
  return (columns || []).map((label) => {
    const value = properties?.[label];
    return [label, value === undefined || value === null || value === "" ? "-" : `${value}`];
  });
}

export function normalizeInsectCount(properties = {}) {
  const value =
    properties["总虫口数"] ??
    properties["虫口数"] ??
    properties.total_insect_count ??
    properties.total_insect ??
    0;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}

export function resolveFeatureSeverity(properties = {}) {
  let rawValue = "";
  if (typeof properties === "string") {
    rawValue = properties;
  } else if (properties) {
    rawValue =
      properties["危害程度"] ??
      properties["严重程度"] ??
      properties["等级"] ??
      properties["级别"] ??
      properties.severity ??
      properties.level ??
      "";
  }

  const normalized = String(rawValue || "").trim();

  if (normalized.includes("轻")) {
    return {
      key: "level1",
      color: "#68C17A",
      radius: 7,
      label: "轻",
    };
  }

  if (normalized.includes("中")) {
    return {
      key: "level2",
      color: "#F0C048",
      radius: 9,
      label: "中",
    };
  }

  if (normalized.includes("重")) {
    return {
      key: "level3",
      color: "#EC6D64",
      radius: 11,
      label: "重",
    };
  }

  return {
    key: "level0",
    color: "#FFFFFF",
    radius: 6,
    label: "白",
  };
}

export function resolveFeatureHoverLabel(columns = [], properties = {}) {
  const preferredColumns = (columns || []).filter((label) => /名称|name|编号/i.test(label));
  const preferredNameColumns = preferredColumns.filter((label) => /名称|name/i.test(label));
  const preferredCodeColumns = preferredColumns.filter((label) => !/名称|name/i.test(label));
  const builtinNameKeys = HOVER_PRIORITY_KEYS.filter((key) => /名称|name/i.test(key));
  const builtinCodeKeys = HOVER_PRIORITY_KEYS.filter((key) => !/名称|name/i.test(key));
  const candidates = [
    ...preferredNameColumns,
    ...builtinNameKeys,
    ...preferredCodeColumns,
    ...builtinCodeKeys,
  ];

  for (const key of candidates) {
    const value = properties?.[key];
    if (value !== undefined && value !== null && `${value}`.trim() !== "") {
      return `${value}`.trim();
    }
  }

  return "";
}

export function resolveSurveyStatus(properties = {}) {
  const rawValue =
    properties["调查状态"] ??
    properties.survey_status ??
    properties.status ??
    properties["状态"];
  const normalized = `${rawValue ?? ""}`.trim();

  if (normalized) {
    if (normalized.includes("中")) {
      return "in_progress";
    }
    if (normalized.includes("未") || normalized.includes("待")) {
      return "pending";
    }
    return "completed";
  }

  const hasSurveyDate = SURVEY_DATE_KEYS.some((key) => {
    const value = properties?.[key];
    return value !== undefined && value !== null && `${value}`.trim() !== "";
  });

  return hasSurveyDate ? "completed" : "pending";
}

export function buildSurveyStatusSummary(features = []) {
  return (features || []).reduce(
    (summary, feature) => {
      const status = resolveSurveyStatus(feature?.properties || {});
      summary[status] += 1;
      return summary;
    },
    {
      completed: 0,
      pending: 0,
      in_progress: 0,
    },
  );
}
