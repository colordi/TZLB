<script setup>
import { Filter, Search, X } from "@lucide/vue";
import { computed, nextTick, onMounted, ref, shallowRef, watch } from "vue";

import { useToast } from "../composables/useToast.js";
import {
  createWhiteMothSite,
  fetchMapFilterOptions,
  fetchMapView,
  fetchReferenceLayer,
  fetchWhiteMothSiteCodeRules,
  listMapViews,
  listReferenceLayers,
} from "../api/map.js";
import { isUnauthorizedError } from "../api/http.js";
import {
  buildPopupRows,
  resolveFeatureHoverLabel,
} from "../components/map/popupFields.js";
import LeafletMap from "../components/map/LeafletMap.vue";

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
const isAddingWhiteMothSite = ref(false);
const isSavingWhiteMothSite = ref(false);
let geojsonRequestToken = 0;
let filterOptionsRequestToken = 0;
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

function getSearchResultTitle(feature) {
  return (
    resolveFeatureHoverLabel(currentView.value.columns, feature?.properties || {}, {
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

const searchableFeatures = computed(() => geojson.value?.features || []);
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
      const title = getSearchResultTitle(feature);
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
  await nextTick();
  searchInputRef.value?.focus?.({ preventScroll: true });
}

function toggleSurveyStatusFilterPanel() {
  isSurveyStatusFilterOpen.value = !isSurveyStatusFilterOpen.value;
  if (isSurveyStatusFilterOpen.value) {
    isSearchPanelOpen.value = false;
    searchFocused.value = false;
  }
}

function submitSearch() {
  if (!searchQuery.value.trim()) {
    return;
  }

  if (searchResults.value.length > 0) {
    selectSearchResult(searchResults.value[0]);
    return;
  }

  info("当前视图没有匹配点位。", "搜索无结果");
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

async function selectDynamicFilter(key, value) {
  dynamicFilterValues.value = { ...dynamicFilterValues.value, [key]: value };
  selectedFeature.value = null;
  mapFocusRequest.value = null;
  await loadGeoJson({ autoFit: false });
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
const resolvedWhiteMothSiteLocality = computed(() => {
  const code = normalizedWhiteMothSiteCode.value;
  if (!code || !whiteMothSiteCodeRegex.value?.test(code)) {
    return "";
  }
  return whiteMothSitePrefixLocalities.value[code.slice(0, 2)] || "";
});
const whiteMothSiteCodeError = computed(() => {
  if (!whiteMothSiteCodeRules.value) {
    return "正在读取编号规则";
  }

  const code = normalizedWhiteMothSiteCode.value;
  if (!code) {
    return "请输入编号";
  }
  if (!whiteMothSiteCodeRegex.value?.test(code) || !resolvedWhiteMothSiteLocality.value) {
    return `编号格式不正确，请输入类似 ${whiteMothSiteCodeExample.value} 的编号`;
  }
  return "";
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
    !whiteMothSiteCodeError.value &&
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
    const payload = await fetchMapFilterOptions(viewName);
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

function onWhiteMothSiteCodeInput(event) {
  whiteMothSiteForm.value.code = event.target.value.toUpperCase();
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
  mapFocusRequest.value = null;
  geojsonRequestToken += 1;
  geojson.value = createEmptyFeatureCollection();
  loading.value = Boolean(selectedView.value);
  await Promise.all([
    loadFilterOptions(),
    loadGeoJson({ autoFit: shouldAutoFit }),
  ]);
});

onMounted(async () => {
  await Promise.all([loadViews(), loadReferenceLayers(), loadWhiteMothSiteCodeRules()]);
});
</script>

<template>
  <section class="page-shell map-page">
    <div class="map-workspace">
      <!-- MapToolbar removed: view/layer tools live inside LeafletMap. -->

      <section class="map-search-panel" aria-label="地图点位搜索">
        <div class="map-control-stack" aria-label="地图快捷工具">
          <button
            type="button"
            class="map-control-icon-button"
            :class="{ 'is-active': isSearchPanelOpen || searchQuery }"
            data-testid="map-search-toggle"
            aria-label="搜索点位"
            aria-controls="map-search-popover"
            :aria-expanded="isSearchPanelOpen"
            :disabled="loadingViews || pointCount === 0"
            @click="toggleSearchPanel"
          >
            <Search :size="17" :stroke-width="1.7" aria-hidden="true" />
            <span
              v-if="searchQuery"
              class="map-control-icon-dot"
              aria-hidden="true"
            ></span>
          </button>
          <button
            v-if="supportsSurveyStatusFilter"
            type="button"
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
            <Filter :size="17" :stroke-width="1.7" aria-hidden="true" />
            <span
              v-if="surveyStatusFilter !== 'all'"
              class="map-control-icon-dot"
              aria-hidden="true"
            ></span>
          </button>
        </div>

        <div class="map-panel-popovers">
          <div
            v-if="isSearchPanelOpen"
            id="map-search-popover"
            class="map-search-popover"
            data-testid="map-search-popover"
          >
            <form class="map-search-form" @submit.prevent="submitSearch">
              <label class="map-search-input-wrap">
                <span class="map-search-sr-only">搜索编号、点位名称、属地</span>
                <Search :size="17" :stroke-width="2" aria-hidden="true" />
                <input
                  ref="searchInputRef"
                  v-model="searchQuery"
                  data-testid="map-search-input"
                  type="text"
                  autocomplete="off"
                  enterkeyhint="search"
                  placeholder="搜索编号、点位名称、属地"
                  :disabled="loadingViews || pointCount === 0"
                  @focus="searchFocused = true"
                />
              </label>
              <button
                v-if="searchQuery"
                type="button"
                class="map-search-clear"
                aria-label="清空搜索"
                @click="clearSearch"
              >
                <X :size="17" :stroke-width="2" aria-hidden="true" />
              </button>
              <button type="submit" class="map-search-submit" :disabled="!searchQuery.trim()">
                搜索
              </button>
            </form>

            <div
              v-if="showSearchResults"
              class="map-search-results"
              data-testid="map-search-results"
            >
              <button
                v-for="result in searchResults"
                :key="result.key"
                type="button"
                class="map-search-result"
                :data-testid="`map-search-result-${result.key}`"
                @mousedown.prevent="selectSearchResult(result)"
              >
                <strong>{{ result.title }}</strong>
                <span>{{ result.meta || "当前视图点位" }}</span>
              </button>
              <div v-if="searchResults.length === 0" class="map-search-empty">
                未找到匹配点位
              </div>
            </div>
          </div>

          <div
            v-if="supportsSurveyStatusFilter && isSurveyStatusFilterOpen"
            class="map-survey-status-filter"
            data-testid="map-survey-status-filter"
            aria-label="调查状态筛选"
          >
            <div class="map-survey-status-segments" role="group" aria-label="调查状态">
              <button
                v-for="option in visibleSurveyStatusOptions"
                :key="option.key"
                type="button"
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
              </button>
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
                <select
                  :value="dynamicFilterValues[field.key] || ''"
                  :data-testid="`map-filter-${field.key}`"
                  :disabled="loading || loadingFilterOptions"
                  @change="selectDynamicFilter(field.key, $event.target.value)"
                >
                  <option value="">全部</option>
                  <option
                    v-for="option in field.options"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.label }}
                  </option>
                </select>
              </label>
            </div>
          </div>
        </div>
      </section>

      <aside
        v-if="selectedFeature"
        class="detail-drawer"
      >
        <article class="panel-card detail-card">
          <header class="detail-header">
            <span class="detail-title">{{ featureTitle || '点位详情' }}</span>
            <button
              type="button"
              class="detail-close-btn"
              aria-label="关闭详情"
              @click="closeDetail"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </header>
          <div class="detail-divider"></div>
          <div class="detail-body">
            <div v-for="[label, value] in featureRows" :key="label" class="detail-row">
              <span class="detail-label">{{ label }}</span>
              <span class="detail-value">{{ value }}</span>
            </div>
          </div>
        </article>
      </aside>

      <aside
        v-if="isAddingWhiteMothSite && whiteMothSiteDraftLocation"
        class="site-add-drawer"
        aria-label="新增美国白蛾点位"
      >
        <article class="panel-card site-add-card">
          <header class="detail-header">
            <span class="detail-title">新增美国白蛾点位</span>
            <button
              type="button"
              class="detail-close-btn"
              aria-label="关闭新增点位"
              :disabled="isSavingWhiteMothSite"
              @click="cancelWhiteMothSiteAdd"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
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
              <input
                :value="whiteMothSiteForm.code"
                data-testid="white-moth-site-code"
                inputmode="text"
                autocomplete="off"
                :placeholder="whiteMothSiteCodeExample"
                :disabled="isSavingWhiteMothSite"
                @blur="normalizeWhiteMothSiteCodeInput"
                @input="onWhiteMothSiteCodeInput"
              />
              <small
                v-if="whiteMothSiteCodeError"
                class="site-add-error"
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

            <label class="site-add-field">
              <span>点位名称</span>
              <input
                v-model="whiteMothSiteForm.siteName"
                data-testid="white-moth-site-name"
                autocomplete="off"
                :disabled="isSavingWhiteMothSite"
                placeholder="可不填写"
              />
            </label>

            <div class="site-add-actions">
              <button
                type="submit"
                data-testid="white-moth-site-submit"
                :disabled="!canSubmitWhiteMothSite"
              >
                {{ isSavingWhiteMothSite ? '保存中' : '保存点位' }}
              </button>
              <button
                type="button"
                class="button-secondary"
                :disabled="isSavingWhiteMothSite"
                @click="cancelWhiteMothSiteAdd"
              >
                取消
              </button>
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
</template>

<style scoped>
.map-page {
  flex: 1;
  gap: 0;
  min-height: 0;
  padding: 0;
}

.map-workspace {
  position: relative;
  flex: 1;
  min-height: calc(100vh - var(--header-h-map, 52px) - 2rem);
  overflow: hidden;
  border: 1px solid color-mix(in oklch, var(--color-border) 72%, transparent);
  border-radius: var(--radius-xl);
  background:
    radial-gradient(circle at 18% 24%, color-mix(in oklch, var(--color-primary) 10%, transparent) 0 9%, transparent 9.4%),
    radial-gradient(circle at 74% 19%, color-mix(in oklch, var(--color-nav) 9%, transparent) 0 13%, transparent 13.6%),
    var(--color-map-land);
  box-shadow: var(--shadow-card);
  isolation: isolate;
}

.map-workspace::before {
  position: absolute;
  inset: 0;
  z-index: 1;
  opacity: 0.24;
  background-image:
    linear-gradient(color-mix(in oklch, var(--color-text) 6%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in oklch, var(--color-text) 6%, transparent) 1px, transparent 1px);
  background-size: 52px 52px;
  content: "";
  pointer-events: none;
}

.map-workspace::after {
  position: absolute;
  inset: 0;
  z-index: 2;
  background:
    linear-gradient(to bottom, color-mix(in oklch, var(--color-surface) 22%, transparent), transparent 24%),
    radial-gradient(circle at 50% 110%, color-mix(in oklch, var(--color-text) 10%, transparent), transparent 42%);
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
  border: 1px solid color-mix(in oklch, var(--color-border) 82%, transparent);
  border-radius: 9px;
  background: var(--color-surface);
  box-shadow: 0 8px 22px rgba(18, 52, 29, 0.1);
}

.map-control-icon-button {
  position: relative;
  min-height: 0;
  width: 2.75rem;
  height: 2.75rem;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--color-primary-strong);
  transition: all 0.2s ease;
  transform: none;
}

.map-control-icon-button + .map-control-icon-button {
  border-top: 1px solid color-mix(in oklch, var(--color-border) 82%, transparent);
}

.map-control-icon-button:hover:not(:disabled) {
  background: color-mix(in oklch, var(--color-primary) 8%, white);
  color: var(--color-primary-strong);
  transform: none;
}

.map-control-icon-button.is-active {
  background: color-mix(in oklch, var(--color-primary) 12%, white);
  color: var(--color-primary);
}

.map-control-icon-button:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.map-control-icon-button svg {
  width: 17px;
  height: 17px;
}

.map-control-icon-dot {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 5px;
  height: 5px;
  border-radius: var(--radius-pill);
  background: var(--color-danger);
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
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  border: 1px solid color-mix(in oklch, var(--color-border) 88%, transparent);
  border-radius: var(--radius-lg);
  background: color-mix(in oklch, var(--color-surface) 94%, transparent);
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(12px);
}

.map-search-input-wrap {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-muted);
}

.map-search-input-wrap > svg {
  width: 17px;
  height: 17px;
  flex: 0 0 auto;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.map-search-input-wrap input {
  appearance: none;
  -webkit-appearance: none;
  min-width: 0;
  min-height: 36px;
  padding: 0 var(--space-2);
  border: 0;
  background: transparent;
  box-shadow: none;
  color: var(--color-text);
  font-size: var(--text-sm);
  font-weight: 650;
}

.map-search-input-wrap input:focus {
  box-shadow: none;
}

.map-search-input-wrap input:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.map-search-clear,
.map-search-submit {
  min-height: 34px;
  border-radius: var(--radius-sm);
  box-shadow: none;
  transform: none;
}

.map-search-clear {
  width: 34px;
  padding: 0;
  background: transparent;
  color: var(--color-text-muted);
  font-size: 20px;
  line-height: 1;
}

.map-search-clear:hover {
  background: var(--color-surface-container);
  box-shadow: none;
  transform: none;
}

.map-search-submit {
  padding: 0 var(--space-4);
  font-size: var(--text-xs);
  font-weight: 800;
}

.map-search-submit:disabled {
  opacity: 0.45;
}

.map-survey-status-filter {
  width: 100%;
  display: grid;
  gap: var(--space-1);
  padding: var(--space-1);
  border: 1px solid color-mix(in oklch, var(--color-border) 88%, transparent);
  border-radius: var(--radius-lg);
  background: color-mix(in oklch, var(--color-surface) 94%, transparent);
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(12px);
}

.map-survey-status-segments {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-1);
}

.map-survey-status-option {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  min-width: 0;
  min-height: 34px;
  padding: 0 var(--space-2);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  box-shadow: none;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: 800;
  line-height: 1;
  transform: none;
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
  font-weight: 850;
}

.map-survey-status-option:hover:not(:disabled) {
  background: var(--color-primary-soft);
  box-shadow: none;
  color: var(--color-text);
  transform: none;
}

.map-survey-status-option.is-active {
  border-color: color-mix(in oklch, var(--color-primary) 68%, transparent);
  background: var(--color-primary);
  color: var(--color-surface);
}

.map-survey-status-option:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.map-dynamic-filters {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
  margin-top: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid color-mix(in oklch, var(--color-border) 80%, transparent);
}

.map-dynamic-filter {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.map-dynamic-filter-label {
  color: var(--color-text-muted);
  font-size: var(--text-2xs);
  font-weight: 700;
  letter-spacing: 0.04em;
}

.map-dynamic-filter select {
  width: 100%;
  min-height: 30px;
  padding: 0 var(--space-2);
  border: 1px solid color-mix(in oklch, var(--color-border) 88%, transparent);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--text-xs);
  font-weight: 600;
}

.map-dynamic-filter select:disabled {
  opacity: 0.58;
  cursor: not-allowed;
}

.map-search-results {
  margin-top: var(--space-2);
  padding: var(--space-2);
  border: 1px solid color-mix(in oklch, var(--color-border) 88%, transparent);
  border-radius: var(--radius-lg);
  background: color-mix(in oklch, var(--color-surface) 96%, transparent);
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(12px);
}

.map-search-result {
  width: 100%;
  min-height: 52px;
  justify-content: flex-start;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  background: transparent;
  box-shadow: none;
  color: var(--color-text);
  text-align: left;
}

.map-search-result:hover {
  background: var(--color-primary-soft);
  box-shadow: none;
  transform: none;
}

.map-search-result strong,
.map-search-result span {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.map-search-result strong {
  font-size: var(--text-sm);
}

.map-search-result span,
.map-search-empty {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: 650;
}

.map-search-empty {
  padding: var(--space-4);
  text-align: center;
}

.map-search-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
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
  border: 0;
  border-left: 1px solid var(--color-border);
  border-radius: 0;
  background: color-mix(in oklch, var(--color-surface) 96%, transparent);
  box-shadow: -18px 0 42px color-mix(in oklch, var(--color-text) 14%, transparent);
  backdrop-filter: blur(14px);
  pointer-events: auto;
  animation: detail-slide-in 0.2s cubic-bezier(0.16, 1, 0.3, 1);
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
  padding: var(--space-6);
}

.detail-title {
  min-width: 0;
  flex: 1;
  font-size: var(--text-xl);
  line-height: 1.25;
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-close-btn {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: none;
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--motion-fast) var(--ease-standard);
}

.detail-close-btn:hover {
  background: var(--color-surface-container);
  color: var(--color-ink);
}

.detail-divider {
  height: 1px;
  background: linear-gradient(to right, var(--color-line-strong), transparent);
  margin: 0 var(--space-6);
}

.detail-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-content: start;
  gap: var(--space-3);
  padding: var(--space-6);
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}

.detail-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-height: 74px;
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-container-lowest);
}

.detail-label {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.detail-value {
  color: var(--color-text);
  font-size: var(--text-sm);
  font-weight: 600;
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
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-container-lowest);
}

.site-add-location strong {
  color: var(--color-ink);
  font-size: 0.92rem;
  overflow-wrap: anywhere;
}

.site-add-field {
  display: flex;
  flex-direction: column;
  gap: 0.38rem;
  color: var(--color-ink);
  font-size: 0.86rem;
  font-weight: 700;
}

.site-add-field input {
  min-width: 0;
  width: 100%;
  padding: 0.72rem 0.82rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-ink);
  font: inherit;
  font-weight: 650;
  outline: none;
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard);
}

.site-add-field input:focus {
  border-color: var(--color-primary);
  box-shadow: var(--focus-ring);
}

.site-add-field input:disabled {
  cursor: not-allowed;
  opacity: 0.68;
}

.site-add-error {
  color: var(--color-danger);
  font-size: 0.76rem;
  font-weight: 700;
  line-height: 1.35;
}

.site-add-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
  padding-top: 0.25rem;
}

@media (max-width: 760px) {
  .map-workspace {
    min-height: calc(100vh - var(--app-mobile-header-height) - 0.65rem);
    border-radius: var(--radius-lg);
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

  .map-search-form {
    grid-template-columns: minmax(0, 1fr) auto auto;
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
    border-top: 1px solid var(--color-border);
    border-left: 0;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    box-shadow: 0 -18px 42px color-mix(in oklch, var(--color-text) 14%, transparent);
  }

  .detail-body {
    grid-template-columns: 1fr;
    padding: var(--space-5);
  }

  .site-add-actions {
    grid-template-columns: 1fr;
  }

}
</style>
