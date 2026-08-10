import { computed, onMounted, ref, shallowRef, watch } from "vue";

import { useToast } from "../useToast.js";
import {
  createMapSite,
  deleteOtherPestSite,
  deleteOtherPestSiteCheck,
  deleteWhiteMothSite,
  deleteWhiteMothSiteCheck,
  fetchMapFilterOptions,
  fetchMapView,
  fetchReferenceLayer,
  fetchSiteCodeHint,
  listMapViews,
  listReferenceLayers,
} from "../../api/map.js";
import { isUnauthorizedError } from "../../api/http.js";
import {
  buildPopupRows,
  resolveFeatureHoverLabel,
} from "../../components/map/popupFields.js";
import { isValidLngLatPair } from "../../components/map/leaflet/geometry.js";
import {
  createEmptyFeatureCollection,
  DELETABLE_BASE_TABLES,
  LOCALITY_FIELD,
  LOCALITY_MODE_MANUAL,
  LOCALITY_MODE_PREFIX,
  matchSitePrefix,
  readStoredSelectedView,
  resolveSiteAddConfig,
  SEARCH_FIELD_KEYS,
  SEARCH_RESULT_LIMIT,
  SITE_ADD_KIND_OTHER_PEST,
  SITE_ADD_KIND_WHITE_MOTH,
  storeSelectedView,
  SURVEY_STATUS_COUNT_KEYS,
  SURVEY_STATUS_FILTER_KEY,
  SURVEY_STATUS_FILTER_OPTIONS,
} from "./constants.js";

/**
 * Map page state: data loading, filters, search, reference layers, site editor.
 */
export function useMapView() {
  const { error, info, success } = useToast();

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
  const isSearchPanelOpen = ref(false);
  const surveyStatusFilter = ref("all");
  const isSurveyStatusFilterOpen = ref(false);
  const dynamicFilterValues = ref({});
  const mapFocusRequest = ref(null);
  const siteDraftLocation = ref(null);
  const siteForm = ref({
    code: "",
    siteName: "",
    locality: "",
  });
  const siteCodeHint = ref(null);
  const loadingSiteCodeHint = ref(false);
  const isAddingSite = ref(false);
  const isSavingSite = ref(false);
  const showDeleteConfirm = ref(false);
  const isDeletingSite = ref(false);
  const deleteCheckLoading = ref(false);
  const pendingDeleteSite = ref(null);
  let geojsonRequestToken = 0;
  let filterOptionsRequestToken = 0;
  let searchIndexRequestToken = 0;
  let siteCodeHintRequestToken = 0;
  let shouldAutoFitOnNextViewChange = true;
  let mapFocusRequestToken = 0;

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

  /**
   * 外部地图跳转链接：高德 URI API（点位几何为 WGS84，coordinate=wgs84
   * 直传 GPS 原始坐标）。callnative=1 时页面会尝试拉起高德 App
   * （Android/iOS 均支持），未安装时回落到高德网页版。
   */
  const externalMapUrl = computed(() => {
    const geometry = selectedFeature.value?.geometry;
    if (geometry?.type !== "Point" || !isValidLngLatPair(geometry.coordinates)) return "";
    const [lng, lat] = geometry.coordinates.map(Number);
    const name = encodeURIComponent(featureTitle.value || "调查点位");
    return `https://uri.amap.com/marker?position=${lng},${lat}&name=${name}&coordinate=wgs84&callnative=1`;
  });

  const canDeleteSelectedSite = computed(() => {
    // 通用删除未做：仅美国白蛾/其他害虫基表保留旧删除入口
    const baseTable = siteAddConfig.value?.base_table || "";
    if (!DELETABLE_BASE_TABLES.has(baseTable)) return false;
    if (!selectedFeature.value?.properties) return false;
    const code = `${selectedFeature.value.properties["编号"] ?? ""}`.trim();
    return code !== "";
  });

  const deleteConfirmMessage = computed(() => {
    const site = pendingDeleteSite.value;
    if (!site) return "";
    const kindLabel =
      site.kind === SITE_ADD_KIND_OTHER_PEST ? "其他害虫点位" : "美国白蛾点位";
    const label = `${site.locality || "未知属地"} · ${site.site_name || "未命名"}`;
    if (!site.survey_record_count) {
      return `将删除${kindLabel}「${site.code}」（${label}）。此操作仅删除点位，不删除已关联的调查记录和台账，且不可撤销。`;
    }
    return `将删除${kindLabel}「${site.code}」（${label}）。该编号当前关联 ${site.survey_record_count} 条调查记录，删除点位后这些调查记录和台账将变为悬空数据。此操作不可撤销，确认仍要删除吗？`;
  });

  function closeDeleteConfirm() {
    showDeleteConfirm.value = false;
    pendingDeleteSite.value = null;
  }

  async function requestDeleteSite() {
    if (isDeletingSite.value || deleteCheckLoading.value) return;
    const baseTable = siteAddConfig.value?.base_table || "";
    const kind =
      baseTable === "其他害虫点位基础表"
        ? SITE_ADD_KIND_OTHER_PEST
        : baseTable === "美国白蛾点位基础表"
          ? SITE_ADD_KIND_WHITE_MOTH
          : "";
    const code = `${selectedFeature.value?.properties?.["编号"] ?? ""}`.trim();
    if (!kind || !code) {
      error("未读取到点位编号。", "删除失败");
      return;
    }

    deleteCheckLoading.value = true;
    try {
      const result =
        kind === SITE_ADD_KIND_OTHER_PEST
          ? await deleteOtherPestSiteCheck(code)
          : await deleteWhiteMothSiteCheck(code);
      if (!result.exists) {
        error("点位已被删除或不存在。", "删除失败");
        closeDetail();
        await refreshSitePointsView();
        return;
      }
      pendingDeleteSite.value = { ...result, kind };
      showDeleteConfirm.value = true;
    } catch (checkError) {
      if (isUnauthorizedError(checkError)) return;
      error(`${checkError.message || checkError}`, "删除前检查失败");
    } finally {
      deleteCheckLoading.value = false;
    }
  }

  async function confirmDeleteSite() {
    const site = pendingDeleteSite.value;
    if (!site) {
      closeDeleteConfirm();
      return;
    }

    isDeletingSite.value = true;
    try {
      const deleted =
        site.kind === SITE_ADD_KIND_OTHER_PEST
          ? await deleteOtherPestSite(site.code)
          : await deleteWhiteMothSite(site.code);
      success(`点位 ${deleted.code} 已删除。`, "删除成功");
      closeDeleteConfirm();
      closeDetail();
      await refreshSitePointsView();
    } catch (deleteError) {
      if (isUnauthorizedError(deleteError)) {
        return;
      }
      error(`${deleteError.message || deleteError}`, "删除失败");
    } finally {
      isDeletingSite.value = false;
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
    if (isAddingSite.value) {
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

  const currentView = computed(
    () => views.value.find((view) => view.name === selectedView.value) || { columns: [] },
  );
  const siteAddConfig = computed(() => resolveSiteAddConfig(currentView.value));
  const canAddSite = computed(() => Boolean(siteAddConfig.value?.enabled));
  /** 兼容旧面板：manual=其他害虫样式；prefix=前缀识别属地 */
  const activeSiteAddKind = computed(() => {
    if (!siteAddConfig.value?.enabled) return null;
    return siteAddConfig.value.locality_mode === LOCALITY_MODE_MANUAL
      ? SITE_ADD_KIND_OTHER_PEST
      : SITE_ADD_KIND_WHITE_MOTH;
  });
  const siteAddLabel = computed(() => {
    if (!canAddSite.value) return "";
    const label = currentView.value.label || currentView.value.name || "点位";
    return `添加点位（${label}）`;
  });
  const siteAddTitle = computed(() => {
    if (!canAddSite.value) return "新增点位";
    const label = currentView.value.label || currentView.value.name || "任务";
    return `新增点位 · ${label}`;
  });
  const siteCodeExample = computed(
    () => siteAddConfig.value?.code_example || "MQ001",
  );
  const sitePrefixLocalities = computed(
    () => siteAddConfig.value?.prefix_localities || {},
  );
  const siteLocalities = computed(() => siteAddConfig.value?.localities || []);
  const siteSerialWidth = computed(() =>
    Number(siteAddConfig.value?.serial_width || 3),
  );
  const isManualLocalityMode = computed(
    () => siteAddConfig.value?.locality_mode === LOCALITY_MODE_MANUAL,
  );
  const normalizedSiteCode = computed(() => siteForm.value.code.trim().toUpperCase());
  const siteCodeRegex = computed(() => {
    const pattern = siteAddConfig.value?.code_pattern || "";
    try {
      return pattern ? new RegExp(pattern) : null;
    } catch {
      return null;
    }
  });
  const matchedSitePrefix = computed(() => {
    if (!siteAddConfig.value?.enabled) return "";
    if (isManualLocalityMode.value) {
      return siteAddConfig.value.fixed_prefix || "";
    }
    return matchSitePrefix(normalizedSiteCode.value, sitePrefixLocalities.value);
  });
  const resolvedSiteLocality = computed(() => {
    if (isManualLocalityMode.value) {
      return siteForm.value.locality || "";
    }
    if (!matchedSitePrefix.value) return "";
    return sitePrefixLocalities.value[matchedSitePrefix.value] || "";
  });
  const isCompleteSiteCode = computed(() => {
    const code = normalizedSiteCode.value;
    if (!code || !siteCodeRegex.value?.test(code)) return false;
    if (isManualLocalityMode.value) return true;
    return Boolean(
      matchedSitePrefix.value &&
        code.slice(matchedSitePrefix.value.length).length === siteSerialWidth.value,
    );
  });
  const siteCodeError = computed(() => {
    if (!siteAddConfig.value?.enabled) {
      return "当前视图不支持添加点位";
    }
    const code = normalizedSiteCode.value;
    if (!code) return "请输入编号";
    if (isManualLocalityMode.value) {
      if (isCompleteSiteCode.value) return "";
      const prefix = siteAddConfig.value.fixed_prefix || "QT";
      // 输入过程中先不报红错
      if (new RegExp(`^${prefix}\\d{0,${siteSerialWidth.value - 1}}$`).test(code)) {
        return "";
      }
      if (code === prefix.slice(0, code.length) && code.length < prefix.length) {
        return "";
      }
      return `编号格式不正确，请输入类似 ${siteCodeExample.value} 的编号`;
    }
    if (matchedSitePrefix.value) {
      // 前缀已识别：完整编号才可提交；输入过程中不报红错
      return "";
    }
    if (/^[A-Z]$/.test(code)) return "";
    return `编号格式不正确，请输入类似 ${siteCodeExample.value} 的编号`;
  });
  const siteCodeHintText = computed(() => {
    if (loadingSiteCodeHint.value) {
      return isManualLocalityMode.value
        ? "正在查询最新编号…"
        : "正在查询该属地最新编号…";
    }
    const hint = siteCodeHint.value;
    if (!hint) return "编号提示暂不可用";
    if (!isManualLocalityMode.value && hint.prefix !== matchedSitePrefix.value) {
      return "编号提示暂不可用";
    }
    if (hint.latest_code && hint.suggested_next_code) {
      return `当前最大编号 ${hint.latest_code}，建议新编号 ${hint.suggested_next_code}`;
    }
    if (hint.suggested_next_code) {
      return isManualLocalityMode.value
        ? `暂无点位，建议新编号 ${hint.suggested_next_code}`
        : `该属地暂无点位，建议新编号 ${hint.suggested_next_code}`;
    }
    if (hint.latest_code) {
      return `当前最大编号 ${hint.latest_code}，序号已用尽`;
    }
    return "编号提示暂不可用";
  });
  // 兼容 SiteEditorPanel 旧 prop 名
  const whiteMothSiteCodeExample = siteCodeExample;
  const otherPestSiteCodeExample = siteCodeExample;
  const otherPestSiteLocalities = siteLocalities;
  const resolvedWhiteMothSiteLocality = resolvedSiteLocality;
  const matchedWhiteMothSitePrefix = matchedSitePrefix;
  const whiteMothSiteCodeHintText = computed(() =>
    isManualLocalityMode.value ? "" : siteCodeHintText.value,
  );
  const otherPestSiteCodeHintText = computed(() =>
    isManualLocalityMode.value ? siteCodeHintText.value : "",
  );
  const whiteMothSiteCodeHint = computed(() =>
    isManualLocalityMode.value ? null : siteCodeHint.value,
  );
  const otherPestSiteCodeHint = computed(() =>
    isManualLocalityMode.value ? siteCodeHint.value : null,
  );
  const loadingWhiteMothSiteCodeHint = loadingSiteCodeHint;
  const loadingOtherPestSiteCodeHint = loadingSiteCodeHint;
  const siteLocationText = computed(() => {
    if (!siteDraftLocation.value) {
      return "请在地图上点击点位位置";
    }

    const { latitude, longitude } = siteDraftLocation.value;
    return `${Number(longitude).toFixed(6)}, ${Number(latitude).toFixed(6)}`;
  });
  const canSubmitSite = computed(() => {
    if (!canAddSite.value || !siteDraftLocation.value || isSavingSite.value) {
      return false;
    }
    if (!isCompleteSiteCode.value) {
      return false;
    }
    if (isManualLocalityMode.value) {
      return Boolean(siteForm.value.locality);
    }
    return true;
  });
  const hasCodeListFilter = computed(() =>
    Boolean(siteAddConfig.value?.has_code_list_filter),
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
        {},
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

  async function ensureReferenceLayerGeojson(layerName) {
    if (referenceLayerGeojsonByName.value[layerName]) {
      return true;
    }

    setReferenceLayerLoading(layerName, true);
    try {
      const payload = await fetchReferenceLayer(layerName, {});
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

  async function refreshSitePointsView() {
    resetSearchIndex();
    return loadGeoJson({ autoFit: false });
  }

  function resetSiteDraft() {
    siteDraftLocation.value = null;
    siteForm.value = {
      code: "",
      siteName: "",
      locality: "",
    };
    siteCodeHint.value = null;
    loadingSiteCodeHint.value = false;
    siteCodeHintRequestToken += 1;
  }



  function applySuggestedSiteCode() {
    if (isSavingSite.value) {
      return;
    }
    const suggested = siteCodeHint.value?.suggested_next_code;
    if (!suggested) {
      return;
    }
    siteForm.value.code = suggested;
  }

  async function loadSiteCodeHint(prefix = "") {
    if (!canAddSite.value || !selectedView.value) {
      siteCodeHint.value = null;
      loadingSiteCodeHint.value = false;
      return;
    }
    if (!isManualLocalityMode.value && !prefix) {
      siteCodeHint.value = null;
      loadingSiteCodeHint.value = false;
      return;
    }

    const requestToken = ++siteCodeHintRequestToken;
    loadingSiteCodeHint.value = true;
    try {
      const hint = await fetchSiteCodeHint(selectedView.value, prefix);
      if (requestToken !== siteCodeHintRequestToken) {
        return;
      }
      siteCodeHint.value = hint;
    } catch {
      if (requestToken !== siteCodeHintRequestToken) {
        return;
      }
      siteCodeHint.value = null;
    } finally {
      if (requestToken === siteCodeHintRequestToken) {
        loadingSiteCodeHint.value = false;
      }
    }
  }

  function startSiteAdd() {
    if (!canAddSite.value) {
      return;
    }
    selectedFeature.value = null;
    isAddingSite.value = true;
    if (isManualLocalityMode.value) {
      loadSiteCodeHint();
    }
    if (hasCodeListFilter.value) {
      info(
        "本任务视图限定了编号清单，新增编号必须在清单内，否则无法保存。",
        "添加点位",
      );
    } else {
      info("请在地图上点击新点位位置。", "添加点位");
    }
  }

  function cancelSiteAdd() {
    isAddingSite.value = false;
    resetSiteDraft();
  }

  function toggleSiteAdd() {
    if (isAddingSite.value) {
      cancelSiteAdd();
      return;
    }
    startSiteAdd();
  }

  function onMapClick(location) {
    closeMapFloatingPanels();
    if (!isAddingSite.value) {
      closeDetail();
      return;
    }

    siteDraftLocation.value = {
      latitude: Number(location.latitude),
      longitude: Number(location.longitude),
    };
    selectedFeature.value = null;
  }

  function onSiteCodeInput(value) {
    siteForm.value.code = `${value ?? ""}`.toUpperCase();
  }

  function normalizeSiteCodeInput() {
    siteForm.value.code = siteForm.value.code.trim().toUpperCase();
  }

  async function submitSite() {
    normalizeSiteCodeInput();
    if (!siteDraftLocation.value) {
      error("请先在地图上点击点位位置。", "新增点位失败");
      return;
    }
    if (!isCompleteSiteCode.value) {
      error(
        siteCodeError.value || `请输入完整编号，例如 ${siteCodeExample.value}`,
        "新增点位失败",
      );
      return;
    }
    if (siteCodeError.value) {
      error(siteCodeError.value, "新增点位失败");
      return;
    }
    if (isManualLocalityMode.value && !siteForm.value.locality) {
      error("请选择属地。", "新增点位失败");
      return;
    }

    isSavingSite.value = true;
    try {
      const createdSite = await createMapSite({
        view_name: selectedView.value,
        code: normalizedSiteCode.value,
        site_name: siteForm.value.siteName.trim(),
        locality: isManualLocalityMode.value ? siteForm.value.locality : undefined,
        longitude: siteDraftLocation.value.longitude,
        latitude: siteDraftLocation.value.latitude,
      });
      success(
        `点位 ${createdSite.code} 已保存到 ${createdSite.locality}。`,
        "新增成功",
      );
      isAddingSite.value = false;
      resetSiteDraft();
      await refreshSitePointsView();
    } catch (saveError) {
      if (isUnauthorizedError(saveError)) {
        return;
      }
      error(`${saveError.message || saveError}`, "新增点位失败");
    } finally {
      isSavingSite.value = false;
    }
  }

  watch(selectedView, async () => {
    const shouldAutoFit = shouldAutoFitOnNextViewChange;
    shouldAutoFitOnNextViewChange = true;
    storeSelectedView(selectedView.value);
    selectedFeature.value = null;
    // 切换图层时退出进行中的添加状态
    if (isAddingSite.value) {
      isAddingSite.value = false;
      resetSiteDraft();
    }
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

  watch(matchedSitePrefix, (prefix) => {
    if (!canAddSite.value || isManualLocalityMode.value) {
      return;
    }
    if (!prefix) {
      siteCodeHintRequestToken += 1;
      siteCodeHint.value = null;
      loadingSiteCodeHint.value = false;
      return;
    }
    loadSiteCodeHint(prefix);
  });

  watch(searchQuery, (keyword) => {
    if (keyword.trim()) {
      ensureSearchIndex();
    }
  });

  onMounted(async () => {
    await Promise.all([loadViews(), loadReferenceLayers()]);
  });


  return {
    views,
    selectedView,
    basemapMode,
    showPointLabels,
    geojson,
    loadingSearchIndex,
    loading,
    loadingViews,
    loadingFilterOptions,
    autoFitOnDataChange,
    selectedFeature,
    searchQuery,
    searchFocused,
    isSearchPanelOpen,
    surveyStatusFilter,
    isSurveyStatusFilterOpen,
    dynamicFilterValues,
    mapFocusRequest,
    siteDraftLocation,
    siteForm,
    whiteMothSiteCodeHint,
    loadingWhiteMothSiteCodeHint,
    otherPestSiteCodeHint,
    loadingOtherPestSiteCodeHint,
    isAddingSite,
    isSavingSite,
    showDeleteConfirm,
    isDeletingSite,
    deleteCheckLoading,
    SITE_ADD_KIND_OTHER_PEST,
    SITE_ADD_KIND_WHITE_MOTH,
    featureTitle,
    featureRows,
    externalMapUrl,
    canDeleteSelectedSite,
    deleteConfirmMessage,
    searchResults,
    showSearchResults,
    supportsSurveyStatusFilter,
    visibleSurveyStatusOptions,
    dynamicFilterFields,
    currentView,
    activeSiteAddKind,
    siteAddConfig,
    canAddSite,
    siteAddLabel,
    siteAddTitle,
    whiteMothSiteCodeExample,
    resolvedWhiteMothSiteLocality,
    matchedWhiteMothSitePrefix,
    whiteMothSiteCodeHintText,
    otherPestSiteCodeExample,
    otherPestSiteLocalities,
    otherPestSiteCodeHintText,
    siteCodeError,
    siteLocationText,
    canSubmitSite,
    hasCodeListFilter,
    siteCodeExample,
    referenceLayersForMap,
    closeDeleteConfirm,
    requestDeleteSite,
    confirmDeleteSite,
    getSurveyStatusCount,
    onFeatureClick,
    selectSearchResult,
    toggleSearchPanel,
    toggleSurveyStatusFilterPanel,
    submitSearch,
    clearSearch,
    closeDetail,
    selectDynamicFilter,
    selectSurveyStatusFilter,
    toggleReferenceLayer,
    toggleSiteAdd,
    onMapClick,
    onSiteCodeInput,
    normalizeSiteCodeInput,
    applySuggestedSiteCode,
    cancelSiteAdd,
    submitSite,
  };
}
