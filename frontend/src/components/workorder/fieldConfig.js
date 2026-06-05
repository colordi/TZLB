export const PEST_OPTIONS = [
  { value: "春尺蠖", label: "春尺蠖" },
  { value: "国槐尺蠖", label: "国槐尺蠖" },
  { value: "美国白蛾", label: "美国白蛾" },
  { value: "其他害虫", label: "其他害虫" },
];

export const CONTROL_TYPE_OPTIONS = [
  { value: "春尺蠖防治", label: "春尺蠖防治" },
  { value: "国槐尺蠖防治", label: "国槐尺蠖防治" },
  { value: "美国白蛾防治", label: "美国白蛾防治" },
  { value: "其他害虫防治", label: "其他害虫防治" },
];

const DEFAULT_CONTROL_TYPE_BY_PEST = {
  春尺蠖: "春尺蠖防治",
  国槐尺蠖: "国槐尺蠖防治",
  美国白蛾: "美国白蛾防治",
  其他害虫: "其他害虫防治",
};

const CONTROL_TASK_OPTIONS_BY_PEST = {
  春尺蠖: [
    { value: "2026春尺蠖防治", label: "2026春尺蠖防治" },
  ],
  国槐尺蠖: [
    { value: "2026国槐尺蠖第一代防治", label: "2026国槐尺蠖第一代防治" },
    { value: "2026国槐尺蠖第二代防治", label: "2026国槐尺蠖第二代防治" },
    { value: "2026国槐尺蠖第三代防治", label: "2026国槐尺蠖第三代防治" },
  ],
  美国白蛾: [
    { value: "2026美国白蛾第一代防治", label: "2026美国白蛾第一代防治" },
  ],
  其他害虫: [
    { value: "2026其他害虫防治", label: "2026其他害虫防治" },
  ],
};

export const REQUIRED_FIELD_KEYS_BY_PEST = {
  春尺蠖: [
    "survey_date",
    "locality",
    "location_id",
    "location_name",
    "description",
  ],
  国槐尺蠖: [
    "survey_date",
    "locality",
    "location_id",
    "location_name",
    "description",
  ],
  美国白蛾: [
    "survey_date",
    "locality",
    "location_id",
    "location_name",
    "description",
  ],
  其他害虫: [
    "survey_date",
    "locality",
    "location_id",
    "location_name",
    "description",
  ],
};

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
  locality: {
    key: "locality",
    label: "属地",
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
    label: "虫害类型",
    type: "text",
  },
  host_plant: {
    key: "host_plant",
    label: "寄主树种",
    type: "text",
  },
  green_space_type: {
    key: "green_space_type",
    label: "绿地性质",
    type: "text",
  },
  pest_hosts: {
    key: "pest_hosts",
    label: "危害寄主",
    type: "text",
  },
  damaged_plant_count: {
    key: "damaged_plant_count",
    label: "受害株数",
    type: "number",
  },
  web_nest_count: {
    key: "web_nest_count",
    label: "网幕数量",
    type: "number",
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

const SPRING_CHI_HUO_FIELD_KEYS = [
  "survey_date",
  "locality",
  "location_id",
  "location_name",
  "note",
  "description",
];

const GUO_HUAI_FIELD_KEYS = [
  "survey_date",
  "locality",
  "location_id",
  "location_name",
  "note",
  "description",
];

const OTHER_PEST_FIELD_KEYS = [
  "survey_date",
  "locality",
  "location_id",
  "location_name",
  "plot_type",
  "pest_name",
  "host_plant",
  "note",
  "description",
];

const MEI_GUO_BAI_E_FIELD_KEYS = [
  "survey_date",
  "locality",
  "location_id",
  "location_name",
  "green_space_type",
  "pest_hosts",
  "damaged_plant_count",
  "web_nest_count",
  "note",
  "description",
];

export function isChiHuo(pestType) {
  return pestType === "春尺蠖" || pestType === "国槐尺蠖";
}

export function isMeiGuoBaiE(pestType) {
  return pestType === "美国白蛾";
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

function getFieldKeysByPest(pestType) {
  if (pestType === "春尺蠖") {
    return SPRING_CHI_HUO_FIELD_KEYS;
  }

  if (pestType === "国槐尺蠖") {
    return GUO_HUAI_FIELD_KEYS;
  }

  if (isMeiGuoBaiE(pestType)) {
    return MEI_GUO_BAI_E_FIELD_KEYS;
  }

  return OTHER_PEST_FIELD_KEYS;
}

export function getVisibleFields(pestType) {
  return getFieldKeysByPest(pestType).map((key) => FIELD_DEFINITIONS[key]);
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
  const defaultRegion = isChiHuo(pestType) || isMeiGuoBaiE(pestType) ? "乡镇" : "城区";
  const next = {
    survey_date: record.survey_date || getTodayDate(),
    region: record.region || defaultRegion,
    locality: record.locality || "",
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

  if (isChiHuo(pestType)) {
    next.pest_name = "";
    next.host_plant = "";
    next.plot_type = "平原造林";
  }

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

export function toPayloadRecord(record, pestType) {
  const normalized = normalizeRecordForPest(record, pestType);
  const sharedPayload = {
    survey_date: normalizeDate(normalized.survey_date),
    locality: normalized.locality.trim(),
    location_id: normalized.location_id.trim(),
    location_name: normalized.location_name.trim(),
    description: normalized.description.trim(),
    note: normalized.note.trim(),
    images: normalized.images.slice(0, 4),
  };

  if (pestType === "春尺蠖" || pestType === "国槐尺蠖") {
    return sharedPayload;
  }

  if (isMeiGuoBaiE(pestType)) {
    return {
      ...sharedPayload,
      green_space_type: normalized.green_space_type.trim(),
      pest_hosts: normalized.pest_hosts.trim(),
      damaged_plant_count: normalizeOptionalInteger(normalized.damaged_plant_count),
      web_nest_count: normalizeOptionalInteger(normalized.web_nest_count),
    };
  }

  return {
    ...sharedPayload,
    pest_name: normalized.pest_name.trim(),
    host_plant: normalized.host_plant.trim(),
    plot_type: normalized.plot_type.trim(),
  };
}

export function validateRecords(records, pestType) {
  return records.map((record) => {
    const current = normalizeRecordForPest(record, pestType);
    const errors = {};
    const requiredFieldKeys = REQUIRED_FIELD_KEYS_BY_PEST[pestType] || REQUIRED_FIELD_KEYS_BY_PEST.其他害虫;

    requiredFieldKeys.forEach((key) => {
      if (!`${current[key] ?? ""}`.trim()) {
        errors[key] = "必填";
      }
    });

    ["total_insect_count", "damaged_plant_count", "web_nest_count"].forEach((key) => {
      if (!getFieldKeysByPest(pestType).includes(key) || current[key] === "") {
        return;
      }

      const numeric = Number(current[key]);
      if (!Number.isFinite(numeric) || numeric < 0) {
        errors[key] = "需为非负数字";
      }
    });

    if ((current.images || []).length > 4) {
      errors.images = "最多 4 张";
    }

    return errors;
  });
}

export function hasValidationErrors(errorList) {
  return errorList.some((entry) => Object.keys(entry).length > 0);
}
