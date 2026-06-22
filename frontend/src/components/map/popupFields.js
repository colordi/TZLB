const HOVER_NAME_KEYS = [
  "点位名称",
  "位置名称",
  "location_name",
  "locationName",
  "名称",
  "name",
];

const HOVER_IDENTIFIER_KEYS = [
  "编号",
  "点位编号",
  "location_id",
  "locationId",
  "id",
];

const POINT_LABEL_KEYS = ["编号", "点位编号", "location_id", "locationId", "id"];

const SURVEY_DATE_KEYS = ["调查日期", "survey_date", "report_time"];

const SEVERITY_FIELD_KEYS = [
  "危害程度",
  "严重程度",
  "等级",
  "级别",
  "severity",
  "level",
];
const PARCEL_STATUS_FIELD_KEYS = ["地块状态", "parcel_status", "parcelStatus"];

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

export function hasFeatureSeverityField(fields = []) {
  const severityFieldKeys = new Set(SEVERITY_FIELD_KEYS.map((field) => field.toLowerCase()));

  return (fields || []).some((field) => {
    const normalizedField = `${field ?? ""}`.trim();
    return severityFieldKeys.has(normalizedField.toLowerCase());
  });
}

export function hasFeatureParcelStatusField(fields = []) {
  const parcelStatusFieldKeys = new Set(
    PARCEL_STATUS_FIELD_KEYS.map((field) => field.toLowerCase()),
  );

  return (fields || []).some((field) => {
    const normalizedField = `${field ?? ""}`.trim();
    return parcelStatusFieldKeys.has(normalizedField.toLowerCase());
  });
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

  if (
    !normalized ||
    normalized === "无" ||
    normalized === "白" ||
    normalized === "无需防治"
  ) {
    return {
      key: "level0",
      color: "#ffffff",
      radius: 7,
      label: "无",
    };
  }

  if (normalized.includes("轻")) {
    return {
      key: "level1",
      color: "#0033ff",
      radius: 7,
      label: "轻",
    };
  }

  if (normalized.includes("中")) {
    return {
      key: "level2",
      color: "#fbff05",
      radius: 9,
      label: "中",
    };
  }

  if (normalized.includes("重")) {
    return {
      key: "level3",
      color: "#ff0000",
      radius: 11,
      label: "重",
    };
  }

  return {
    key: "level0",
    color: "#ffffff",
    radius: 7,
    label: "无",
  };
}

export function resolveFeatureParcelStatus(properties = {}) {
  const rawValue =
    properties["地块状态"] ??
    properties.parcel_status ??
    properties.parcelStatus ??
    "";
  const normalized = `${rawValue ?? ""}`.trim();

  if (normalized === "调查") {
    return {
      key: "parcel-surveyed",
      color: "#ff0000",
      radius: 8,
      label: "调查",
    };
  }

  if (normalized === "伐除") {
    return {
      key: "parcel-removed",
      color: "#000000",
      radius: 8,
      label: "伐除",
    };
  }

  return {
    key: "parcel-default",
    color: "#ffffff",
    radius: 8,
    label: "其他",
  };
}

export function resolveFeatureHoverLabel(columns = [], properties = {}, options = {}) {
  const preferredColumns = (columns || []).filter((label) =>
    /名称|name|编号|id/i.test(label),
  );
  const preferredNameColumns = preferredColumns.filter((label) => /名称|name/i.test(label));
  const preferredCodeColumns = preferredColumns.filter((label) => !/名称|name/i.test(label));
  const candidates = options.preferIdentifier
    ? [
        ...HOVER_IDENTIFIER_KEYS,
        ...preferredCodeColumns,
        ...preferredNameColumns,
        ...HOVER_NAME_KEYS,
      ]
    : [
        ...preferredNameColumns,
        ...HOVER_NAME_KEYS,
        ...preferredCodeColumns,
        ...HOVER_IDENTIFIER_KEYS,
      ];

  for (const key of Array.from(new Set(candidates))) {
    const value = properties?.[key];
    if (value !== undefined && value !== null && `${value}`.trim() !== "") {
      return `${value}`.trim();
    }
  }

  return "";
}

export function resolveFeaturePointLabel(properties = {}) {
  for (const key of POINT_LABEL_KEYS) {
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
