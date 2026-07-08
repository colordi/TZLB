const COMMON_REQUIRED_FIELD_KEYS = [
  "survey_date",
  "locality",
  "location_id",
  "location_name",
  "description",
];

const COMMON_PAYLOAD_FIELD_KEYS = [
  "survey_date",
  "locality",
  "location_id",
  "location_name",
  "description",
  "note",
  "images",
];

const CHI_HUO_FIELD_KEYS = [
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

const CHI_HUO_IMPORT_COLUMNS = [
  { key: "location_id", label: "编号", fallback: "—" },
  { key: "locality", label: "属地", fallback: "未匹配" },
  { key: "location_name", label: "点位名称", fallback: "未匹配" },
  { key: "total_insect_count", label: "总虫口数", fallback: "—" },
  { key: "damage_level", label: "受害程度", fallback: "—" },
];

const COMMON_IMPORT_KEY_FIELDS = ["survey_date", "location_id", "pest_name"];

const DEFAULT_TASK_TEMPLATE = "{year}{pest}{generation}防治";
const GENERATION_NONE = [null];
const GENERATIONS_THREE = ["第一代", "第二代", "第三代"];

export const PEST_REGISTRY = [
  {
    key: "春尺蠖",
    label: "春尺蠖",
    group: "chi_huo",
    controlType: "春尺蠖防治",
    taskTemplate: DEFAULT_TASK_TEMPLATE,
    generations: GENERATION_NONE,
    fieldKeys: CHI_HUO_FIELD_KEYS,
    requiredFieldKeys: COMMON_REQUIRED_FIELD_KEYS,
    numberFieldKeys: [],
    payloadFieldKeys: COMMON_PAYLOAD_FIELD_KEYS,
    defaultRegion: "乡镇",
    recordDefaults: { plot_type: "平原造林" },
    recordOverrides: { pest_name: "", host_plant: "" },
    surveyImport: {
      description: "按调查日期查询春尺蠖受害点位，并批量追加到当前工作单。",
      idleHint: "当前支持导入春尺蠖幼虫调查数据。",
      columns: CHI_HUO_IMPORT_COLUMNS,
      candidateKeyFields: COMMON_IMPORT_KEY_FIELDS,
    },
  },
  {
    key: "国槐尺蠖",
    label: "国槐尺蠖",
    group: "chi_huo",
    controlType: "国槐尺蠖防治",
    taskTemplate: DEFAULT_TASK_TEMPLATE,
    generations: GENERATIONS_THREE,
    fieldKeys: CHI_HUO_FIELD_KEYS,
    requiredFieldKeys: COMMON_REQUIRED_FIELD_KEYS,
    numberFieldKeys: [],
    payloadFieldKeys: COMMON_PAYLOAD_FIELD_KEYS,
    defaultRegion: "乡镇",
    recordDefaults: { plot_type: "平原造林" },
    recordOverrides: { pest_name: "", host_plant: "" },
    surveyImport: {
      description: "按调查日期查询国槐尺蠖受害点位，并批量追加到当前工作单。",
      idleHint: "当前支持导入国槐尺蠖幼虫调查数据。",
      columns: CHI_HUO_IMPORT_COLUMNS,
      candidateKeyFields: COMMON_IMPORT_KEY_FIELDS,
    },
  },
  {
    key: "美国白蛾",
    label: "美国白蛾",
    group: "mei_guo_bai_e",
    controlType: "美国白蛾防治",
    taskTemplate: DEFAULT_TASK_TEMPLATE,
    generations: GENERATIONS_THREE,
    fieldKeys: MEI_GUO_BAI_E_FIELD_KEYS,
    requiredFieldKeys: COMMON_REQUIRED_FIELD_KEYS,
    numberFieldKeys: ["damaged_plant_count", "web_nest_count"],
    payloadFieldKeys: [
      ...COMMON_PAYLOAD_FIELD_KEYS,
      "green_space_type",
      "pest_hosts",
      "damaged_plant_count",
      "web_nest_count",
    ],
    defaultRegion: "乡镇",
    recordDefaults: {},
    recordOverrides: {},
    surveyImport: {
      description: "按调查日期查询美国白蛾第一代问题点位，并批量追加到当前工作单。",
      idleHint: "当前支持按调查日期导入美国白蛾第一代调查数据。",
      columns: [
        { key: "location_id", label: "编号", fallback: "—" },
        { key: "locality", label: "属地", fallback: "未匹配" },
        { key: "location_name", label: "点位名称", fallback: "未匹配" },
        { key: "green_space_type", label: "绿地性质", fallback: "—" },
        { key: "pest_hosts", label: "危害寄主", fallback: "—" },
        { key: "damaged_plant_count", label: "受害株数", fallback: "—" },
        { key: "web_nest_count", label: "网幕数量", fallback: "—" },
      ],
      candidateKeyFields: COMMON_IMPORT_KEY_FIELDS,
    },
  },
  {
    key: "其他害虫",
    label: "其他害虫",
    group: "other_pest",
    controlType: "其他害虫防治",
    taskTemplate: DEFAULT_TASK_TEMPLATE,
    generations: GENERATION_NONE,
    fieldKeys: OTHER_PEST_FIELD_KEYS,
    requiredFieldKeys: COMMON_REQUIRED_FIELD_KEYS,
    numberFieldKeys: [],
    payloadFieldKeys: [
      ...COMMON_PAYLOAD_FIELD_KEYS,
      "plot_type",
      "pest_name",
      "host_plant",
    ],
    defaultRegion: "城区",
    recordDefaults: {},
    recordOverrides: {},
    surveyImport: {
      description: "按调查日期查询其他害虫问题点位，并批量追加到当前工作单。",
      idleHint: "当前支持按调查日期导入其他害虫调查数据。",
      columns: [
        { key: "location_id", label: "编号", fallback: "—" },
        { key: "locality", label: "属地", fallback: "未匹配" },
        { key: "location_name", label: "点位名称", fallback: "未匹配" },
        { key: "pest_name", label: "虫害类型", fallback: "—" },
        { key: "host_plant", label: "寄主树种", fallback: "—" },
        { key: "survey_result", label: "调查结论", fallback: "—" },
      ],
      candidateKeyFields: COMMON_IMPORT_KEY_FIELDS,
    },
  },
];

const PEST_REGISTRY_BY_KEY = Object.fromEntries(
  PEST_REGISTRY.map((entry) => [entry.key, entry]),
);

export const PEST_OPTIONS = PEST_REGISTRY.map((entry) => ({
  value: entry.key,
  label: entry.label,
}));

export const CONTROL_TYPE_OPTIONS = Array.from(
  new Map(
    PEST_REGISTRY.map((entry) => [
      entry.controlType,
      { value: entry.controlType, label: entry.controlType },
    ]),
  ).values(),
);

export const REQUIRED_FIELD_KEYS_BY_PEST = Object.fromEntries(
  PEST_REGISTRY.map((entry) => [entry.key, entry.requiredFieldKeys]),
);

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
  town_or_street: {
    key: "town_or_street",
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

export function getPestConfig(pestType) {
  return PEST_REGISTRY_BY_KEY[pestType] || PEST_REGISTRY_BY_KEY.其他害虫;
}

export function isChiHuo(pestType) {
  return getPestConfig(pestType).group === "chi_huo";
}

export function isMeiGuoBaiE(pestType) {
  return getPestConfig(pestType).group === "mei_guo_bai_e";
}

export function supportsSurveyImport(pestType) {
  return Boolean(getPestConfig(pestType).surveyImport);
}

export function getSurveyImportConfig(pestType) {
  const config = getPestConfig(pestType).surveyImport;
  return (
    config || {
      description: "当前虫种暂不支持从数据库导入调查记录。",
      idleHint: "当前虫种暂不支持从数据库导入调查记录。",
      columns: [],
      candidateKeyFields: COMMON_IMPORT_KEY_FIELDS,
    }
  );
}

export function getDefaultControlType(pestType) {
  return getPestConfig(pestType).controlType;
}

export function buildTask(pestType, year, generation) {
  const config = getPestConfig(pestType);
  return config.taskTemplate
    .replace("{year}", year)
    .replace("{pest}", pestType)
    .replace("{generation}", generation || "");
}

export function getCurrentYear() {
  return new Date().getFullYear();
}

export function getGenerations(pestType) {
  return getPestConfig(pestType).generations;
}

export function supportsGeneration(pestType) {
  return getPestConfig(pestType).generations.some((gen) => gen !== null);
}

export function getTaskOptions(pestType, year = getCurrentYear()) {
  const config = getPestConfig(pestType);
  return config.generations.map((gen) => {
    const task = buildTask(pestType, year, gen);
    return { value: task, label: task, generation: gen };
  });
}

export function getDefaultTask(pestType, year = getCurrentYear()) {
  return getTaskOptions(pestType, year)[0]?.value || "";
}

export function getGenerationFromTask(pestType, taskValue, year = getCurrentYear()) {
  const option = getTaskOptions(pestType, year).find((opt) => opt.value === taskValue);
  return option?.generation ?? null;
}

function getFieldKeysByPest(pestType) {
  return getPestConfig(pestType).fieldKeys;
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

export function validateRecords(records, pestType) {
  const config = getPestConfig(pestType);

  return records.map((record) => {
    const current = normalizeRecordForPest(record, pestType);
    const errors = {};

    config.requiredFieldKeys.forEach((key) => {
      if (!`${current[key] ?? ""}`.trim()) {
        errors[key] = "必填";
      }
    });

    config.numberFieldKeys.forEach((key) => {
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
