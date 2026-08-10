/** Shared map page constants and small pure helpers. */

export const LOCALITY_MODE_PREFIX = "prefix";
export const LOCALITY_MODE_MANUAL = "manual";

/** 仅这两种基础表保留旧的按编号删除入口（通用删除未做） */
export const DELETABLE_BASE_TABLES = new Set([
  "美国白蛾点位基础表",
  "其他害虫点位基础表",
]);

export const SITE_ADD_KIND_WHITE_MOTH = "white-moth";
export const SITE_ADD_KIND_OTHER_PEST = "other-pest";
export const SITE_ADD_KIND_GENERIC = "generic";

export const LOCALITY_FIELD = "属地";
export const SURVEY_STATUS_FILTER_KEY = "调查状态";
export const SELECTED_VIEW_STORAGE_KEY = "tzlb.map.selectedView";

export const SURVEY_STATUS_FILTER_OPTIONS = [
  { key: "all", label: "全部", value: "" },
  { key: "completed", label: "已调查", value: "调查" },
  { key: "pending", label: "未调查", value: "未调查" },
];

export const SURVEY_STATUS_COUNT_KEYS = {
  all: "all",
  completed: "completed",
  pending: "pending",
};

export const SEARCH_RESULT_LIMIT = 8;

export const SEARCH_FIELD_KEYS = [
  "编号",
  "点位编号",
  "location_id",
  "locationId",
  "id",
  "点位名称",
  "位置名称",
  "名称",
  "location_name",
  "locationName",
  "name",
  "属地",
  "乡镇",
  "村",
  "乡镇街道",
  "town_or_street",
  "township",
];

export function createEmptyFeatureCollection() {
  return {
    type: "FeatureCollection",
    features: [],
  };
}

export function readStoredSelectedView() {
  try {
    return globalThis.localStorage?.getItem(SELECTED_VIEW_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

export function storeSelectedView(viewName) {
  const normalizedViewName = `${viewName || ""}`.trim();
  if (!normalizedViewName) {
    return;
  }

  try {
    globalThis.localStorage?.setItem(SELECTED_VIEW_STORAGE_KEY, normalizedViewName);
  } catch {
    // 浏览器禁用本地存储时不影响地图正常使用。
  }
}

export function normalizeBbox(bbox) {
  const values = Array.isArray(bbox)
    ? bbox
    : [bbox?.minLng, bbox?.minLat, bbox?.maxLng, bbox?.maxLat];
  if (values.length !== 4 || !values.every((item) => Number.isFinite(Number(item)))) {
    return null;
  }
  return values.map((item) => Number(item));
}

export function isSameBbox(left, right) {
  if (!left || !right || left.length !== right.length) {
    return false;
  }
  return left.every((value, index) => Math.abs(value - right[index]) < 0.000001);
}

export function resolveSiteAddConfig(view) {
  const siteAdd = view?.site_add;
  if (!siteAdd?.enabled) {
    return null;
  }
  return siteAdd;
}

export function matchSitePrefix(code, prefixLocalities = {}) {
  const normalized = `${code || ""}`.trim().toUpperCase();
  if (!normalized) return "";
  const prefixes = Object.keys(prefixLocalities).sort((a, b) => b.length - a.length);
  for (const prefix of prefixes) {
    if (normalized === prefix) return prefix;
    if (
      normalized.startsWith(prefix) &&
      /^\d*$/.test(normalized.slice(prefix.length))
    ) {
      return prefix;
    }
  }
  return "";
}
