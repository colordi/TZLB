export const PEST_OPTIONS = [
  { value: "春尺蠖", label: "春尺蠖" },
  { value: "国槐尺蠖", label: "国槐尺蠖" },
  { value: "其他害虫", label: "其他害虫" },
];

export const CONTROL_TYPE_OPTIONS = [
  { value: "春尺蠖防治", label: "春尺蠖防治" },
  { value: "国槐尺蠖防治", label: "国槐尺蠖防治" },
  { value: "美国白蛾防治", label: "美国白蛾防治" },
];

const DEFAULT_CONTROL_TYPE_BY_PEST = {
  春尺蠖: "春尺蠖防治",
  国槐尺蠖: "国槐尺蠖防治",
  其他害虫: "美国白蛾防治",
};

const CONTROL_TASK_OPTIONS_BY_PEST = {
  春尺蠖: [
    { value: "2026春尺蠖防治", label: "2026春尺蠖防治" },
  ],
  国槐尺蠖: [],
  其他害虫: [],
};

export const REQUIRED_FIELD_KEYS = [
  "survey_date",
  "town_or_street",
  "location_id",
  "location_name",
  "description",
];

const FIELD_DEFINITIONS = {
  survey_date: {
    key: "survey_date",
    label: "调查日期",
    type: "date",
    required: true,
  },
  region: {
    key: "region",
    label: "区域",
    type: "select",
    options: ["乡镇", "城区"],
  },
  town_or_street: {
    key: "town_or_street",
    label: "乡镇｜街道",
    type: "text",
    required: true,
  },
  location_id: {
    key: "location_id",
    label: "编号",
    type: "text",
    required: true,
  },
  location_name: {
    key: "location_name",
    label: "点位名称",
    type: "text",
    required: true,
  },
  occurrence_position: {
    key: "occurrence_position",
    label: "发生位置",
    type: "text",
  },
  total_insect_count: {
    key: "total_insect_count",
    label: "总虫口数",
    type: "number",
  },
  damage_level: {
    key: "damage_level",
    label: "受害程度",
    type: "select",
    options: ["轻", "中", "重"],
  },
  pest_name: {
    key: "pest_name",
    label: "虫种",
    type: "text",
  },
  host_plant: {
    key: "host_plant",
    label: "受害树种",
    type: "text",
  },
  plot_type: {
    key: "plot_type",
    label: "地块类型",
    type: "text",
  },
  report_time: {
    key: "report_time",
    label: "上报时间",
    type: "date",
  },
  description: {
    key: "description",
    label: "详细情况描述",
    type: "textarea",
    required: true,
  },
  note: {
    key: "note",
    label: "备注",
    type: "text",
  },
};

const CHI_HUO_FIELD_KEYS = [
  "survey_date",
  "region",
  "town_or_street",
  "location_id",
  "location_name",
  "occurrence_position",
  "plot_type",
  "total_insect_count",
  "damage_level",
  "report_time",
  "description",
];

const OTHER_PEST_FIELD_KEYS = [
  "survey_date",
  "region",
  "town_or_street",
  "location_id",
  "location_name",
  "occurrence_position",
  "plot_type",
  "pest_name",
  "host_plant",
  "report_time",
  "description",
];

export function isChiHuo(pestType) {
  return pestType === "春尺蠖" || pestType === "国槐尺蠖";
}

export function getDefaultControlType(pestType) {
  return DEFAULT_CONTROL_TYPE_BY_PEST[pestType] || CONTROL_TYPE_OPTIONS[0].value;
}

export function getTaskOptions(pestType) {
  return CONTROL_TASK_OPTIONS_BY_PEST[pestType] || [];
}

export function getDefaultTask(pestType) {
  return getTaskOptions(pestType)[0]?.value || "";
}

export function getVisibleFields(pestType) {
  const fieldKeys = isChiHuo(pestType) ? CHI_HUO_FIELD_KEYS : OTHER_PEST_FIELD_KEYS;
  return fieldKeys.map((key) => FIELD_DEFINITIONS[key]);
}

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

export function createEmptyRecord(pestType) {
  return normalizeRecordForPest(
    {
      survey_date: getTodayDate(),
      region: "",
      town_or_street: "",
      location_id: "",
      location_name: "",
      occurrence_position: "",
      total_insect_count: "",
      damage_level: "",
      pest_name: "",
      host_plant: "",
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
  const defaultRegion = isChiHuo(pestType) ? "乡镇" : "城区";
  const next = {
    survey_date: record.survey_date || getTodayDate(),
    region: record.region || defaultRegion,
    town_or_street: record.town_or_street || "",
    location_id: record.location_id || "",
    location_name: record.location_name || "",
    occurrence_position: record.occurrence_position || "",
    total_insect_count: record.total_insect_count ?? "",
    damage_level: record.damage_level || "",
    pest_name: record.pest_name || "",
    host_plant: record.host_plant || "",
    description: record.description || "",
    note: record.note || "",
    plot_type: record.plot_type || "",
    report_time: record.report_time || getTodayDate(),
    images: Array.isArray(record.images) ? record.images.slice(0, 4) : [],
  };

  if (isChiHuo(pestType)) {
    next.pest_name = "";
    next.host_plant = "";
    next.plot_type = "平原造林";
  }

  return next;
}

export function toPayloadRecord(record, pestType) {
  const normalized = normalizeRecordForPest(record, pestType);
  const base = {
    survey_date: normalizeDate(normalized.survey_date),
    region: normalized.region.trim(),
    town_or_street: normalized.town_or_street.trim(),
    location_id: normalized.location_id.trim(),
    location_name: normalized.location_name.trim(),
    occurrence_position: normalized.occurrence_position.trim(),
    report_time: normalizeDate(normalized.report_time),
    description: normalized.description.trim(),
    note: normalized.note.trim(),
    images: normalized.images.slice(0, 4),
  };

  if (isChiHuo(pestType)) {
    return {
      ...base,
      plot_type: "平原造林",
      total_insect_count: normalized.total_insect_count === "" ? null : Number(normalized.total_insect_count),
      damage_level: normalized.damage_level.trim(),
    };
  }

  return {
    ...base,
    pest_name: normalized.pest_name.trim(),
    host_plant: normalized.host_plant.trim(),
    plot_type: normalized.plot_type.trim(),
  };
}

export function validateRecords(records, pestType) {
  return records.map((record) => {
    const current = normalizeRecordForPest(record, pestType);
    const errors = {};

    REQUIRED_FIELD_KEYS.forEach((key) => {
      if (!`${current[key] ?? ""}`.trim()) {
        errors[key] = "必填";
      }
    });

    if (isChiHuo(pestType) && current.total_insect_count !== "") {
      const numeric = Number(current.total_insect_count);
      if (!Number.isFinite(numeric) || numeric < 0) {
        errors.total_insect_count = "需为非负数字";
      }
    }

    if ((current.images || []).length > 4) {
      errors.images = "最多 4 张";
    }

    return errors;
  });
}

export function hasValidationErrors(errorList) {
  return errorList.some((entry) => Object.keys(entry).length > 0);
}

export function parseClipboardGrid(rawText) {
  const normalized = `${rawText ?? ""}`.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const lines = normalized.split("\n");
  while (lines.length && lines[lines.length - 1] === "") {
    lines.pop();
  }
  return lines.map((line) => line.split("\t"));
}
