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

const OTHER_PEST_IMPORT_COLUMNS = [
  { key: "location_id", label: "编号", fallback: "—" },
  { key: "locality", label: "属地", fallback: "未匹配" },
  { key: "location_name", label: "点位名称", fallback: "未匹配" },
  { key: "pest_name", label: "虫害类型", fallback: "—" },
  { key: "host_plant", label: "寄主树种", fallback: "—" },
  { key: "survey_result", label: "调查结论", fallback: "—" },
];

const DEFAULT_TASK_TEMPLATE = "{year}{pest}{generation}防治";
const GENERATION_NONE = [null];
const GENERATIONS_THREE = ["第一代", "第二代", "第三代"];

// 与后端 pest_registry 的图片策略一致
const IMAGE_STRATEGY_UPLOADED = "uploaded_images";
const IMAGE_STRATEGY_AUTO_DISK = "auto_disk_images";

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
    imageStrategy: IMAGE_STRATEGY_UPLOADED,
    surveyImport: {
      description: "按调查日期查询春尺蠖受害点位，并批量导入到当前工单。",
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
    imageStrategy: IMAGE_STRATEGY_UPLOADED,
    surveyImport: {
      description: "按调查日期查询国槐尺蠖受害点位，并批量导入到当前工单。",
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
    imageStrategy: IMAGE_STRATEGY_AUTO_DISK,
    surveyImport: {
      description: "按调查日期查询美国白蛾第一代问题点位，并批量导入到当前工单。",
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
    imageStrategy: IMAGE_STRATEGY_AUTO_DISK,
    surveyImport: {
      description: "按调查日期查询其他害虫问题点位，并批量导入到当前工单。",
      idleHint: "当前支持按调查日期导入其他害虫调查数据。",
      columns: OTHER_PEST_IMPORT_COLUMNS,
      candidateKeyFields: COMMON_IMPORT_KEY_FIELDS,
    },
  },
  {
    key: "杨树食叶害虫",
    label: "杨树食叶害虫",
    group: "yangshu_shiye",
    controlType: "杨树食叶害虫防治",
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
    defaultRegion: "乡镇",
    recordDefaults: {},
    recordOverrides: {},
    imageStrategy: IMAGE_STRATEGY_AUTO_DISK,
    surveyImport: {
      description: "按调查日期查询杨树食叶害虫问题点位，并批量导入到当前工单。",
      idleHint: "当前支持按调查日期导入杨树食叶害虫调查数据。",
      columns: OTHER_PEST_IMPORT_COLUMNS,
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

export {
  COMMON_IMPORT_KEY_FIELDS,
  COMMON_PAYLOAD_FIELD_KEYS,
  COMMON_REQUIRED_FIELD_KEYS,
};
