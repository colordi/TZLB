<script setup>
import { Filter, Search, X } from "@lucide/vue";
import { computed, nextTick, onMounted, ref, shallowRef, watch } from "vue";

import { useToast } from "../composables/useToast.js";
import {
  createWhiteMothSite,
  deleteWhiteMothSite,
  deleteWhiteMothSiteCheck,
  fetchMapFilterOptions,
  fetchMapView,
  fetchReferenceLayer,
  fetchWhiteMothSiteCodeHint,
  fetchWhiteMothSiteCodeRules,
  listMapViews,
  listReferenceLayers,
} from "../api/map.js";
import { isUnauthorizedError } from "../api/http.js";
import {
  buildPopupRows,
  resolveFeatureHoverLabel,
} from "../components/map/popupFields.js";
import ConfirmDialog from "../components/common/ConfirmDialog.vue";
import LeafletMap from "../components/map/LeafletMap.vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";

function createEmptyFeatureCollection() {
  return {
    type: "FeatureCollection",
    features: [],
  };
}

const { error, info, success } = useToast();
const WHITE_MOTH_SITE_VIEW_NAME = "美国白蛾点位";
const LOCALITY_FIELD = "属地";
const SURVEY_STATUS_FILTER_KEY = "调查状态";
const SELECTED_VIEW_STORAGE_KEY = "tzlb.map.selectedView";
const SURVEY_STATUS_FILTER_OPTIONS = [
  { key: "all", label: "全部", value: "" },
  { key: "completed", label: "已调查", value: "调查" },
  { key: "pending", label: "未调查", value: "未调查" },
];
const SURVEY_STATUS_COUNT_KEYS = {
  all: "all",
  completed: "completed",
  pending: "pending",
};

const views = ref([]);
const selectedView = ref("");
const basemapMode = ref("satellite");
const showPointLabels = ref(true);
const geojson = ref(createEmptyFeatureCollection());
const searchIndexByView = shallowRef({});
const loadingSearchIndex = ref(false);
const mapFilterOptions = ref({ filter_fields: [] });
const referenceLayers = ref([]);
const activeReferenceLayerNames = ref([]);
const referenceLayerGeojsonByName = shallowRef({});
const loadingReferenceLayerNames = ref([]);
const loading = ref(false);
const loadingViews = ref(false);
const loadingFilterOptions = ref(false);
const autoFitOnDataChange = ref(true);
const selectedFeature = ref(null);
const searchQuery = ref("");
const searchFocused = ref(false);
const searchInputRef = ref(null);
const isSearchPanelOpen = ref(false);
const surveyStatusFilter = ref("all");
const isSurveyStatusFilterOpen = ref(false);
const dynamicFilterValues = ref({});
const mapFocusRequest = ref(null);
const whiteMothSiteCodeRules = ref(null);
const whiteMothSiteDraftLocation = ref(null);
const currentMapViewport = ref(null);
const whiteMothSiteForm = ref({
  code: "",
  siteName: "",
});
const whiteMothSiteCodeHint = ref(null);
const loadingWhiteMothSiteCodeHint = ref(false);
const isAddingWhiteMothSite = ref(false);
const isSavingWhiteMothSite = ref(false);
const showDeleteConfirm = ref(false);
const isDeletingWhiteMothSite = ref(false);
const deleteCheckLoading = ref(false);
const pendingDeleteSite = ref(null);
let geojsonRequestToken = 0;
let filterOptionsRequestToken = 0;
let searchIndexRequestToken = 0;
let whiteMothSiteCodeHintRequestToken = 0;
let shouldAutoFitOnNextViewChange = true;
let mapFocusRequestToken = 0;

const SEARCH_RESULT_LIMIT = 8;
const SEARCH_FIELD_KEYS = [
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

function readStoredSelectedView() {
  try {
    return globalThis.localStorage?.getItem(SELECTED_VIEW_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

function storeSelectedView(viewName) {
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

const featureTitle = computed(() => {
  if (!selectedFeature.value?.properties) return "";
  return resolveFeatureHoverLabel(currentView.value.columns, selectedFeature.value.properties, {
    preferIdentifier: false,
  });
});

const featureRows = computed(() => {
  if (!selectedFeature.value?.properties) return [];
  return buildPopupRows(currentView.value.columns, selectedFeature.value.properties);
});

const canDeleteSelectedSite = computed(() => {
  if (selectedView.value !== WHITE_MOTH_SITE_VIEW_NAME) return false;
  if (!selectedFeature.value?.properties) return false;
  const code = `${selectedFeature.value.properties["编号"] ?? ""}`.trim();
  return code !== "";
});

const deleteConfirmMessage = computed(() => {
  const site = pendingDeleteSite.value;
  if (!site) return "";
  const label = `${site.locality || "未知属地"} · ${site.site_name || "未命名"}`;
  if (!site.survey_record_count) {
    return `将删除美国白蛾点位「${site.code}」（${label}）。此操作仅删除点位，不删除已关联的调查记录和台账，且不可撤销。`;
  }
  return `将删除美国白蛾点位「${site.code}」（${label}）。该编号当前关联 ${site.survey_record_count} 条调查记录，删除点位后这些调查记录和台账将变为悬空数据。此操作不可撤销，确认仍要删除吗？`;
});

function closeDeleteConfirm() {
  showDeleteConfirm.value = false;
  pendingDeleteSite.value = null;
}

async function requestDeleteWhiteMothSite() {
  if (isDeletingWhiteMothSite.value || deleteCheckLoading.value) return;
  const code = `${selectedFeature.value?.properties?.["编号"] ?? ""}`.trim();
  if (!code) {
    error("未读取到点位编号。", "删除失败");
    return;
  }

  deleteCheckLoading.value = true;
  try {
    const result = await deleteWhiteMothSiteCheck(code);
    if (!result.exists) {
      error("点位已被删除或不存在。", "删除失败");
      closeDetail();
      await refreshWhiteMothSiteView();
      return;
    }
    pendingDeleteSite.value = result;
    showDeleteConfirm.value = true;
  } catch (checkError) {
    if (isUnauthorizedError(checkError)) return;
    error(`${checkError.message || checkError}`, "删除前检查失败");
  } finally {
    deleteCheckLoading.value = false;
  }
}

async function confirmDeleteWhiteMothSite() {
  const site = pendingDeleteSite.value;
  if (!site) {
    closeDeleteConfirm();
    return;
  }

  isDeletingWhiteMothSite.value = true;
  try {
    const deleted = await deleteWhiteMothSite(site.code);
    success(`点位 ${deleted.code} 已删除。`, "删除成功");
    closeDeleteConfirm();
    closeDetail();
    await refreshWhiteMothSiteView();
  } catch (deleteError) {
    if (isUnauthorizedError(deleteError)) {
      return;
    }
    error(`${deleteError.message || deleteError}`, "删除失败");
  } finally {
    isDeletingWhiteMothSite.value = false;
  }
}

function normalizeSearchValue(value) {
  return `${value ?? ""}`.trim();
}

function getFirstFeatureValue(properties = {}, keys = []) {
  for (const key of keys) {
    const value = normalizeSearchValue(properties[key]);
    if (value) {
      return value;
    }
  }
  return "";
}

function getSearchResultTitle(feature, columns = []) {
  return (
    resolveFeatureHoverLabel(columns, feature?.properties || {}, {
      preferIdentifier: false,
    }) ||
    getFirstFeatureValue(feature?.properties || {}, SEARCH_FIELD_KEYS) ||
    "未命名点位"
  );
}

function getSearchResultMeta(feature) {
  const properties = feature?.properties || {};
  const identifier = getFirstFeatureValue(properties, [
    "编号",
    "点位编号",
    "location_id",
    "locationId",
    "id",
  ]);
  const district = getFirstFeatureValue(properties, [
    "属地",
    "乡镇",
    "村",
    "town_or_street",
    "township",
  ]);

  return [identifier, district].filter(Boolean).join(" · ");
}

async function ensureSearchIndex() {
  const viewName = selectedView.value;
  if (!viewName || searchIndexByView.value[viewName]) {
    return;
  }

  const requestToken = ++searchIndexRequestToken;
  loadingSearchIndex.value = true;

  try {
    // 拉取当前视图全量点位（不带筛选和视口 bbox），保证搜索覆盖全部点位
    const payload = await fetchMapView(viewName);
    if (requestToken !== searchIndexRequestToken || viewName !== selectedView.value) {
      return;
    }
    searchIndexByView.value = { ...searchIndexByView.value, [viewName]: payload };
  } catch (loadError) {
    if (!isUnauthorizedError(loadError)) {
      info(`${loadError.message || loadError}`, "点位搜索数据加载失败");
    }
  } finally {
    if (requestToken === searchIndexRequestToken) {
      loadingSearchIndex.value = false;
    }
  }
}

function resetSearchIndex() {
  searchIndexRequestToken += 1;
  searchIndexByView.value = {};
  loadingSearchIndex.value = false;
}

const searchableFeatures = computed(
  () => searchIndexByView.value[selectedView.value]?.features || [],
);
const searchResults = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase();
  if (!keyword) {
    return [];
  }

  return searchableFeatures.value
    .map((feature, index) => {
      const properties = feature?.properties || {};
      const searchableValues = Array.from(
        new Set([
          ...SEARCH_FIELD_KEYS,
          ...(currentView.value.columns || []),
        ]),
      )
        .map((key) => normalizeSearchValue(properties[key]))
        .filter(Boolean);
      const title = getSearchResultTitle(feature, currentView.value.columns);
      const meta = getSearchResultMeta(feature);
      const haystack = [title, meta, ...searchableValues].join(" ").toLowerCase();
      return {
        key: `${index}-${title}-${meta}`,
        feature,
        title,
        meta,
        matched: haystack.includes(keyword),
      };
    })
    .filter((result) => result.matched)
    .slice(0, SEARCH_RESULT_LIMIT);
});
const showSearchResults = computed(() => searchQuery.value.trim() !== "");
const surveyStatusField = computed(() =>
  (mapFilterOptions.value?.filter_fields || []).find(
    (field) => field?.key === SURVEY_STATUS_FILTER_KEY,
  ),
);
const supportsSurveyStatusFilter = computed(() => Boolean(surveyStatusField.value));
const visibleSurveyStatusOptions = computed(() => {
  const values = new Set(
    (surveyStatusField.value?.options || [])
      .map((option) => `${option?.value ?? ""}`.trim())
      .filter(Boolean),
  );

  return SURVEY_STATUS_FILTER_OPTIONS.filter(
    (option) => option.key === "all" || values.has(option.value),
  );
});
const surveyStatusCounts = computed(
  () => mapFilterOptions.value?.survey_status_counts || {},
);
const dynamicFilterFields = computed(() =>
  (mapFilterOptions.value?.filter_fields || []).filter(
    (field) => field?.key !== SURVEY_STATUS_FILTER_KEY,
  ),
);
const activeMapFilters = computed(() => {
  const filters = {};

  if (supportsSurveyStatusFilter.value && surveyStatusFilter.value !== "all") {
    const selectedOption = SURVEY_STATUS_FILTER_OPTIONS.find(
      (option) => option.key === surveyStatusFilter.value,
    );
    if (selectedOption?.value) {
      filters[SURVEY_STATUS_FILTER_KEY] = [selectedOption.value];
    }
  }

  for (const [key, value] of Object.entries(dynamicFilterValues.value)) {
    if (value) {
      filters[key] = [value];
    }
  }

  return filters;
});

function getSurveyStatusCount(optionKey) {
  const countKey = SURVEY_STATUS_COUNT_KEYS[optionKey];
  const count = surveyStatusCounts.value?.[countKey];
  return Number.isFinite(Number(count)) ? Number(count) : 0;
}

function onFeatureClick(feature) {
  if (isAddingWhiteMothSite.value) {
    return;
  }
  selectedFeature.value = feature;
}

function focusFeatureOnMap(feature) {
  mapFocusRequestToken += 1;
  mapFocusRequest.value = {
    token: mapFocusRequestToken,
    feature,
  };
}

function selectSearchResult(result) {
  if (!result?.feature) {
    return;
  }

  selectedFeature.value = result.feature;
  searchQuery.value = result.title;
  searchFocused.value = false;
  isSearchPanelOpen.value = false;
  focusFeatureOnMap(result.feature);
}

async function toggleSearchPanel() {
  isSearchPanelOpen.value = !isSearchPanelOpen.value;
  if (!isSearchPanelOpen.value) {
    searchFocused.value = false;
    return;
  }

  isSurveyStatusFilterOpen.value = false;
  ensureSearchIndex();
  await nextTick();
  // ui/input 组件 ref 取组件实例，需取 $el 才能调原生 focus
  const searchInputEl = searchInputRef.value?.$el ?? searchInputRef.value;
  searchInputEl?.focus?.({ preventScroll: true });
}

function toggleSurveyStatusFilterPanel() {
  isSurveyStatusFilterOpen.value = !isSurveyStatusFilterOpen.value;
  if (isSurveyStatusFilterOpen.value) {
    isSearchPanelOpen.value = false;
    searchFocused.value = false;
  }
}

async function submitSearch() {
  if (!searchQuery.value.trim()) {
    return;
  }

  await ensureSearchIndex();
  if (searchResults.value.length > 0) {
    selectSearchResult(searchResults.value[0]);
    return;
  }

  info("未找到匹配点位。", "搜索无结果");
}

function clearSearch() {
  searchQuery.value = "";
  searchFocused.value = false;
}

function closeDetail() {
  selectedFeature.value = null;
}

function closeMapFloatingPanels() {
  isSearchPanelOpen.value = false;
  searchFocused.value = false;
  isSurveyStatusFilterOpen.value = false;
}

function resetSurveyStatusFilter() {
  surveyStatusFilter.value = "all";
  isSurveyStatusFilterOpen.value = false;
}

function resetDynamicFilters() {
  dynamicFilterValues.value = {};
}

function resolveDefaultDynamicFilters() {
  const view = views.value.find((v) => v.name === selectedView.value);
  const configuredDefaults = view?.default_filters || {};
  const excludedKeys = new Set([SURVEY_STATUS_FILTER_KEY, LOCALITY_FIELD]);
  const dynamicFields = (mapFilterOptions.value?.filter_fields || []).filter(
    (field) => !excludedKeys.has(field.key),
  );

  const resolved = {};
  for (const field of dynamicFields) {
    const configuredValue = configuredDefaults[field.key];
    if (configuredValue) {
      const optionValues = (field.options || []).map((o) => o.value);
      if (optionValues.includes(configuredValue)) {
        resolved[field.key] = configuredValue;
      }
      continue;
    }
    if (field.default_value) {
      const optionValues = (field.options || []).map((o) => o.value);
      if (optionValues.includes(field.default_value)) {
        resolved[field.key] = field.default_value;
      }
    }
  }
  return resolved;
}

async function selectDynamicFilter(key, value) {
  dynamicFilterValues.value = { ...dynamicFilterValues.value, [key]: value };
  selectedFeature.value = null;
  mapFocusRequest.value = null;
  await Promise.all([loadGeoJson({ autoFit: false }), loadFilterOptions()]);
}

function normalizeBbox(bbox) {
  const values = Array.isArray(bbox)
    ? bbox
    : [bbox?.minLng, bbox?.minLat, bbox?.maxLng, bbox?.maxLat];
  if (
    values.length !== 4 ||
    !values.every((item) => Number.isFinite(Number(item)))
  ) {
    return null;
  }
  return values.map((item) => Number(item));
}

function isSameBbox(left, right) {
  if (!left || !right || left.length !== right.length) {
    return false;
  }
  return left.every((value, index) => Math.abs(value - right[index]) < 0.000001);
}

function buildMapRequestOptions() {
  return {
    bbox: currentMapViewport.value?.bbox || null,
  };
}

const currentView = computed(
  () => views.value.find((view) => view.name === selectedView.value) || { columns: [] },
);
const whiteMothSiteCodeExample = computed(
  () => whiteMothSiteCodeRules.value?.code_example || "MQ001",
);
const whiteMothSitePrefixLocalities = computed(
  () => whiteMothSiteCodeRules.value?.prefix_localities || {},
);
const normalizedWhiteMothSiteCode = computed(() =>
  whiteMothSiteForm.value.code.trim().toUpperCase(),
);
const whiteMothSiteCodeRegex = computed(() => {
  const pattern = whiteMothSiteCodeRules.value?.code_pattern || "";
  try {
    return pattern ? new RegExp(pattern) : null;
  } catch {
    return null;
  }
});
const sortedWhiteMothSitePrefixes = computed(() =>
  Object.keys(whiteMothSitePrefixLocalities.value).sort((a, b) => b.length - a.length),
);
const matchedWhiteMothSitePrefix = computed(() => {
  const code = normalizedWhiteMothSiteCode.value;
  if (!code) {
    return "";
  }
  // 按前缀长度从长到短匹配，输入前缀即可识别，且避免 LYI 被误判为 LY
  for (const prefix of sortedWhiteMothSitePrefixes.value) {
    if (code === prefix) {
      return prefix;
    }
    if (code.startsWith(prefix) && /^\d{0,3}$/.test(code.slice(prefix.length))) {
      return prefix;
    }
  }
  return "";
});
const resolvedWhiteMothSiteLocality = computed(() => {
  if (!matchedWhiteMothSitePrefix.value) {
    return "";
  }
  return whiteMothSitePrefixLocalities.value[matchedWhiteMothSitePrefix.value] || "";
});
const isCompleteWhiteMothSiteCode = computed(() => {
  const code = normalizedWhiteMothSiteCode.value;
  return Boolean(
    code &&
      matchedWhiteMothSitePrefix.value &&
      whiteMothSiteCodeRegex.value?.test(code) &&
      code.slice(matchedWhiteMothSitePrefix.value.length).length === 3,
  );
});
const whiteMothSiteCodeError = computed(() => {
  if (!whiteMothSiteCodeRules.value) {
    return "正在读取编号规则";
  }

  const code = normalizedWhiteMothSiteCode.value;
  if (!code) {
    return "请输入编号";
  }
  if (matchedWhiteMothSitePrefix.value) {
    // 前缀已识别：完整编号才可提交；输入过程中不报红错
    return "";
  }
  // 仍在输入首个字母时先不报错
  if (/^[A-Z]$/.test(code)) {
    return "";
  }
  return `编号格式不正确，请输入类似 ${whiteMothSiteCodeExample.value} 的编号`;
});
const whiteMothSiteCodeHintText = computed(() => {
  if (!matchedWhiteMothSitePrefix.value) {
    return "";
  }
  if (loadingWhiteMothSiteCodeHint.value) {
    return "正在查询该属地最新编号…";
  }
  const hint = whiteMothSiteCodeHint.value;
  if (!hint || hint.prefix !== matchedWhiteMothSitePrefix.value) {
    return "编号提示暂不可用";
  }
  if (hint.latest_code && hint.suggested_next_code) {
    return `当前最大编号 ${hint.latest_code}，建议新编号 ${hint.suggested_next_code}`;
  }
  if (hint.suggested_next_code) {
    return `该属地暂无点位，建议新编号 ${hint.suggested_next_code}`;
  }
  if (hint.latest_code) {
    return `当前最大编号 ${hint.latest_code}，序号已用尽`;
  }
  return "编号提示暂不可用";
});
const whiteMothSiteLocationText = computed(() => {
  if (!whiteMothSiteDraftLocation.value) {
    return "请在地图上点击点位位置";
  }

  const { latitude, longitude } = whiteMothSiteDraftLocation.value;
  return `${Number(longitude).toFixed(6)}, ${Number(latitude).toFixed(6)}`;
});
const canSubmitWhiteMothSite = computed(
  () =>
    Boolean(whiteMothSiteDraftLocation.value) &&
    isCompleteWhiteMothSiteCode.value &&
    !isSavingWhiteMothSite.value,
);
const pointCount = computed(() => geojson.value?.features?.length || 0);
const referenceLayersForMap = computed(() =>
  referenceLayers.value.map((layer) => ({
    ...layer,
    active: activeReferenceLayerNames.value.includes(layer.name),
    loading: loadingReferenceLayerNames.value.includes(layer.name),
    geojson: referenceLayerGeojsonByName.value[layer.name] || createEmptyFeatureCollection(),
  })),
);

async function loadViews() {
  loadingViews.value = true;

  try {
    const payload = await listMapViews();
    views.value = payload;
    resetSearchIndex();
    if (!payload.length) {
      selectedView.value = "";
      geojsonRequestToken += 1;
      filterOptionsRequestToken += 1;
      geojson.value = createEmptyFeatureCollection();
      mapFilterOptions.value = { filter_fields: [] };
      resetSurveyStatusFilter();
      return true;
    }

    if (!payload.some((view) => view.name === selectedView.value)) {
      const storedViewName = readStoredSelectedView();
      const restoredView = payload.find((view) => view.name === storedViewName);
      selectedView.value = restoredView?.name || payload[0].name;
    }
    return true;
  } catch (loadError) {
    views.value = [];
    selectedView.value = "";
    geojson.value = createEmptyFeatureCollection();
    mapFilterOptions.value = { filter_fields: [] };
    resetSurveyStatusFilter();
    if (isUnauthorizedError(loadError)) {
      return false;
    }
    error(`${loadError.message || loadError}`, "地图视图读取失败");
    return false;
  } finally {
    loadingViews.value = false;
  }
}

async function loadWhiteMothSiteCodeRules() {
  try {
    whiteMothSiteCodeRules.value = await fetchWhiteMothSiteCodeRules();
  } catch (loadError) {
    whiteMothSiteCodeRules.value = null;
    if (isUnauthorizedError(loadError)) {
      return;
    }
    error(`${loadError.message || loadError}`, "编号规则读取失败");
  }
}

async function loadFilterOptions(viewName = selectedView.value) {
  if (!viewName) {
    loadingFilterOptions.value = false;
    mapFilterOptions.value = { filter_fields: [] };
    resetSurveyStatusFilter();
    return false;
  }

  const requestToken = ++filterOptionsRequestToken;
  loadingFilterOptions.value = true;

  try {
    const payload = await fetchMapFilterOptions(viewName, dynamicFilterValues.value);
    if (requestToken !== filterOptionsRequestToken || viewName !== selectedView.value) {
      return false;
    }
    mapFilterOptions.value = payload || { filter_fields: [] };
    if (
      !(mapFilterOptions.value?.filter_fields || []).some(
        (field) => field?.key === SURVEY_STATUS_FILTER_KEY,
      )
    ) {
      resetSurveyStatusFilter();
    }
    return true;
  } catch (loadError) {
    if (requestToken !== filterOptionsRequestToken || viewName !== selectedView.value) {
      return false;
    }
    mapFilterOptions.value = { filter_fields: [] };
    resetSurveyStatusFilter();
    if (isUnauthorizedError(loadError)) {
      return false;
    }
    info(`${loadError.message || loadError}`, "地图筛选不可用");
    return false;
  } finally {
    if (requestToken === filterOptionsRequestToken) {
      loadingFilterOptions.value = false;
    }
  }
}

async function loadGeoJson({ autoFit = false } = {}) {
  if (!selectedView.value) {
    loading.value = false;
    return false;
  }

  const requestToken = ++geojsonRequestToken;
  const viewName = selectedView.value;
  autoFitOnDataChange.value = autoFit;
  loading.value = true;

  try {
    const payload = await fetchMapView(
      viewName,
      activeMapFilters.value,
      buildMapRequestOptions(),
    );
    if (requestToken !== geojsonRequestToken || viewName !== selectedView.value) {
      return false;
    }
    geojson.value = payload;
    return true;
  } catch (loadError) {
    if (requestToken !== geojsonRequestToken || viewName !== selectedView.value) {
      return false;
    }
    geojson.value = createEmptyFeatureCollection();
    if (isUnauthorizedError(loadError)) {
      return false;
    }
    error(`${loadError.message || loadError}`, "地图数据读取失败");
    return false;
  } finally {
    if (requestToken === geojsonRequestToken) {
      loading.value = false;
    }
  }
}

async function selectSurveyStatusFilter(filterKey) {
  if (
    loading.value ||
    loadingViews.value ||
    loadingFilterOptions.value ||
    !visibleSurveyStatusOptions.value.some((option) => option.key === filterKey)
  ) {
    return;
  }

  if (filterKey === surveyStatusFilter.value) {
    isSurveyStatusFilterOpen.value = false;
    return;
  }

  surveyStatusFilter.value = filterKey;
  isSurveyStatusFilterOpen.value = false;
  selectedFeature.value = null;
  mapFocusRequest.value = null;
  await loadGeoJson({ autoFit: false });
}

async function reloadActiveReferenceLayers() {
  const activeLayerNames = activeReferenceLayerNames.value.slice();
  if (!activeLayerNames.length) {
    return;
  }

  await Promise.all(
    activeLayerNames.map((layerName) =>
      ensureReferenceLayerGeojson(layerName, { force: true }),
    ),
  );
}

async function onMapViewportChange(viewport) {
  const bbox = normalizeBbox(viewport?.bbox);
  if (!bbox) {
    return;
  }
  if (isSameBbox(currentMapViewport.value?.bbox, bbox)) {
    return;
  }

  currentMapViewport.value = {
    bbox,
    zoom: viewport?.zoom ?? null,
  };

  if (selectedView.value && !loadingViews.value) {
    await loadGeoJson({ autoFit: false });
    await reloadActiveReferenceLayers();
  }
}

function setReferenceLayerLoading(layerName, isLoading) {
  if (!layerName) {
    return;
  }

  if (isLoading) {
    loadingReferenceLayerNames.value = Array.from(
      new Set([...loadingReferenceLayerNames.value, layerName]),
    );
    return;
  }

  loadingReferenceLayerNames.value = loadingReferenceLayerNames.value.filter(
    (name) => name !== layerName,
  );
}

async function ensureReferenceLayerGeojson(layerName, { force = false } = {}) {
  if (!force && referenceLayerGeojsonByName.value[layerName]) {
    return true;
  }

  setReferenceLayerLoading(layerName, true);
  try {
    const payload = await fetchReferenceLayer(layerName, buildMapRequestOptions());
    referenceLayerGeojsonByName.value = {
      ...referenceLayerGeojsonByName.value,
      [layerName]: payload,
    };
    return true;
  } catch (loadError) {
    if (isUnauthorizedError(loadError)) {
      return false;
    }
    info(`${loadError.message || loadError}`, "参考图层未加载");
    return false;
  } finally {
    setReferenceLayerLoading(layerName, false);
  }
}

async function loadReferenceLayers() {
  try {
    const payload = await listReferenceLayers();
    referenceLayers.value = payload;
    activeReferenceLayerNames.value = payload
      .filter((layer) => layer.default_visible)
      .map((layer) => layer.name);
    await Promise.all(
      activeReferenceLayerNames.value.map((layerName) =>
        ensureReferenceLayerGeojson(layerName),
      ),
    );
  } catch (loadError) {
    referenceLayers.value = [];
    activeReferenceLayerNames.value = [];
    referenceLayerGeojsonByName.value = {};
    if (isUnauthorizedError(loadError)) {
      return;
    }
    info(`${loadError.message || loadError}`, "参考图层未加载");
  }
}

async function toggleReferenceLayer(layerName) {
  if (activeReferenceLayerNames.value.includes(layerName)) {
    activeReferenceLayerNames.value = activeReferenceLayerNames.value.filter(
      (name) => name !== layerName,
    );
    return;
  }

  activeReferenceLayerNames.value = [...activeReferenceLayerNames.value, layerName];
  const loaded = await ensureReferenceLayerGeojson(layerName);
  if (!loaded) {
    activeReferenceLayerNames.value = activeReferenceLayerNames.value.filter(
      (name) => name !== layerName,
    );
  }
}

async function refreshViewsAndData() {
  const previousView = selectedView.value;
  const loadedViews = await loadViews();
  if (!loadedViews) {
    return;
  }

  let loadedGeoJson = true;
  if (selectedView.value === previousView) {
    loadedGeoJson = await loadGeoJson({ autoFit: false });
  }

  if (loadedGeoJson) {
    success("地图视图与点位数据已刷新。", "刷新完成");
  }
}

async function refreshWhiteMothSiteView() {
  const loadedViews = await loadViews();
  if (!loadedViews) {
    return false;
  }

  const hasWhiteMothSiteView = views.value.some(
    (view) => view.name === WHITE_MOTH_SITE_VIEW_NAME,
  );
  if (hasWhiteMothSiteView && selectedView.value !== WHITE_MOTH_SITE_VIEW_NAME) {
    shouldAutoFitOnNextViewChange = false;
    selectedView.value = WHITE_MOTH_SITE_VIEW_NAME;
    return true;
  }

  return loadGeoJson({ autoFit: false });
}

function resetWhiteMothSiteDraft() {
  whiteMothSiteDraftLocation.value = null;
  whiteMothSiteForm.value = {
    code: "",
    siteName: "",
  };
  whiteMothSiteCodeHint.value = null;
  loadingWhiteMothSiteCodeHint.value = false;
  whiteMothSiteCodeHintRequestToken += 1;
}

async function loadWhiteMothSiteCodeHint(prefix) {
  const normalizedPrefix = `${prefix || ""}`.trim().toUpperCase();
  if (!normalizedPrefix) {
    whiteMothSiteCodeHint.value = null;
    loadingWhiteMothSiteCodeHint.value = false;
    return;
  }

  const requestToken = ++whiteMothSiteCodeHintRequestToken;
  loadingWhiteMothSiteCodeHint.value = true;
  try {
    const hint = await fetchWhiteMothSiteCodeHint(normalizedPrefix);
    if (requestToken !== whiteMothSiteCodeHintRequestToken) {
      return;
    }
    whiteMothSiteCodeHint.value = hint;
  } catch {
    if (requestToken !== whiteMothSiteCodeHintRequestToken) {
      return;
    }
    // 提示失败不打断录入，仅隐藏建议编号。
    whiteMothSiteCodeHint.value = null;
  } finally {
    if (requestToken === whiteMothSiteCodeHintRequestToken) {
      loadingWhiteMothSiteCodeHint.value = false;
    }
  }
}

function applySuggestedWhiteMothSiteCode() {
  const suggested = whiteMothSiteCodeHint.value?.suggested_next_code;
  if (!suggested || isSavingWhiteMothSite.value) {
    return;
  }
  whiteMothSiteForm.value.code = suggested;
}

function startWhiteMothSiteAdd() {
  selectedFeature.value = null;
  isAddingWhiteMothSite.value = true;
  info("请在地图上点击新点位位置。", "添加点位");
}

function cancelWhiteMothSiteAdd() {
  isAddingWhiteMothSite.value = false;
  resetWhiteMothSiteDraft();
}

function toggleWhiteMothSiteAdd() {
  if (isAddingWhiteMothSite.value) {
    cancelWhiteMothSiteAdd();
    return;
  }
  startWhiteMothSiteAdd();
}

function onMapClick(location) {
  closeMapFloatingPanels();
  if (!isAddingWhiteMothSite.value) {
    closeDetail();
    return;
  }

  whiteMothSiteDraftLocation.value = {
    latitude: Number(location.latitude),
    longitude: Number(location.longitude),
  };
  selectedFeature.value = null;
}

function onWhiteMothSiteCodeInput(value) {
  whiteMothSiteForm.value.code = `${value ?? ""}`.toUpperCase();
}

function normalizeWhiteMothSiteCodeInput() {
  whiteMothSiteForm.value.code = normalizedWhiteMothSiteCode.value;
}

async function submitWhiteMothSite() {
  normalizeWhiteMothSiteCodeInput();
  if (!whiteMothSiteDraftLocation.value) {
    error("请先在地图上点击点位位置。", "新增点位失败");
    return;
  }
  if (!isCompleteWhiteMothSiteCode.value) {
    error(
      whiteMothSiteCodeError.value ||
        `请输入完整编号，例如 ${whiteMothSiteCodeExample.value}`,
      "新增点位失败",
    );
    return;
  }
  if (whiteMothSiteCodeError.value) {
    error(whiteMothSiteCodeError.value, "新增点位失败");
    return;
  }

  isSavingWhiteMothSite.value = true;
  try {
    const createdSite = await createWhiteMothSite({
      code: normalizedWhiteMothSiteCode.value,
      site_name: whiteMothSiteForm.value.siteName.trim(),
      longitude: whiteMothSiteDraftLocation.value.longitude,
      latitude: whiteMothSiteDraftLocation.value.latitude,
    });
    success(
      `点位 ${createdSite.code} 已保存到 ${createdSite.locality}。`,
      "新增成功",
    );
    isAddingWhiteMothSite.value = false;
    resetWhiteMothSiteDraft();
    await refreshWhiteMothSiteView();
  } catch (saveError) {
    if (isUnauthorizedError(saveError)) {
      return;
    }
    error(`${saveError.message || saveError}`, "新增点位失败");
  } finally {
    isSavingWhiteMothSite.value = false;
  }
}

watch(selectedView, async () => {
  const shouldAutoFit = shouldAutoFitOnNextViewChange;
  shouldAutoFitOnNextViewChange = true;
  storeSelectedView(selectedView.value);
  selectedFeature.value = null;
  clearSearch();
  isSearchPanelOpen.value = false;
  resetSurveyStatusFilter();
  resetDynamicFilters();
  resetSearchIndex();
  mapFocusRequest.value = null;
  geojsonRequestToken += 1;
  geojson.value = createEmptyFeatureCollection();
  loading.value = Boolean(selectedView.value);

  const optionsLoaded = await loadFilterOptions();
  if (optionsLoaded && selectedView.value) {
    dynamicFilterValues.value = resolveDefaultDynamicFilters();
    if (Object.keys(dynamicFilterValues.value).length) {
      // 应用默认筛选后再取一次，让调查状态计数跟随默认筛选（如年份、世代）
      await loadFilterOptions();
    }
  }
  await loadGeoJson({ autoFit: shouldAutoFit });
});

watch(matchedWhiteMothSitePrefix, (prefix) => {
  if (!prefix) {
    whiteMothSiteCodeHintRequestToken += 1;
    whiteMothSiteCodeHint.value = null;
    loadingWhiteMothSiteCodeHint.value = false;
    return;
  }
  loadWhiteMothSiteCodeHint(prefix);
});

watch(searchQuery, (keyword) => {
  if (keyword.trim()) {
    ensureSearchIndex();
  }
});

onMounted(async () => {
  await Promise.all([loadViews(), loadReferenceLayers(), loadWhiteMothSiteCodeRules()]);
});
</script>

<template>
  <section class="map-page">
    <div class="map-workspace">
      <!-- MapToolbar removed: view/layer tools live inside LeafletMap. -->

      <section class="map-search-panel" aria-label="地图点位搜索">
        <div
          class="map-control-stack rounded-xl border bg-card/95 shadow-md backdrop-blur"
          aria-label="地图快捷工具"
        >
          <Button
            type="button"
            variant="ghost"
            size="icon"
            class="map-control-icon-button"
            :class="{ 'is-active': isSearchPanelOpen || searchQuery }"
            data-testid="map-search-toggle"
            aria-label="搜索点位"
            aria-controls="map-search-popover"
            :aria-expanded="isSearchPanelOpen"
            :disabled="loadingViews || !selectedView"
            @click="toggleSearchPanel"
          >
            <Search aria-hidden="true" />
            <span
              v-if="searchQuery"
              class="map-control-icon-dot"
              aria-hidden="true"
            ></span>
          </Button>
          <Button
            v-if="supportsSurveyStatusFilter"
            type="button"
            variant="ghost"
            size="icon"
            class="map-control-icon-button"
            :class="{
              'is-active': isSurveyStatusFilterOpen || surveyStatusFilter !== 'all',
            }"
            data-testid="map-survey-status-toggle"
            aria-label="调查状态筛选"
            aria-controls="map-survey-status-filter"
            :aria-expanded="isSurveyStatusFilterOpen"
            :disabled="loadingViews || loadingFilterOptions"
            @click="toggleSurveyStatusFilterPanel"
          >
            <Filter aria-hidden="true" />
            <span
              v-if="surveyStatusFilter !== 'all'"
              class="map-control-icon-dot"
              aria-hidden="true"
            ></span>
          </Button>
        </div>

        <div class="map-panel-popovers">
          <div
            v-if="isSearchPanelOpen"
            id="map-search-popover"
            class="map-search-popover"
            data-testid="map-search-popover"
          >
            <form
              class="map-search-form rounded-xl border bg-card/95 shadow-md backdrop-blur"
              @submit.prevent="submitSearch"
            >
              <Search :size="16" class="ml-1 shrink-0 text-muted-foreground" aria-hidden="true" />
              <Input
                ref="searchInputRef"
                v-model="searchQuery"
                data-testid="map-search-input"
                type="text"
                autocomplete="off"
                enterkeyhint="search"
                aria-label="搜索编号、点位名称、属地"
                placeholder="搜索编号、点位名称、属地"
                :disabled="loadingViews || !selectedView"
                @focus="searchFocused = true"
              />
              <Button
                v-if="searchQuery"
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label="清空搜索"
                @click="clearSearch"
              >
                <X aria-hidden="true" />
              </Button>
              <Button
                type="submit"
                size="sm"
                class="map-search-submit"
                :disabled="!searchQuery.trim()"
              >
                搜索
              </Button>
            </form>

            <div
              v-if="showSearchResults"
              class="map-search-results rounded-xl border bg-card/95 shadow-md backdrop-blur"
              data-testid="map-search-results"
            >
              <Button
                v-for="result in searchResults"
                :key="result.key"
                type="button"
                variant="ghost"
                class="map-search-result"
                :data-testid="`map-search-result-${result.key}`"
                @mousedown.prevent="selectSearchResult(result)"
              >
                <strong>{{ result.title }}</strong>
                <span>{{ result.meta || "当前视图点位" }}</span>
              </Button>
              <div
                v-if="searchResults.length === 0 && loadingSearchIndex"
                class="px-3 py-4 text-center text-xs text-muted-foreground"
              >
                正在加载点位…
              </div>
              <div
                v-else-if="searchResults.length === 0"
                class="px-3 py-4 text-center text-xs text-muted-foreground"
              >
                未找到匹配点位
              </div>
            </div>
          </div>

          <div
            v-if="supportsSurveyStatusFilter && isSurveyStatusFilterOpen"
            class="map-survey-status-filter rounded-xl border bg-card/95 shadow-md backdrop-blur"
            data-testid="map-survey-status-filter"
            aria-label="调查状态筛选"
          >
            <div class="map-survey-status-segments" role="group" aria-label="调查状态">
              <Button
                v-for="option in visibleSurveyStatusOptions"
                :key="option.key"
                type="button"
                :variant="surveyStatusFilter === option.key ? 'default' : 'ghost'"
                size="sm"
                class="map-survey-status-option"
                :class="{ 'is-active': surveyStatusFilter === option.key }"
                :data-testid="`map-survey-status-${option.key}`"
                :aria-pressed="surveyStatusFilter === option.key"
                :disabled="loading || loadingViews || loadingFilterOptions"
                @click="selectSurveyStatusFilter(option.key)"
              >
                <span class="map-survey-status-option-text">{{ option.label }}</span>
                <span class="map-survey-status-option-count">
                  {{ getSurveyStatusCount(option.key) }}
                </span>
              </Button>
            </div>

            <div
              v-if="dynamicFilterFields.length"
              class="map-dynamic-filters"
              data-testid="map-dynamic-filters"
            >
              <label
                v-for="field in dynamicFilterFields"
                :key="field.key"
                class="map-dynamic-filter"
              >
                <span class="map-dynamic-filter-label">{{ field.label }}</span>
                <NativeSelect
                  :model-value="dynamicFilterValues[field.key] || ''"
                  :data-testid="`map-filter-${field.key}`"
                  :disabled="loading || loadingFilterOptions"
                  class="h-8 text-xs"
                  @update:model-value="selectDynamicFilter(field.key, $event)"
                >
                  <option value="">全部</option>
                  <option
                    v-for="option in field.options"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.label }}
                  </option>
                </NativeSelect>
              </label>
            </div>
          </div>
        </div>
      </section>

      <aside
        v-if="selectedFeature"
        class="detail-drawer"
      >
        <article class="detail-card">
          <header class="detail-header">
            <span class="detail-title">{{ featureTitle || '点位详情' }}</span>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              class="shrink-0 text-muted-foreground"
              aria-label="关闭详情"
              @click="closeDetail"
            >
              <X aria-hidden="true" />
            </Button>
          </header>
          <div class="detail-divider"></div>
          <div class="detail-body">
            <div v-for="[label, value] in featureRows" :key="label" class="detail-row">
              <span class="detail-label">{{ label }}</span>
              <span class="detail-value">{{ value }}</span>
            </div>
          </div>
          <footer v-if="canDeleteSelectedSite" class="detail-footer">
            <Button
              type="button"
              variant="destructive"
              class="w-full"
              data-testid="white-moth-site-delete-btn"
              :disabled="deleteCheckLoading"
              @click="requestDeleteWhiteMothSite"
            >
              {{ deleteCheckLoading ? "检查中…" : "删除点位" }}
            </Button>
          </footer>
        </article>
      </aside>

      <aside
        v-if="isAddingWhiteMothSite && whiteMothSiteDraftLocation"
        class="site-add-drawer"
        aria-label="新增美国白蛾点位"
      >
        <article class="site-add-card">
          <header class="detail-header">
            <span class="detail-title">新增美国白蛾点位</span>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              class="shrink-0 text-muted-foreground"
              aria-label="关闭新增点位"
              :disabled="isSavingWhiteMothSite"
              @click="cancelWhiteMothSiteAdd"
            >
              <X aria-hidden="true" />
            </Button>
          </header>
          <div class="detail-divider"></div>

          <form class="site-add-form" @submit.prevent="submitWhiteMothSite">
            <div class="site-add-location">
              <span class="detail-label">坐标</span>
              <strong data-testid="white-moth-site-location">
                {{ whiteMothSiteLocationText }}
              </strong>
            </div>

            <label class="site-add-field">
              <span>编号</span>
              <Input
                :model-value="whiteMothSiteForm.code"
                data-testid="white-moth-site-code"
                inputmode="text"
                autocomplete="off"
                :placeholder="whiteMothSiteCodeExample"
                :disabled="isSavingWhiteMothSite"
                @blur="normalizeWhiteMothSiteCodeInput"
                @update:model-value="onWhiteMothSiteCodeInput"
              />
              <small
                v-if="whiteMothSiteCodeError"
                class="text-xs text-destructive"
                data-testid="white-moth-site-code-error"
              >
                {{ whiteMothSiteCodeError }}
              </small>
            </label>

            <div class="site-add-location">
              <span class="detail-label">自动识别属地</span>
              <strong data-testid="white-moth-site-locality">
                {{ resolvedWhiteMothSiteLocality || '待识别' }}
              </strong>
            </div>

            <div
              v-if="matchedWhiteMothSitePrefix"
              class="site-add-location site-add-code-hint"
              data-testid="white-moth-site-code-hint"
            >
              <span class="detail-label">编号提示</span>
              <strong data-testid="white-moth-site-code-hint-text">
                {{ whiteMothSiteCodeHintText }}
              </strong>
              <Button
                v-if="whiteMothSiteCodeHint?.suggested_next_code && !loadingWhiteMothSiteCodeHint"
                type="button"
                variant="outline"
                size="xs"
                class="self-start"
                data-testid="white-moth-site-fill-suggested-code"
                :disabled="isSavingWhiteMothSite"
                @click="applySuggestedWhiteMothSiteCode"
              >
                填入建议编号
              </Button>
            </div>

            <label class="site-add-field">
              <span>点位名称</span>
              <Input
                v-model="whiteMothSiteForm.siteName"
                data-testid="white-moth-site-name"
                autocomplete="off"
                :disabled="isSavingWhiteMothSite"
                placeholder="可不填写"
              />
            </label>

            <div class="site-add-actions">
              <Button
                type="submit"
                data-testid="white-moth-site-submit"
                :disabled="!canSubmitWhiteMothSite"
              >
                {{ isSavingWhiteMothSite ? '保存中' : '保存点位' }}
              </Button>
              <Button
                type="button"
                variant="outline"
                :disabled="isSavingWhiteMothSite"
                @click="cancelWhiteMothSiteAdd"
              >
                取消
              </Button>
            </div>
          </form>
        </article>
      </aside>

      <section class="map-panel" aria-label="调查点位地图">
        <LeafletMap
          :auto-fit-on-data-change="autoFitOnDataChange"
          :basemap-mode="basemapMode"
          :geojson="geojson"
          :loading="loading"
          :loading-views="loadingViews"
          :map-focus-request="mapFocusRequest"
          :popup-fields="currentView.columns"
          :reference-layers="referenceLayersForMap"
          :show-point-labels="showPointLabels"
          :view-name="selectedView"
          :views="views"
          :white-moth-site-add-mode="isAddingWhiteMothSite"
          :white-moth-site-draft-location="whiteMothSiteDraftLocation"
          :white-moth-site-saving="isSavingWhiteMothSite"
          @feature-click="onFeatureClick"
          @map-click="onMapClick"
          @viewport-change="onMapViewportChange"
          @toggle-reference-layer="toggleReferenceLayer"
          @toggle-white-moth-site-add="toggleWhiteMothSiteAdd"
          @update:basemap-mode="basemapMode = $event"
          @update:show-point-labels="showPointLabels = $event"
          @update:view-name="selectedView = $event"
        />
      </section>

    </div>
  </section>

  <ConfirmDialog
    :open="showDeleteConfirm"
    :busy="isDeletingWhiteMothSite"
    title="删除点位"
    confirm-text="确认删除"
    :message="deleteConfirmMessage"
    @close="closeDeleteConfirm"
    @confirm="confirmDeleteWhiteMothSite"
  />
</template>

<style scoped>
/* 颜色一律 var(--*) 语义 token；浮层视觉（bg-card/95、backdrop-blur、圆角、边框、阴影）
 * 走模板 Tailwind 类（规范 §7），此处保留布局结构与移动端媒体查询。 */
.map-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0;
  min-height: 0;
  height: 100%;
  padding: 0;
  background: var(--background);
  color: var(--foreground);
}

.map-workspace {
  position: relative;
  flex: 1;
  min-height: 0;
  height: 100%;
  overflow: hidden;
  border: none;
  border-radius: 0;
  background: var(--background);
  box-shadow: none;
  isolation: isolate;
}

.map-workspace::before {
  position: absolute;
  inset: 0;
  z-index: 1;
  opacity: 0.24;
  background-image:
    linear-gradient(color-mix(in oklch, var(--foreground) 6%, transparent) 1px, transparent 1px),
    linear-gradient(
      90deg,
      color-mix(in oklch, var(--foreground) 6%, transparent) 1px,
      transparent 1px
    );
  background-size: 52px 52px;
  content: "";
  pointer-events: none;
}

.map-workspace::after {
  position: absolute;
  inset: 0;
  z-index: 2;
  background:
    linear-gradient(
      to bottom,
      color-mix(in oklch, var(--card) 22%, transparent),
      transparent 24%
    ),
    radial-gradient(
      circle at 50% 110%,
      color-mix(in oklch, var(--foreground) 10%, transparent),
      transparent 42%
    );
  content: "";
  pointer-events: none;
}

.map-panel {
  position: absolute;
  inset: 0;
  z-index: 0;
  display: flex;
  min-width: 0;
  min-height: 0;
}

.map-panel :deep(.map-shell) {
  flex: 1;
  min-height: 0;
  height: 100%;
  background: transparent;
}

.map-search-panel {
  position: absolute;
  top: 1.5rem;
  left: 1.5rem;
  z-index: 1004;
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  max-width: calc(100% - 3rem);
  pointer-events: auto;
}

.map-control-stack {
  display: grid;
  overflow: hidden;
}

.map-control-icon-button {
  position: relative;
  width: 2.75rem;
  height: 2.75rem;
  padding: 0;
  border-radius: 0;
  color: var(--primary);
}

.map-control-icon-button + .map-control-icon-button {
  border-top: 1px solid var(--border);
}

.map-control-icon-button.is-active {
  background: color-mix(in oklch, var(--primary) 12%, transparent);
  color: var(--primary);
}

.map-control-icon-dot {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 5px;
  height: 5px;
  border-radius: 999px;
  background: var(--destructive);
}

.map-panel-popovers {
  min-width: 0;
  width: min(342px, calc(100vw - 7.5rem));
}

.map-search-popover {
  width: 100%;
}

.map-search-form {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
}

.map-search-results {
  margin-top: 0.5rem;
  padding: 0.5rem;
}

.map-search-result {
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
  gap: 2px;
  width: 100%;
  height: auto;
  min-height: 52px;
  padding: 0.75rem;
  color: var(--foreground);
  text-align: left;
  white-space: normal;
}

.map-search-result strong,
.map-search-result span {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.map-search-result strong {
  font-size: 0.875rem;
}

.map-search-result span {
  color: var(--muted-foreground);
  font-size: 0.75rem;
  font-weight: 500;
}

.map-survey-status-filter {
  width: 100%;
  display: grid;
  gap: 0.25rem;
  padding: 0.25rem;
}

.map-survey-status-segments {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.25rem;
}

.map-survey-status-option {
  min-width: 0;
}

.map-survey-status-option-text,
.map-survey-status-option-count {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.map-survey-status-option-count {
  color: color-mix(in oklch, currentColor 76%, transparent);
  font-size: 0.72rem;
  font-weight: 700;
}

.map-dynamic-filters {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border);
}

.map-dynamic-filter {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.map-dynamic-filter-label {
  color: var(--muted-foreground);
  font-size: 0.75rem;
  font-weight: 500;
}

.map-dynamic-filter :deep([data-slot="native-select-wrapper"]) {
  width: 100%;
}

.detail-drawer,
.site-add-drawer {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 1200;
  width: min(390px, calc(100vw - 320px));
  pointer-events: none;
}

.detail-card,
.site-add-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0;
  border-left: 1px solid var(--border);
  background: color-mix(in oklch, var(--card) 96%, transparent);
  box-shadow: -18px 0 42px color-mix(in oklch, var(--foreground) 14%, transparent);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  pointer-events: auto;
  animation: detail-slide-in 180ms cubic-bezier(0.2, 0, 0, 1);
}

@keyframes detail-slide-in {
  from {
    opacity: 0;
    transform: translateX(12px);
  }

  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1.5rem;
}

.detail-title {
  min-width: 0;
  flex: 1;
  color: var(--foreground);
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-divider {
  height: 1px;
  margin: 0 1.5rem;
  background: linear-gradient(to right, var(--border), transparent);
}

.detail-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-content: start;
  gap: 0.75rem;
  padding: 1.5rem;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}

.detail-footer {
  padding: 1rem 1.5rem 1.5rem;
  border-top: 1px solid var(--border);
  background: var(--card);
}

.detail-row {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-height: 74px;
  padding: 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
}

.detail-label {
  color: var(--muted-foreground);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.detail-value {
  color: var(--foreground);
  font-size: 0.875rem;
  font-weight: 500;
  overflow-wrap: anywhere;
}

.site-add-card {
  height: auto;
  max-height: 100%;
}

.site-add-form {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 1rem 1.25rem 1.25rem;
  overflow-y: auto;
}

.site-add-location {
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
  padding: 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
}

.site-add-location strong {
  color: var(--foreground);
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}

.site-add-field {
  display: flex;
  flex-direction: column;
  gap: 0.38rem;
  color: var(--foreground);
  font-size: 0.875rem;
  font-weight: 500;
}

.site-add-code-hint {
  gap: 0.45rem;
}

.site-add-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
  padding-top: 0.25rem;
}

@media (max-width: 760px) {
  .map-workspace {
    min-height: calc(100vh - 4.25rem - 0.65rem);
    border-radius: var(--radius);
  }

  .map-search-panel {
    top: 4rem;
    left: 1rem;
    right: auto;
    max-width: calc(100% - 2rem);
  }

  .map-panel-popovers {
    width: min(286px, calc(100vw - 9.5rem));
  }

  .map-search-submit {
    display: none;
  }

  .detail-drawer,
  .site-add-drawer {
    top: auto;
    right: 0;
    bottom: 0;
    left: 0;
    width: 100%;
    height: min(62vh, 560px);
  }

  .detail-card,
  .site-add-card {
    border-top: 1px solid var(--border);
    border-left: 0;
    border-radius: var(--radius) var(--radius) 0 0;
    box-shadow: 0 -18px 42px color-mix(in oklch, var(--foreground) 14%, transparent);
  }

  .detail-body {
    grid-template-columns: 1fr;
    padding: 1.25rem;
  }

  .site-add-actions {
    grid-template-columns: 1fr;
  }
}
</style>
