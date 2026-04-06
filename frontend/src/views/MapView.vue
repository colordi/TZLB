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
const townshipOptions = computed(() => filterOptions.value.townships || []);

const filterHint = computed(() => {
  if (supportsTownshipFilter.value || supportsSurveyStatusFilter.value) {
    return "按当前视图筛选点位。";
  }
  return "当前视图暂无可用筛选。";
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
    const filters = {};
    if (supportsTownshipFilter.value && townshipFilter.value) {
      filters["乡镇"] = townshipFilter.value;
    }
    if (supportsSurveyStatusFilter.value && surveyStatusFilter.value) {
      filters["调查状态"] = surveyStatusFilter.value;
    }
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
  } catch (loadError) {
    filterOptions.value = {
      townships: [],
      supportsTownshipFilter: currentView.value.columns.includes("乡镇"),
      supportsSurveyStatusFilter: currentView.value.columns.includes("调查日期"),
    };
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
  townshipFilter.value = "";
  surveyStatusFilter.value = "";
  loadGeoJson({ autoFit: false });
  info("筛选条件已清空。", "已恢复全部点位");
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
  <section class="page-shell map-page">
    <div class="page-content-grid">
      <aside class="page-sidebar">
        <article class="panel-card sidebar-panel sidebar-panel-slim">
          <div class="panel-head panel-head-slim">
            <span class="icon-badge" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path
                  d="M11.62 2.6a1 1 0 0 1 .76 0l7.25 2.9a1 1 0 0 1 0 1.86l-7.25 2.9a1 1 0 0 1-.76 0l-7.25-2.9a1 1 0 0 1 0-1.86l7.25-2.9Zm-4.5 4.83L12 9.39l4.88-1.96L12 5.48 7.12 7.43Zm-2.84 3.82a1 1 0 0 1 1.3-.56L12 13.22l6.42-2.53a1 1 0 1 1 .74 1.86l-6.79 2.68a1 1 0 0 1-.74 0L4.84 12.55a1 1 0 0 1-.56-1.3Zm0 4.6a1 1 0 0 1 1.3-.56L12 17.82l6.42-2.53a1 1 0 1 1 .74 1.86l-6.79 2.68a1 1 0 0 1-.74 0l-6.79-2.68a1 1 0 0 1-.56-1.3Z"
                />
              </svg>
            </span>
            <div class="panel-head-copy">
              <h2>视图配置</h2>
            </div>
          </div>

          <div class="field-block">
            <label for="map-view-select" class="sr-only">当前视图</label>
            <select
              id="map-view-select"
              data-testid="view-select"
              v-model="selectedView"
              :disabled="loadingViews || !views.length"
            >
              <option v-if="!views.length" value="">暂无可用视图</option>
              <option v-for="view in views" :key="view.name" :value="view.name">
                {{ view.name }}
              </option>
            </select>
          </div>
        </article>

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
            <div class="field-block">
              <label for="township-select">乡镇 / 街道</label>
              <select
                id="township-select"
                data-testid="township-select"
                v-model="townshipFilter"
                :disabled="!supportsTownshipFilter"
              >
                <option value="">全部乡镇</option>
                <option v-for="township in townshipOptions" :key="township" :value="township">
                  {{ township }}
                </option>
              </select>
            </div>

            <div class="field-block">
              <label for="survey-status-select">调查状态</label>
              <select
                id="survey-status-select"
                data-testid="survey-status-select"
                v-model="surveyStatusFilter"
                :disabled="!supportsSurveyStatusFilter"
              >
                <option value="">全部状态</option>
                <option value="调查">调查</option>
                <option value="未调查">未调查</option>
              </select>
            </div>

            <div class="field-block">
              <label>底图模式</label>
              <div class="segmented-control basemap-toggle">
                <button
                  type="button"
                  class="segment-button"
                  :class="{ 'is-active': basemapMode === 'standard' }"
                  @click="basemapMode = 'standard'"
                >
                  标准地图
                </button>
                <button
                  type="button"
                  class="segment-button"
                  :class="{ 'is-active': basemapMode === 'satellite' }"
                  @click="basemapMode = 'satellite'"
                >
                  卫星地图
                </button>
              </div>
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
            :popup-fields="currentView.columns"
            :view-name="selectedView"
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

.basemap-toggle {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  width: 100%;
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

  .basemap-toggle {
    grid-template-columns: 1fr;
  }
}
</style>
