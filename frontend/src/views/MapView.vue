<script setup>
import { computed, onMounted, ref, watch } from "vue";

import {
  fetchAdminBoundary,
  fetchMapFilterOptions,
  fetchMapView,
  listMapViews,
} from "../api/map.js";
import LeafletMap from "../components/map/LeafletMap.vue";
import MapLegend from "../components/map/MapLegend.vue";

const views = ref([]);
const selectedView = ref("");
const basemapMode = ref("standard");
const geojson = ref({
  type: "FeatureCollection",
  features: [],
});
const boundaryGeojson = ref({
  type: "FeatureCollection",
  features: [],
});
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
const basemapSummary = computed(() =>
  basemapMode.value === "satellite"
    ? "当前使用 Esri World Imagery 影像底图。"
    : "当前使用 OpenStreetMap.HOT 底图。",
);

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
      geojson.value = {
        type: "FeatureCollection",
        features: [],
      };
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
    return;
  }

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
    geojson.value = await fetchMapView(selectedView.value, filters);
  } catch (error) {
    geojson.value = {
      type: "FeatureCollection",
      features: [],
    };
  } finally {
    loading.value = false;
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
    boundaryGeojson.value = {
      type: "FeatureCollection",
      features: [],
    };
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
    <div class="map-layout">
      <section class="map-panel map-primary">
        <div class="map-header">
          <div class="map-header-copy">
            <p class="ui-eyebrow">监测控制</p>
            <h2>视图选择与筛选</h2>
          </div>
          <p class="ui-note">
            先选择监测视图，再按乡镇和调查状态过滤，地图会同步更新点位结果。
          </p>
        </div>

        <div class="map-metrics">
          <article class="ui-stat">
            <span class="ui-stat-label">可用视图</span>
            <strong class="ui-stat-value">{{ views.length }}</strong>
          </article>
          <article class="ui-stat">
            <span class="ui-stat-label">当前点位</span>
            <strong class="ui-stat-value">{{ featureCount }}</strong>
          </article>
          <article class="ui-stat">
            <span class="ui-stat-label">高风险点</span>
            <strong class="ui-stat-value">{{ levelSummary.level3 }}</strong>
          </article>
        </div>

        <div class="map-form-grid">
          <label class="map-field map-view-field">
            <span>监测视图</span>
            <select v-model="selectedView" :disabled="loadingViews || !views.length">
              <option v-for="view in views" :key="view.name" :value="view.name">
                {{ view.name }}
              </option>
            </select>
          </label>

          <label class="map-field">
            <span>乡镇</span>
            <select v-model="townshipFilter" :disabled="!supportsTownshipFilter">
              <option value="">全部乡镇</option>
              <option v-for="township in townshipOptions" :key="township" :value="township">
                {{ township }}
              </option>
            </select>
          </label>

          <label class="map-field">
            <span>调查状态</span>
            <select v-model="surveyStatusFilter" :disabled="!supportsSurveyStatusFilter">
              <option value="">全部状态</option>
              <option value="调查">调查</option>
              <option value="未调查">未调查</option>
            </select>
          </label>
        </div>

        <div class="map-actions">
          <button type="button" class="ghost" @click="refreshViewsAndData">
            刷新视图
          </button>
          <button type="button" :disabled="loading || !selectedView" @click="applyFilter">
            应用筛选
          </button>
          <button type="button" class="ghost" :disabled="loading" @click="resetFilter">
            清空
          </button>
        </div>

        <p class="map-hint">
          {{
            supportsTownshipFilter || supportsSurveyStatusFilter
              ? "支持按乡镇和调查状态组合筛选。"
              : "当前视图不包含可用的筛选字段，筛选器已自动禁用。"
          }}
        </p>
      </section>

      <div class="map-stage">
        <LeafletMap
          :auto-fit-on-data-change="autoFitOnDataChange"
          :basemap-mode="basemapMode"
          :boundary-geojson="boundaryGeojson"
          :geojson="geojson"
          :loading="loading"
          :view-name="selectedView"
        />
      </div>

      <aside class="map-secondary">
        <section class="map-panel secondary-panel">
          <div class="secondary-head">
            <p class="ui-eyebrow">底图模式</p>
            <p class="ui-note">{{ basemapSummary }}</p>
          </div>

          <div class="basemap-toggle" role="tablist" aria-label="底图模式切换">
            <button
              type="button"
              class="basemap-button"
              :class="{ active: basemapMode === 'standard' }"
              :aria-pressed="basemapMode === 'standard'"
              @click="basemapMode = 'standard'"
            >
              标准地图
            </button>
            <button
              type="button"
              class="basemap-button"
              :class="{ active: basemapMode === 'satellite' }"
              :aria-pressed="basemapMode === 'satellite'"
              @click="basemapMode = 'satellite'"
            >
              卫星地图
            </button>
          </div>
        </section>

        <MapLegend />
      </aside>
    </div>
  </section>
</template>

<style scoped>
.map-view {
  display: grid;
}

.map-layout {
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(0, 1.25fr) 280px;
  grid-template-areas:
    "primary secondary"
    "map map";
}

.map-panel {
  display: grid;
  gap: 0.9rem;
  padding: 1rem;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-lg);
  background: var(--surface-base);
  box-shadow: var(--shadow-card);
}

.map-primary {
  grid-area: primary;
}

.map-stage {
  grid-area: map;
  min-width: 0;
}

.map-secondary {
  grid-area: secondary;
  display: grid;
  gap: 1rem;
}

.map-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.map-header-copy {
  display: grid;
  gap: 0.35rem;
}

.map-header-copy h2 {
  font-size: clamp(1.35rem, 2vw, 1.8rem);
  line-height: 1.15;
}

.map-header .ui-note {
  max-width: 26rem;
}

.map-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.7rem;
}

.map-form-grid {
  display: grid;
  grid-template-columns: minmax(240px, 1.15fr) repeat(2, minmax(0, 0.8fr));
  gap: 0.75rem;
}

.map-field {
  display: grid;
  gap: 0.42rem;
}

.map-field span {
  font-size: 0.72rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--muted-soft);
}

.map-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.map-actions button {
  min-height: 2.85rem;
  min-width: 7rem;
  padding: 0.72rem 1.15rem;
  font-size: 1rem;
  box-shadow: none;
}

.map-hint {
  color: var(--muted);
  line-height: 1.6;
}

.secondary-panel {
  align-content: start;
}

.secondary-head {
  display: grid;
  gap: 0.35rem;
}

.basemap-toggle {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.45rem;
}

.basemap-button {
  min-height: 2.85rem;
  border: 1px solid var(--line-strong);
  background: rgba(255, 252, 247, 0.86);
  color: var(--ink);
  box-shadow: none;
}

.basemap-button:hover {
  transform: none;
  background: rgba(248, 244, 236, 0.96);
}

.basemap-button.active {
  border-color: transparent;
  background: var(--accent);
  color: #f8f5ee;
  box-shadow: 0 8px 18px rgba(65, 83, 50, 0.16);
}

@media (max-width: 1120px) {
  .map-layout {
    grid-template-columns: 1fr;
    grid-template-areas:
      "primary"
      "map"
      "secondary";
  }

  .map-header {
    flex-direction: column;
  }
}

@media (max-width: 760px) {
  .map-panel {
    padding: 0.95rem;
  }

  .map-metrics,
  .map-form-grid,
  .basemap-toggle {
    grid-template-columns: 1fr;
  }
}
</style>
