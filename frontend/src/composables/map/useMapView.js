import { computed, onMounted, ref, shallowRef, watch } from "vue";

import { useToast } from "../useToast.js";
import {
  createOtherPestSite,
  createWhiteMothSite,
  deleteOtherPestSite,
  deleteOtherPestSiteCheck,
  deleteWhiteMothSite,
  deleteWhiteMothSiteCheck,
  fetchMapFilterOptions,
  fetchMapView,
  fetchOtherPestSiteCodeHint,
  fetchOtherPestSiteCodeRules,
  fetchReferenceLayer,
  fetchWhiteMothSiteCodeHint,
  fetchWhiteMothSiteCodeRules,
  listMapViews,
  listReferenceLayers,
} from "../../api/map.js";
import { isUnauthorizedError } from "../../api/http.js";
import {
  buildPopupRows,
  resolveFeatureHoverLabel,
} from "../../components/map/popupFields.js";
import {
  createEmptyFeatureCollection,
  LOCALITY_FIELD,
  readStoredSelectedView,
  SEARCH_FIELD_KEYS,
  SEARCH_RESULT_LIMIT,
  SITE_ADD_KIND_OTHER_PEST,
  SITE_ADD_KIND_WHITE_MOTH,
  SITE_ADD_TARGETS,
  storeSelectedView,
  SURVEY_STATUS_COUNT_KEYS,
  SURVEY_STATUS_FILTER_KEY,
  SURVEY_STATUS_FILTER_OPTIONS,
  WHITE_MOTH_SITE_VIEW_NAME,
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
  const whiteMothSiteCodeRules = ref(null);
  const siteDraftLocation = ref(null);
  const siteForm = ref({
    code: "",
    siteName: "",
    locality: "",
  });
  const whiteMothSiteCodeHint = ref(null);
  const loadingWhiteMothSiteCodeHint = ref(false);
  const otherPestSiteCodeRules = ref(null);
  const otherPestSiteCodeHint = ref(null);
  const loadingOtherPestSiteCodeHint = ref(false);
  const isAddingSite = ref(false);
  const isSavingSite = ref(false);
  const showDeleteConfirm = ref(false);
  const isDeletingSite = ref(false);
  const deleteCheckLoading = ref(false);
  const pendingDeleteSite = ref(null);
  let geojsonRequestToken = 0;
  let filterOptionsRequestToken = 0;
  let searchIndexRequestToken = 0;
  let whiteMothSiteCodeHintRequestToken = 0;
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

  const canDeleteSelectedSite = computed(() => {
    // 支持添加点位的图层（美国白蛾点位、其他害虫点位）同样支持按编号删除
    if (!activeSiteAddKind.value) return false;
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
    const kind = activeSiteAddKind.value;
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
  const activeSiteAddKind = computed(() => SITE_ADD_TARGETS[selectedView.value] ?? null);
  const siteAddLabel = computed(() => {
    if (activeSiteAddKind.value === SITE_ADD_KIND_WHITE_MOTH) return "添加美国白蛾点位";
    if (activeSiteAddKind.value === SITE_ADD_KIND_OTHER_PEST) return "添加其他害虫点位";
    return "";
  });
  const siteAddTitle = computed(() =>
    activeSiteAddKind.value === SITE_ADD_KIND_OTHER_PEST
      ? "新增其他害虫点位"
      : "新增美国白蛾点位",
  );
  const whiteMothSiteCodeExample = computed(
    () => whiteMothSiteCodeRules.value?.code_example || "MQ001",
  );
  const whiteMothSitePrefixLocalities = computed(
    () => whiteMothSiteCodeRules.value?.prefix_localities || {},
  );
  const normalizedWhiteMothSiteCode = computed(() =>
    siteForm.value.code.trim().toUpperCase(),
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
  const otherPestSiteCodeExample = computed(
    () => otherPestSiteCodeRules.value?.code_example || "QT0001",
  );
  const otherPestSiteLocalities = computed(
    () => otherPestSiteCodeRules.value?.localities || [],
  );
  const normalizedOtherPestSiteCode = computed(() =>
    siteForm.value.code.trim().toUpperCase(),
  );
  const otherPestSiteCodeRegex = computed(() => {
    const pattern = otherPestSiteCodeRules.value?.code_pattern || "";
    try {
      return pattern ? new RegExp(pattern) : null;
    } catch {
      return null;
    }
  });
  const isCompleteOtherPestSiteCode = computed(() =>
    Boolean(
      normalizedOtherPestSiteCode.value &&
        otherPestSiteCodeRegex.value?.test(normalizedOtherPestSiteCode.value),
    ),
  );
  const otherPestSiteCodeError = computed(() => {
    if (!otherPestSiteCodeRules.value) {
      return "正在读取编号规则";
    }

    const code = normalizedOtherPestSiteCode.value;
    if (!code) {
      return "请输入编号";
    }
    if (isCompleteOtherPestSiteCode.value) {
      return "";
    }
    // 输入过程中（QT + 不足 4 位数字）先不报红错
    if (/^Q(T\d{0,3})?$/.test(code)) {
      return "";
    }
    return `编号格式不正确，请输入类似 ${otherPestSiteCodeExample.value} 的编号`;
  });
  const otherPestSiteCodeHintText = computed(() => {
    if (loadingOtherPestSiteCodeHint.value) {
      return "正在查询最新编号…";
    }
    const hint = otherPestSiteCodeHint.value;
    if (!hint) {
      return "编号提示暂不可用";
    }
    if (hint.latest_code && hint.suggested_next_code) {
      return `当前最大编号 ${hint.latest_code}，建议新编号 ${hint.suggested_next_code}`;
    }
    if (hint.suggested_next_code) {
      return `暂无点位，建议新编号 ${hint.suggested_next_code}`;
    }
    if (hint.latest_code) {
      return `当前最大编号 ${hint.latest_code}，序号已用尽`;
    }
    return "编号提示暂不可用";
  });
  const siteCodeExample = computed(() =>
    activeSiteAddKind.value === SITE_ADD_KIND_OTHER_PEST
      ? otherPestSiteCodeExample.value
      : whiteMothSiteCodeExample.value,
  );
  const siteCodeError = computed(() =>
    activeSiteAddKind.value === SITE_ADD_KIND_OTHER_PEST
      ? otherPestSiteCodeError.value
      : whiteMothSiteCodeError.value,
  );
  const isCompleteSiteCode = computed(() =>
    activeSiteAddKind.value === SITE_ADD_KIND_OTHER_PEST
      ? isCompleteOtherPestSiteCode.value
      : isCompleteWhiteMothSiteCode.value,
  );
  const siteLocationText = computed(() => {
    if (!siteDraftLocation.value) {
      return "请在地图上点击点位位置";
    }

    const { latitude, longitude } = siteDraftLocation.value;
    return `${Number(longitude).toFixed(6)}, ${Number(latitude).toFixed(6)}`;
  });
  const canSubmitSite = computed(() => {
    if (!activeSiteAddKind.value || !siteDraftLocation.value || isSavingSite.value) {
      return false;
    }
    if (!isCompleteSiteCode.value) {
      return false;
    }
    if (activeSiteAddKind.value === SITE_ADD_KIND_OTHER_PEST) {
      return Boolean(siteForm.value.locality);
    }
    return true;
  });
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

  async function loadOtherPestSiteCodeRules() {
    try {
      otherPestSiteCodeRules.value = await fetchOtherPestSiteCodeRules();
    } catch (loadError) {
      otherPestSiteCodeRules.value = null;
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

  function resetSiteDraft() {
    siteDraftLocation.value = null;
    siteForm.value = {
      code: "",
      siteName: "",
      locality: "",
    };
    whiteMothSiteCodeHint.value = null;
    loadingWhiteMothSiteCodeHint.value = false;
    whiteMothSiteCodeHintRequestToken += 1;
    otherPestSiteCodeHint.value = null;
    loadingOtherPestSiteCodeHint.value = false;
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

  async function loadOtherPestSiteCodeHint() {
    loadingOtherPestSiteCodeHint.value = true;
    try {
      otherPestSiteCodeHint.value = await fetchOtherPestSiteCodeHint();
    } catch {
      // 提示失败不打断录入，仅隐藏建议编号。
      otherPestSiteCodeHint.value = null;
    } finally {
      loadingOtherPestSiteCodeHint.value = false;
    }
  }

  function applySuggestedSiteCode() {
    if (isSavingSite.value) {
      return;
    }
    const suggested =
      activeSiteAddKind.value === SITE_ADD_KIND_OTHER_PEST
        ? otherPestSiteCodeHint.value?.suggested_next_code
        : whiteMothSiteCodeHint.value?.suggested_next_code;
    if (!suggested) {
      return;
    }
    siteForm.value.code = suggested;
  }

  function startSiteAdd() {
    if (!activeSiteAddKind.value) {
      return;
    }
    selectedFeature.value = null;
    isAddingSite.value = true;
    if (activeSiteAddKind.value === SITE_ADD_KIND_OTHER_PEST) {
      loadOtherPestSiteCodeHint();
    }
    info("请在地图上点击新点位位置。", "添加点位");
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

  async function refreshSitePointsView() {
    if (activeSiteAddKind.value === SITE_ADD_KIND_OTHER_PEST) {
      // 当前就在其他害虫点位视图，重载数据与搜索索引即可
      resetSearchIndex();
      return loadGeoJson({ autoFit: false });
    }
    return refreshWhiteMothSiteView();
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
    if (
      activeSiteAddKind.value === SITE_ADD_KIND_OTHER_PEST &&
      !siteForm.value.locality
    ) {
      error("请选择属地。", "新增点位失败");
      return;
    }

    isSavingSite.value = true;
    try {
      const basePayload = {
        site_name: siteForm.value.siteName.trim(),
        longitude: siteDraftLocation.value.longitude,
        latitude: siteDraftLocation.value.latitude,
      };
      const createdSite =
        activeSiteAddKind.value === SITE_ADD_KIND_OTHER_PEST
          ? await createOtherPestSite({
              ...basePayload,
              code: normalizedOtherPestSiteCode.value,
              locality: siteForm.value.locality,
            })
          : await createWhiteMothSite({
              ...basePayload,
              code: normalizedWhiteMothSiteCode.value,
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

  watch(matchedWhiteMothSitePrefix, (prefix) => {
    if (activeSiteAddKind.value !== SITE_ADD_KIND_WHITE_MOTH) {
      return;
    }
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
    await Promise.all([
      loadViews(),
      loadReferenceLayers(),
      loadWhiteMothSiteCodeRules(),
      loadOtherPestSiteCodeRules(),
    ]);
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
    canDeleteSelectedSite,
    deleteConfirmMessage,
    searchResults,
    showSearchResults,
    supportsSurveyStatusFilter,
    visibleSurveyStatusOptions,
    dynamicFilterFields,
    currentView,
    activeSiteAddKind,
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
