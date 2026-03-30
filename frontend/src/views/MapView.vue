<script setup>
import { computed, onMounted, ref, watch } from "vue";

import {
  fetchAdminBoundary,
  fetchMapFilterOptions,
  fetchMapView,
  listMapViews,
} from "../api/map.js";
import LeafletMap from "../components/map/LeafletMap.vue";

function createEmptyFeatureCollection() {
  return {
    type: "FeatureCollection",
    features: [],
  };
}

const views = ref([]);
const selectedView = ref("");
const basemapMode = ref("standard");
const geojson = ref(createEmptyFeatureCollection());
const boundaryGeojson = ref(createEmptyFeatureCollection());
const townshipFilter = ref("");
const surveyStatusFilter = ref("");
const filterOptions = ref({
  townships: [],
  supportsTownshipFilter: false,
  supportsSurveyStatusFilter: false,
});
const loading = ref(false);
const loadingViews = ref(false);
const autoFitOnDataChange = ref(true);
let geojsonRequestToken = 0;

const currentView = computed(
  () => views.value.find((view) => view.name === selectedView.value) || { columns: [] },
);
const supportsTownshipFilter = computed(
  () => filterOptions.value.supportsTownshipFilter || currentView.value.columns.includes("乡镇"),
);
const supportsSurveyStatusFilter = computed(
  () =>
    filterOptions.value.supportsSurveyStatusFilter ||
    currentView.value.columns.includes("调查日期"),
);
const featureCount = computed(() => geojson.value?.features?.length || 0);
const townshipOptions = computed(() => filterOptions.value.townships || []);

const levelSummary = computed(() => {
  const summary = {
    level0: 0,
    level1: 0,
    level2: 0,
    level3: 0,
  };

  (geojson.value?.features || []).forEach((feature) => {
    const raw =
      feature.properties?.["总虫口数"] ??
      feature.properties?.["虫口数"] ??
      feature.properties?.total_insect_count ??
      0;
    const count = Number(raw);
    if (!Number.isFinite(count) || count <= 0) {
      summary.level0 += 1;
    } else if (count <= 10) {
      summary.level1 += 1;
    } else if (count <= 50) {
      summary.level2 += 1;
    } else {
      summary.level3 += 1;
    }
  });

  return summary;
});

async function loadViews() {
  loadingViews.value = true;

  try {
    const payload = await listMapViews();
    views.value = payload;
    if (!payload.length) {
      selectedView.value = "";
      geojsonRequestToken += 1;
      geojson.value = createEmptyFeatureCollection();
      return;
    }

    if (!payload.some((view) => view.name === selectedView.value)) {
      selectedView.value = payload[0].name;
    }
  } finally {
    loadingViews.value = false;
  }
}

async function loadGeoJson({ autoFit = false } = {}) {
  if (!selectedView.value) {
    loading.value = false;
    return;
  }

  const requestToken = ++geojsonRequestToken;
  const viewName = selectedView.value;
  autoFitOnDataChange.value = autoFit;
  loading.value = true;

  try {
    const filters = {};
    if (supportsTownshipFilter.value && townshipFilter.value) {
      filters["乡镇"] = townshipFilter.value;
    }
    if (supportsSurveyStatusFilter.value && surveyStatusFilter.value) {
      filters["调查状态"] = surveyStatusFilter.value;
    }
    const payload = await fetchMapView(viewName, filters);
    if (requestToken !== geojsonRequestToken || viewName !== selectedView.value) {
      return;
    }
    geojson.value = payload;
  } catch (error) {
    if (requestToken !== geojsonRequestToken || viewName !== selectedView.value) {
      return;
    }
    geojson.value = createEmptyFeatureCollection();
  } finally {
    if (requestToken === geojsonRequestToken) {
      loading.value = false;
    }
  }
}

async function loadFilterOptions() {
  if (!selectedView.value) {
    filterOptions.value = {
      townships: [],
      supportsTownshipFilter: false,
      supportsSurveyStatusFilter: false,
    };
    return;
  }

  try {
    const payload = await fetchMapFilterOptions(selectedView.value);
    filterOptions.value = {
      townships: payload.townships || [],
      supportsTownshipFilter: Boolean(payload.supports_township_filter),
      supportsSurveyStatusFilter: Boolean(payload.supports_survey_status_filter),
    };
  } catch (error) {
    filterOptions.value = {
      townships: [],
      supportsTownshipFilter: currentView.value.columns.includes("乡镇"),
      supportsSurveyStatusFilter: currentView.value.columns.includes("调查日期"),
    };
    console.error(error);
  }
}

async function loadAdminBoundary() {
  try {
    boundaryGeojson.value = await fetchAdminBoundary();
  } catch (error) {
    boundaryGeojson.value = createEmptyFeatureCollection();
    console.error(error);
  }
}

async function refreshViewsAndData() {
  const previousView = selectedView.value;
  await loadViews();
  if (selectedView.value === previousView) {
    await loadGeoJson({ autoFit: false });
  }
}

function applyFilter() {
  loadGeoJson({ autoFit: false });
}

function resetFilter() {
  townshipFilter.value = "";
  surveyStatusFilter.value = "";
  loadGeoJson({ autoFit: false });
}

watch(selectedView, async () => {
  geojsonRequestToken += 1;
  geojson.value = createEmptyFeatureCollection();
  loading.value = Boolean(selectedView.value);
  if (!supportsTownshipFilter.value) {
    townshipFilter.value = "";
  }
  if (!supportsSurveyStatusFilter.value) {
    surveyStatusFilter.value = "";
  }
  await loadFilterOptions();
  if (!supportsTownshipFilter.value) {
    townshipFilter.value = "";
  }
  if (!supportsSurveyStatusFilter.value) {
    surveyStatusFilter.value = "";
  }
  await loadGeoJson({ autoFit: true });
});

onMounted(async () => {
  await Promise.all([loadViews(), loadAdminBoundary()]);
});
</script>

<template>
  <section class="map-view">
    <aside class="map-sidebar">
      <!-- 统计指标 -->
      <div class="sidebar-section metrics-section">
        <div class="metric-item">
          <span class="metric-value">{{ views.length }}</span>
          <span class="metric-label">可用视图</span>
        </div>
        <div class="metric-item">
          <span class="metric-value">{{ featureCount }}</span>
          <span class="metric-label">当前点位</span>
        </div>
        <div class="metric-item">
          <span class="metric-value text-danger">{{ levelSummary.level3 }}</span>
          <span class="metric-label">高风险点</span>
        </div>
      </div>

      <!-- 视图选择 -->
      <div class="sidebar-section">
        <label class="field-label">监测视图</label>
        <select v-model="selectedView" :disabled="loadingViews || !views.length" class="field-select">
          <option v-for="view in views" :key="view.name" :value="view.name">
            {{ view.name }}
          </option>
        </select>
      </div>

      <!-- 筛选条件 -->
      <div class="sidebar-section">
        <label class="field-label">乡镇</label>
        <select v-model="townshipFilter" :disabled="!supportsTownshipFilter" class="field-select">
          <option value="">全部乡镇</option>
          <option v-for="township in townshipOptions" :key="township" :value="township">
            {{ township }}
          </option>
        </select>

        <label class="field-label">调查状态</label>
        <select v-model="surveyStatusFilter" :disabled="!supportsSurveyStatusFilter" class="field-select">
          <option value="">全部状态</option>
          <option value="调查">调查</option>
          <option value="未调查">未调查</option>
        </select>
      </div>

      <!-- 操作按钮 -->
      <div class="sidebar-section actions-section">
        <button type="button" class="btn-primary" :disabled="loading || !selectedView" @click="applyFilter">
          应用筛选
        </button>
        <div class="btn-row">
          <button type="button" class="btn-ghost" @click="refreshViewsAndData">
            刷新
          </button>
          <button type="button" class="btn-ghost" :disabled="loading" @click="resetFilter">
            清空
          </button>
        </div>
      </div>

      <!-- 底图切换 -->
      <div class="sidebar-section">
        <label class="field-label">底图模式</label>
        <div class="basemap-toggle">
          <button
            type="button"
            class="basemap-btn"
            :class="{ active: basemapMode === 'standard' }"
            @click="basemapMode = 'standard'"
          >
            标准地图
          </button>
          <button
            type="button"
            class="basemap-btn"
            :class="{ active: basemapMode === 'satellite' }"
            @click="basemapMode = 'satellite'"
          >
            卫星地图
          </button>
        </div>
      </div>

      <!-- 图例 -->
      <div class="sidebar-section legend-section">
        <label class="field-label">虫口数分级</label>
        <div class="legend-list">
          <div class="legend-item">
            <span class="legend-dot level-0"></span>
            <span>0 或缺失</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot level-1"></span>
            <span>1 - 10</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot level-2"></span>
            <span>11 - 50</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot level-3"></span>
            <span>50 以上</span>
          </div>
        </div>
      </div>

      <p v-if="!supportsTownshipFilter && !supportsSurveyStatusFilter" class="sidebar-hint">
        当前视图不包含筛选字段
      </p>
    </aside>

    <div class="map-container">
      <LeafletMap
        :auto-fit-on-data-change="autoFitOnDataChange"
        :basemap-mode="basemapMode"
        :boundary-geojson="boundaryGeojson"
        :geojson="geojson"
        :loading="loading"
        :popup-fields="currentView.columns"
        :view-name="selectedView"
      />
    </div>
  </section>
</template>

<style scoped>
.map-view {
  display: flex;
  flex: 1;
  gap: 1rem;
  min-height: 0;
}

/* 左侧边栏 */
.map-sidebar {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  overflow-y: auto;
  padding-right: 0.5rem;
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.875rem;
  background: var(--surface-base);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-soft);
}

.metrics-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  padding: 0.75rem;
}

.metric-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.25rem;
}

.metric-value {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--ink);
  line-height: 1;
}

.metric-value.text-danger {
  color: var(--danger);
}

.metric-label {
  font-size: 0.6875rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.field-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--muted);
}

.field-select {
  width: 100%;
  min-height: 2.25rem;
  padding: 0.5rem 0.625rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-strong);
  color: var(--ink);
  font-size: 0.8125rem;
}

.field-select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--focus-ring);
}

.field-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--bg);
}

.actions-section {
  gap: 0.5rem;
}

.btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 2.25rem;
  padding: 0 1rem;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--accent);
  color: #fff;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 150ms ease;
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-strong);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.btn-ghost {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 2rem;
  padding: 0 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-strong);
  color: var(--ink-soft);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 150ms ease;
}

.btn-ghost:hover {
  background: var(--hover-tint);
  border-color: var(--border-strong);
}

.basemap-toggle {
  display: flex;
  gap: 0.5rem;
}

.basemap-btn {
  flex: 1;
  height: 2rem;
  padding: 0 0.5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-strong);
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 150ms ease;
}

.basemap-btn:hover {
  border-color: var(--border-strong);
  color: var(--ink);
}

.basemap-btn.active {
  border-color: var(--accent);
  background: var(--accent);
  color: #fff;
}

.legend-section {
  gap: 0.625rem;
}

.legend-list {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: var(--ink-soft);
}

.legend-dot {
  width: 0.625rem;
  height: 0.625rem;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-dot.level-0 { background: #94a3b8; }
.legend-dot.level-1 { background: #22c55e; }
.legend-dot.level-2 { background: #f59e0b; }
.legend-dot.level-3 { background: #ef4444; }

.sidebar-hint {
  font-size: 0.75rem;
  color: var(--muted);
  text-align: center;
  padding: 0.5rem;
}

/* 地图区域 */
.map-container {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

/* 响应式 */
@media (max-width: 1024px) {
  .map-view {
    flex-direction: column;
  }

  .map-sidebar {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
    padding-right: 0;
  }

  .sidebar-section {
    flex: 1;
    min-width: 200px;
  }

  .metrics-section {
    flex: 1;
    min-width: 200px;
  }

  .legend-section {
    flex: 2;
    min-width: 300px;
  }
}

@media (max-width: 640px) {
  .map-sidebar {
    flex-direction: column;
  }

  .sidebar-section,
  .metrics-section,
  .legend-section {
    flex: none;
    min-width: auto;
    width: 100%;
  }
}
</style>
