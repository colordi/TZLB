<script setup>
import { computed, onMounted, ref, watch } from "vue";

import { useToast } from "../composables/useToast.js";
import {
  fetchAdminBoundary,
  fetchMapFilterOptions,
  fetchMapView,
  listMapViews,
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

const views = ref([]);
const selectedView = ref("");
const basemapMode = ref("standard");
const showPointLabels = ref(false);
const geojson = ref(createEmptyFeatureCollection());
const boundaryGeojson = ref(createEmptyFeatureCollection());
const activeFilters = ref({});
const filterOptions = ref({
  filterFields: [],
});
const isFilterPanelOpen = ref(false);
const openFilterMenus = ref({});
const loading = ref(false);
const loadingViews = ref(false);
const autoFitOnDataChange = ref(true);
const selectedFeature = ref(null);
let geojsonRequestToken = 0;

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

function onFeatureClick(feature) {
  selectedFeature.value = feature;
}

function closeDetail() {
  selectedFeature.value = null;
}

const currentView = computed(
  () => views.value.find((view) => view.name === selectedView.value) || { columns: [] },
);
const filterFields = computed(() => filterOptions.value.filterFields || []);
const hasFilterFields = computed(() => filterFields.value.length > 0);

const filterHint = computed(() => {
  if (hasFilterFields.value) {
    return "按当前视图筛选点位。";
  }
  return "当前视图暂无可用筛选。";
});

function normalizeFilterOptions(options = []) {
  return (options || [])
    .map((option) => {
      if (typeof option === "string") {
        return {
          value: option,
          label: option,
        };
      }
      return {
        value: `${option?.value ?? ""}`,
        label: `${option?.label ?? option?.value ?? ""}`,
      };
    })
    .filter((option) => option.value !== "");
}

function normalizeSelectedFilterValues(value) {
  const values = Array.isArray(value) ? value : [value];
  const selectedValues = values
    .map((item) => `${item ?? ""}`.trim())
    .filter((item) => item !== "");

  return Array.from(new Set(selectedValues));
}

function buildLegacyFilterFields(payload) {
  const fields = [];
  const columns = currentView.value.columns || [];
  const townships = payload?.townships || [];

  if (payload?.supports_township_filter || columns.includes("乡镇")) {
    fields.push({
      key: "乡镇",
      label: "乡镇 / 街道",
      type: "select",
      options: normalizeFilterOptions(townships),
      defaultValues: [],
    });
  }

  if (payload?.supports_survey_status_filter || columns.includes("调查日期")) {
    fields.push({
      key: "调查状态",
      label: "调查状态",
      type: "select",
      options: normalizeFilterOptions(["调查", "未调查"]),
      defaultValues: [],
    });
  }

  return fields;
}

function normalizeFilterFields(payload) {
  if (!Array.isArray(payload?.filter_fields)) {
    return buildLegacyFilterFields(payload);
  }

  return payload.filter_fields.map((field) => ({
    key: `${field.key || ""}`,
    label: `${field.label || field.key || ""}`,
    type: field.type || "select",
    options: normalizeFilterOptions(field.options || []),
    defaultValues: normalizeSelectedFilterValues(field.default_values ?? field.default_value),
  })).filter((field) => field.key && field.label);
}

function buildDefaultFilterValues(fields = filterFields.value) {
  return fields.reduce((values, field) => {
    values[field.key] = [...(field.defaultValues || [])];
    return values;
  }, {});
}

function buildFilterMenuState(fields = filterFields.value) {
  return fields.reduce((menus, field) => {
    menus[field.key] = false;
    return menus;
  }, {});
}

function isFilterMenuOpen(fieldKey) {
  return Boolean(openFilterMenus.value[fieldKey]);
}

function setFilterMenuOpen(fieldKey, open) {
  const nextState = buildFilterMenuState();
  if (open && Object.hasOwn(nextState, fieldKey)) {
    nextState[fieldKey] = true;
  }
  openFilterMenus.value = nextState;
}

function toggleFilterMenu(fieldKey) {
  setFilterMenuOpen(fieldKey, !isFilterMenuOpen(fieldKey));
}

function getFilterOptionLabel(field, value) {
  return field.options.find((option) => option.value === value)?.label || value;
}

function getFilterSummary(field) {
  if (!field.options.length) {
    return "暂无可选项";
  }

  const selectedValues = normalizeSelectedFilterValues(activeFilters.value[field.key]);
  if (!selectedValues.length) {
    return `选择${field.label}`;
  }

  const selectedLabels = selectedValues.map((value) => getFilterOptionLabel(field, value));
  if (selectedLabels.length <= 2) {
    return selectedLabels.join("、");
  }

  return `${selectedLabels.slice(0, 2).join("、")} 等 ${selectedLabels.length} 项`;
}

function hasSelectedFilterValues(fieldKey) {
  return normalizeSelectedFilterValues(activeFilters.value[fieldKey]).length > 0;
}

function isFilterSummaryMuted(field) {
  return !field.options.length || !hasSelectedFilterValues(field.key);
}

function buildActiveFilterPayload() {
  return filterFields.value.reduce((filters, field) => {
    const values = normalizeSelectedFilterValues(activeFilters.value[field.key]);
    if (values.length > 0) {
      filters[field.key] = values;
    }
    return filters;
  }, {});
}

async function loadViews() {
  loadingViews.value = true;

  try {
    const payload = await listMapViews();
    views.value = payload;
    if (!payload.length) {
      selectedView.value = "";
      geojsonRequestToken += 1;
      geojson.value = createEmptyFeatureCollection();
      return true;
    }

    if (!payload.some((view) => view.name === selectedView.value)) {
      selectedView.value = payload[0].name;
    }
    return true;
  } catch (loadError) {
    views.value = [];
    selectedView.value = "";
    geojson.value = createEmptyFeatureCollection();
    if (isUnauthorizedError(loadError)) {
      return false;
    }
    error(`${loadError.message || loadError}`, "地图视图读取失败");
    return false;
  } finally {
    loadingViews.value = false;
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
    const filters = buildActiveFilterPayload();
    const payload = await fetchMapView(viewName, filters);
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

async function loadFilterOptions() {
  if (!selectedView.value) {
    filterOptions.value = {
      filterFields: [],
    };
    activeFilters.value = {};
    openFilterMenus.value = {};
    return;
  }

  try {
    const payload = await fetchMapFilterOptions(selectedView.value);
    filterOptions.value = {
      filterFields: normalizeFilterFields(payload),
    };
    activeFilters.value = buildDefaultFilterValues(filterOptions.value.filterFields);
    openFilterMenus.value = buildFilterMenuState(filterOptions.value.filterFields);
  } catch (loadError) {
    filterOptions.value = {
      filterFields: buildLegacyFilterFields({}),
    };
    activeFilters.value = buildDefaultFilterValues(filterOptions.value.filterFields);
    openFilterMenus.value = buildFilterMenuState(filterOptions.value.filterFields);
    if (isUnauthorizedError(loadError)) {
      return;
    }
    error(`${loadError.message || loadError}`, "筛选配置读取失败");
  }
}

async function loadAdminBoundary() {
  try {
    boundaryGeojson.value = await fetchAdminBoundary();
  } catch (loadError) {
    boundaryGeojson.value = createEmptyFeatureCollection();
    if (isUnauthorizedError(loadError)) {
      return;
    }
    info(`${loadError.message || loadError}`, "行政区边界未加载");
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

function applyFilter() {
  loadGeoJson({ autoFit: false });
}

function resetFilter() {
  activeFilters.value = buildDefaultFilterValues();
  loadGeoJson({ autoFit: false });
  info("筛选条件已恢复默认。", "已刷新点位");
}

watch(selectedView, async () => {
  selectedFeature.value = null;
  geojsonRequestToken += 1;
  geojson.value = createEmptyFeatureCollection();
  loading.value = Boolean(selectedView.value);
  activeFilters.value = {};
  openFilterMenus.value = {};
  await loadFilterOptions();
  await loadGeoJson({ autoFit: true });
});

watch(isFilterPanelOpen, (open) => {
  if (!open) {
    openFilterMenus.value = buildFilterMenuState();
  }
});

onMounted(async () => {
  await Promise.all([loadViews(), loadAdminBoundary()]);
});
</script>

<template>
  <section class="page-shell map-page">
    <div class="map-workspace">
      <aside
        class="filter-drawer"
        :class="{ 'is-open': isFilterPanelOpen }"
        aria-label="地图筛选"
      >
        <article
          class="panel-card sidebar-panel sidebar-panel-slim"
          :class="{ 'is-collapsed': !isFilterPanelOpen }"
        >
          <button
            type="button"
            class="filter-panel-toggle"
            data-testid="map-filter-toggle"
            :aria-expanded="isFilterPanelOpen"
            aria-controls="map-filter-panel-body"
            :aria-label="isFilterPanelOpen ? '收起筛选配置' : '展开筛选配置'"
            @click="isFilterPanelOpen = !isFilterPanelOpen"
          >
            <span class="icon-badge" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path
                  d="M4 5.75A1.75 1.75 0 0 1 5.75 4h12.5A1.75 1.75 0 0 1 20 5.75v.31a1.75 1.75 0 0 1-.36 1.06l-4.64 6.04v4.09a1.75 1.75 0 0 1-1.02 1.59l-2 1A1.75 1.75 0 0 1 9 18.25v-5.09L4.36 7.12A1.75 1.75 0 0 1 4 6.06v-.31Zm1.75-.25a.25.25 0 0 0-.25.25v.31c0 .05.02.11.05.15l4.8 6.24a.75.75 0 0 1 .15.46v5.34a.25.25 0 0 0 .36.22l2-1a.25.25 0 0 0 .14-.22v-4.34a.75.75 0 0 1 .15-.46l4.8-6.24a.25.25 0 0 0 .05-.15v-.31a.25.25 0 0 0-.25-.25H5.75Z"
                />
              </svg>
            </span>
            <span class="filter-toggle-title">筛选配置</span>
            <span class="filter-toggle-chevron" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path d="M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41Z" />
              </svg>
            </span>
          </button>

          <div v-if="isFilterPanelOpen" id="map-filter-panel-body" class="filter-panel-body">
            <div class="sidebar-field-stack">
              <div
                v-for="field in filterFields"
                :key="field.key"
                class="field-block filter-field-card"
                :class="{ 'is-open': isFilterMenuOpen(field.key) }"
              >
                <div class="filter-select">
                  <button
                    type="button"
                    class="filter-select-trigger"
                    :class="{ 'is-open': isFilterMenuOpen(field.key) }"
                    :data-testid="`map-filter-trigger-${field.key}`"
                    :aria-expanded="isFilterMenuOpen(field.key)"
                    :aria-controls="`map-filter-menu-${field.key}`"
                    :disabled="loading || field.options.length === 0"
                    @click="toggleFilterMenu(field.key)"
                  >
                    <span class="filter-select-copy">
                      <span class="filter-select-label">{{ field.label }}</span>
                      <span
                        class="filter-select-summary"
                        :class="{ 'is-muted': isFilterSummaryMuted(field) }"
                      >
                        {{ getFilterSummary(field) }}
                      </span>
                    </span>
                    <span class="filter-select-meta">
                      <span v-if="hasSelectedFilterValues(field.key)" class="filter-select-count" aria-hidden="true">
                        {{ activeFilters[field.key].length }}
                      </span>
                      <span class="filter-select-chevron" aria-hidden="true">
                        <svg viewBox="0 0 24 24">
                          <path
                            d="M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41Z"
                          />
                        </svg>
                      </span>
                    </span>
                  </button>

                  <div
                    v-if="isFilterMenuOpen(field.key)"
                    :id="`map-filter-menu-${field.key}`"
                    class="filter-option-dropdown"
                    :data-testid="`map-filter-${field.key}`"
                    role="group"
                    :aria-label="field.label"
                    :aria-disabled="loading || field.options.length === 0"
                  >
                    <label
                      v-for="option in field.options"
                      :key="option.value"
                      class="filter-option"
                      :class="{ 'is-disabled': loading }"
                    >
                      <input
                        v-model="activeFilters[field.key]"
                        type="checkbox"
                        :value="option.value"
                        :data-testid="`map-filter-${field.key}-${option.value}`"
                        :disabled="loading"
                      />
                      <span>{{ option.label }}</span>
                    </label>
                  </div>
                </div>
              </div>

              <div v-if="!hasFilterFields" class="filter-empty-state">
                当前视图暂无筛选字段
              </div>
            </div>

            <div class="filter-actions">
              <button type="button" :disabled="loading || !selectedView" @click="applyFilter">
                应用筛选
              </button>
              <button type="button" class="button-secondary" @click="refreshViewsAndData">
                刷新
              </button>
              <button
                type="button"
                class="button-secondary"
                :disabled="loading"
                @click="resetFilter"
              >
                清空
              </button>
            </div>

            <p class="muted-note">{{ filterHint }}</p>
          </div>
        </article>
      </aside>

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

      <section class="map-panel" aria-label="调查点位地图">
        <LeafletMap
          :auto-fit-on-data-change="autoFitOnDataChange"
          :basemap-mode="basemapMode"
          :boundary-geojson="boundaryGeojson"
          :geojson="geojson"
          :loading="loading"
          :loading-views="loadingViews"
          :popup-fields="currentView.columns"
          :show-point-labels="showPointLabels"
          :view-name="selectedView"
          :views="views"
          @feature-click="onFeatureClick"
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
}

.map-workspace {
  position: relative;
  flex: 1;
  min-height: calc(100vh - 6.85rem);
  overflow: hidden;
  background: rgba(229, 244, 230, 0.54);
}

.filter-drawer {
  position: absolute;
  top: 5.35rem;
  left: 1rem;
  z-index: 1200;
  width: 3.4rem;
  max-width: calc(100% - 2rem);
  max-height: calc(100% - 6.35rem);
  pointer-events: none;
  transition:
    top 180ms ease,
    width 180ms ease;
}

.filter-drawer.is-open {
  top: 1rem;
  bottom: 1rem;
  width: min(20rem, calc(100% - 2rem));
  max-height: none;
}

.sidebar-panel {
  width: 100%;
  height: 100%;
  max-height: inherit;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0.65rem;
  pointer-events: auto;
}

.sidebar-panel-slim {
  border-radius: 18px;
}

.sidebar-panel.is-collapsed {
  display: flex;
  justify-content: center;
  padding: 0.35rem;
}

.filter-panel-toggle {
  width: 100%;
  min-height: 2.8rem;
  justify-content: flex-start;
  padding: 0.35rem;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-ink);
  box-shadow: none;
  text-align: left;
}

.filter-panel-toggle:hover {
  background: var(--color-surface-container-low);
  box-shadow: none;
  transform: none;
}

.filter-panel-toggle:focus-visible {
  box-shadow: var(--focus-ring);
}

.sidebar-panel.is-collapsed .filter-panel-toggle {
  width: 2.6rem;
  height: 2.6rem;
  min-height: 2.6rem;
  justify-content: center;
  padding: 0;
}

.sidebar-panel.is-collapsed .icon-badge {
  width: 2.6rem;
  height: 2.6rem;
}

.sidebar-panel.is-collapsed .filter-toggle-title,
.sidebar-panel.is-collapsed .filter-toggle-chevron {
  display: none;
}

.filter-toggle-title {
  min-width: 0;
  flex: 1;
  font-size: 1.12rem;
  line-height: 1.15;
  font-family: var(--font-display);
  font-weight: 800;
  white-space: nowrap;
}

.filter-toggle-chevron {
  width: 1.8rem;
  height: 1.8rem;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-xs);
  color: var(--color-muted);
  transition:
    color 180ms ease,
    transform 180ms ease;
}

.filter-toggle-chevron svg {
  width: 1.2rem;
  height: 1.2rem;
  fill: currentColor;
}

.filter-panel-toggle[aria-expanded="true"] .filter-toggle-chevron {
  color: var(--color-primary);
  transform: rotate(180deg);
}

.filter-panel-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  min-height: 0;
  margin-top: 0.9rem;
}

.sidebar-field-stack {
  display: grid;
  gap: 0;
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding-right: 0.18rem;
  border: 1px solid rgba(46, 125, 50, 0.14);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.78);
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}

.filter-empty-state {
  padding: 0.85rem;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  font-size: 0.86rem;
  font-weight: 700;
}

.filter-field-card {
  gap: 0;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  transition:
    border-color 180ms ease,
    background-color 180ms ease,
    box-shadow 180ms ease;
}

.filter-field-card + .filter-field-card {
  border-top: 1px solid rgba(46, 125, 50, 0.12);
}

.filter-field-card.is-open {
  background: rgba(244, 250, 245, 0.92);
  box-shadow: none;
}

.filter-select {
  display: grid;
  gap: 0;
}

.filter-select-trigger {
  width: 100%;
  min-height: 0;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.68rem 0.8rem;
  border: none;
  border-radius: 0;
  background: transparent;
  color: var(--color-ink);
  box-shadow: none;
  text-align: left;
}

.filter-select-trigger:hover {
  background: rgba(90, 165, 110, 0.1);
  transform: none;
}

.filter-select-trigger:focus-visible {
  box-shadow: var(--focus-ring);
}

.filter-select-trigger:disabled {
  opacity: 0.68;
  cursor: not-allowed;
}

.filter-select-trigger.is-open {
  background: rgba(90, 165, 110, 0.12);
}

.filter-select-copy {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.14rem;
}

.filter-select-label {
  color: var(--color-muted);
  font-size: 0.73rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  line-height: 1.3;
  text-transform: uppercase;
}

.filter-select-summary {
  min-width: 0;
  font-size: 0.92rem;
  font-weight: 700;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.filter-select-summary.is-muted {
  color: var(--color-muted);
  font-weight: 600;
}

.filter-select-meta {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  flex-shrink: 0;
}

.filter-select-count {
  min-width: 1.5rem;
  height: 1.5rem;
  padding: 0 0.45rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(46, 125, 50, 0.12);
  color: var(--color-primary-strong);
  font-size: 0.75rem;
  font-weight: 800;
}

.filter-select-chevron {
  width: 1.5rem;
  height: 1.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-muted);
  transition:
    color 180ms ease,
    transform 180ms ease;
}

.filter-select-chevron svg {
  width: 1.1rem;
  height: 1.1rem;
  fill: currentColor;
}

.filter-select-trigger.is-open .filter-select-chevron {
  color: var(--color-primary);
  transform: rotate(180deg);
}

.filter-option-dropdown {
  display: grid;
  gap: 0.45rem;
  max-height: 11rem;
  overflow: auto;
  margin: 0 0.8rem 0.65rem;
  padding: 0.55rem 0 0;
  border-top: 1px solid rgba(46, 125, 50, 0.12);
  border-right: none;
  border-bottom: none;
  border-left: none;
  border-radius: 0;
  background: transparent;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}

.filter-option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 0.55rem;
  min-height: 2.35rem;
  padding: 0.45rem 0.55rem;
  border-radius: var(--radius-sm);
  color: var(--color-ink);
  font-size: var(--text-sm);
  font-weight: 700;
  cursor: pointer;
}

.filter-option:hover {
  background: rgba(90, 165, 110, 0.1);
}

.filter-option.is-disabled {
  cursor: not-allowed;
  opacity: 0.66;
}

.filter-option input {
  width: 1rem;
  height: 1rem;
  min-height: 1rem;
  padding: 0;
  margin: 0;
  box-shadow: none;
  accent-color: var(--color-primary);
}

.filter-option span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.filter-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}

.filter-actions > button:first-child {
  grid-column: 1 / -1;
}

.map-panel {
  position: absolute;
  inset: 0;
  display: flex;
  min-width: 0;
  min-height: 0;
}

.map-panel :deep(.map-shell) {
  flex: 1;
  min-height: 0;
  height: 100%;
}

.detail-drawer {
  position: absolute;
  top: 1rem;
  right: 1rem;
  bottom: 1rem;
  z-index: 1200;
  width: min(20rem, calc(100% - 2rem));
  pointer-events: none;
}

.detail-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0;
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
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1rem 1.25rem 0.85rem;
}

.detail-title {
  min-width: 0;
  flex: 1;
  font-size: 1.05rem;
  line-height: 1.25;
  font-family: var(--font-display);
  font-weight: 800;
  color: var(--color-primary-strong);
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
  border-radius: 999px;
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.detail-close-btn:hover {
  background: var(--color-surface-container-high);
  color: var(--color-ink);
}

.detail-divider {
  height: 1px;
  background: linear-gradient(to right, var(--color-line-strong), transparent);
  margin: 0 1.25rem;
}

.detail-body {
  flex: 1;
  min-height: 0;
  display: grid;
  gap: 0;
  padding: 0.65rem 1.25rem 1.1rem;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}

.detail-row {
  display: flex;
  flex-direction: column;
  gap: 0.08rem;
  padding: 0.6rem 0;
}

.detail-row + .detail-row {
  border-top: 1px solid var(--color-line);
}

.detail-label {
  color: var(--color-muted);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.detail-value {
  color: var(--color-ink);
  font-size: 0.9rem;
  font-weight: 600;
  overflow-wrap: anywhere;
}

@media (max-width: 760px) {
  .map-workspace {
    min-height: calc(100vh - var(--app-mobile-header-height) - 0.65rem);
  }

  .filter-drawer {
    top: 4.85rem;
    left: 0.75rem;
    width: 3.1rem;
    max-width: calc(100% - 1.5rem);
    max-height: calc(100% - 5.6rem);
  }

  .filter-drawer.is-open {
    top: 0.75rem;
    bottom: 0.75rem;
    width: min(19rem, calc(100% - 1.5rem));
    max-height: none;
  }

  .filter-actions {
    grid-template-columns: 1fr;
  }

  .filter-actions > button:first-child {
    grid-column: auto;
  }

  .filter-actions > button {
    flex: 1;
  }

  .detail-drawer {
    top: 0.75rem;
    right: 0.75rem;
    bottom: 0.75rem;
    width: min(19rem, calc(100% - 1.5rem));
  }
}
</style>
