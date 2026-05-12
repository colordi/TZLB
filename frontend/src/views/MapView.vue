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
const loading = ref(false);
const loadingViews = ref(false);
const autoFitOnDataChange = ref(true);
let geojsonRequestToken = 0;

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
    return;
  }

  try {
    const payload = await fetchMapFilterOptions(selectedView.value);
    filterOptions.value = {
      filterFields: normalizeFilterFields(payload),
    };
    activeFilters.value = buildDefaultFilterValues(filterOptions.value.filterFields);
  } catch (loadError) {
    filterOptions.value = {
      filterFields: buildLegacyFilterFields({}),
    };
    activeFilters.value = buildDefaultFilterValues(filterOptions.value.filterFields);
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
  geojsonRequestToken += 1;
  geojson.value = createEmptyFeatureCollection();
  loading.value = Boolean(selectedView.value);
  activeFilters.value = {};
  await loadFilterOptions();
  await loadGeoJson({ autoFit: true });
});

onMounted(async () => {
  await Promise.all([loadViews(), loadAdminBoundary()]);
});
</script>

<template>
  <section class="page-shell map-page">
    <div class="page-content-grid">
      <aside class="page-sidebar">
        <article class="panel-card sidebar-panel sidebar-panel-slim">
          <div class="panel-head panel-head-slim">
            <span class="icon-badge" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path
                  d="M4 5.75A1.75 1.75 0 0 1 5.75 4h12.5A1.75 1.75 0 0 1 20 5.75v.31a1.75 1.75 0 0 1-.36 1.06l-4.64 6.04v4.09a1.75 1.75 0 0 1-1.02 1.59l-2 1A1.75 1.75 0 0 1 9 18.25v-5.09L4.36 7.12A1.75 1.75 0 0 1 4 6.06v-.31Zm1.75-.25a.25.25 0 0 0-.25.25v.31c0 .05.02.11.05.15l4.8 6.24a.75.75 0 0 1 .15.46v5.34a.25.25 0 0 0 .36.22l2-1a.25.25 0 0 0 .14-.22v-4.34a.75.75 0 0 1 .15-.46l4.8-6.24a.25.25 0 0 0 .05-.15v-.31a.25.25 0 0 0-.25-.25H5.75Z"
                />
              </svg>
            </span>
            <div class="panel-head-copy">
              <h2>筛选配置</h2>
            </div>
          </div>

          <div class="sidebar-field-stack">
            <div v-for="field in filterFields" :key="field.key" class="field-block">
              <span class="field-label">{{ field.label }}</span>
              <div
                class="filter-option-list"
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
                <div v-if="field.options.length === 0" class="filter-empty-state">
                  暂无可选项
                </div>
              </div>
              <div
                v-if="activeFilters[field.key]?.length"
                class="filter-selected-count"
                :data-testid="`map-filter-${field.key}-selected-count`"
              >
                已选 {{ activeFilters[field.key].length }} 项
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
            <button type="button" class="button-secondary" @click="refreshViewsAndData">刷新</button>
            <button type="button" class="button-secondary" :disabled="loading" @click="resetFilter">
              清空
            </button>
          </div>

          <p class="muted-note">{{ filterHint }}</p>
        </article>
      </aside>

      <div class="page-main-column">
        <section class="panel-card map-panel">
          <div class="map-panel-head">
            <div class="panel-head map-panel-title">
              <span class="icon-badge" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path
                    d="M12 2.75A7.25 7.25 0 0 0 4.75 10c0 5.02 5.8 10.39 6.05 10.61a1.8 1.8 0 0 0 2.4 0c.25-.22 6.05-5.59 6.05-10.61A7.25 7.25 0 0 0 12 2.75Zm0 16.52C10.5 17.76 6.25 13.4 6.25 10a5.75 5.75 0 1 1 11.5 0c0 3.4-4.25 7.76-5.75 9.27Zm0-12.52A3.25 3.25 0 1 0 15.25 10 3.25 3.25 0 0 0 12 6.75Zm0 5A1.75 1.75 0 1 1 13.75 10 1.75 1.75 0 0 1 12 11.75Z"
                  />
                </svg>
              </span>
              <div class="panel-head-copy">
                <h2>调查点位分布</h2>
                <p>支持点位弹窗详情、名称悬停与底图切换。</p>
              </div>
            </div>
          </div>

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
            @update:basemap-mode="basemapMode = $event"
            @update:show-point-labels="showPointLabels = $event"
            @update:view-name="selectedView = $event"
          />
        </section>
      </div>
    </div>
  </section>
</template>

<style scoped>
.map-page {
  gap: 0;
}

.sidebar-panel {
  padding: 1rem;
}

.sidebar-panel-slim {
  border-radius: 22px;
}

.panel-head-slim {
  margin-bottom: 0.9rem;
}

.sidebar-panel .panel-head-copy h2 {
  font-size: 1.12rem;
  line-height: 1.15;
  letter-spacing: -0.02em;
}

.sidebar-field-stack {
  display: grid;
  gap: 0.85rem;
  margin-bottom: 0.9rem;
}

.filter-empty-state {
  padding: 0.85rem;
  border: 1px dashed var(--color-line);
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  font-size: 0.86rem;
  font-weight: 700;
}

.filter-option-list {
  display: grid;
  gap: 0.45rem;
  max-height: 11.25rem;
  overflow: auto;
  padding: 0.55rem;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  background: var(--color-surface-container-low);
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

.filter-selected-count {
  color: var(--color-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.filter-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
  margin-bottom: 0.7rem;
}

.filter-actions > button:first-child {
  grid-column: 1 / -1;
}

.map-panel {
  padding: 1.15rem;
}

.map-panel-head {
  margin-bottom: 0.9rem;
}

.map-panel-title {
  margin-bottom: 0;
}

@media (max-width: 760px) {
  .filter-actions {
    grid-template-columns: 1fr;
  }

  .filter-actions > button:first-child {
    grid-column: auto;
  }

  .filter-actions > button,
  .sidebar-panel {
    flex: 1;
  }
}
</style>
