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

async function loadGeoJson() {
  if (!selectedView.value) {
    return;
  }

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
  await loadViews();
  await loadGeoJson();
}

function applyFilter() {
  loadGeoJson();
}

function resetFilter() {
  townshipFilter.value = "";
  surveyStatusFilter.value = "";
  loadGeoJson();
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
  await loadGeoJson();
});

onMounted(async () => {
  await Promise.all([loadViews(), loadAdminBoundary()]);
});
</script>

<template>
  <section class="map-view">
    <section class="map-controls">
      <section class="sidebar-card view-control-card">
        <p class="sidebar-eyebrow">视图控制</p>

        <div class="view-metrics">
          <div class="view-metric">
            <span>可用视图</span>
            <strong>{{ views.length }}</strong>
          </div>
          <div class="view-metric">
            <span>当前点位</span>
            <strong>{{ featureCount }}</strong>
          </div>
          <div class="view-metric">
            <span>高风险点</span>
            <strong>{{ levelSummary.level3 }}</strong>
          </div>
        </div>

        <label class="sidebar-field">
          <span>监测视图</span>
          <select v-model="selectedView" :disabled="loadingViews || !views.length">
            <option v-for="view in views" :key="view.name" :value="view.name">
              {{ view.name }}
            </option>
          </select>
        </label>

        <div class="sidebar-buttons">
          <button type="button" class="ghost" @click="refreshViewsAndData">
            刷新视图
          </button>
        </div>
      </section>

      <section class="sidebar-card">
        <p class="sidebar-eyebrow">查询过滤</p>
        <div class="filter-grid">
          <label class="sidebar-field">
            <span>乡镇</span>
            <select v-model="townshipFilter" :disabled="!supportsTownshipFilter">
              <option value="">全部乡镇</option>
              <option v-for="township in townshipOptions" :key="township" :value="township">
                {{ township }}
              </option>
            </select>
          </label>

          <label class="sidebar-field">
            <span>调查状态</span>
            <select v-model="surveyStatusFilter" :disabled="!supportsSurveyStatusFilter">
              <option value="">全部状态</option>
              <option value="调查">调查</option>
              <option value="未调查">未调查</option>
            </select>
          </label>
        </div>

        <div class="sidebar-buttons">
          <button type="button" @click="applyFilter" :disabled="loading || !selectedView">
            应用筛选
          </button>
          <button type="button" class="ghost" @click="resetFilter" :disabled="loading">
            清空
          </button>
        </div>

        <p class="sidebar-hint">
          {{
            supportsTownshipFilter || supportsSurveyStatusFilter
              ? "支持多字段组合筛选，可同时按乡镇和调查状态过滤。"
              : "当前视图不包含可用的筛选字段，已自动禁用筛选器。"
          }}
        </p>
      </section>

      <MapLegend class="map-control-card" />
    </section>

    <div class="map-stage">
      <LeafletMap
        :boundary-geojson="boundaryGeojson"
        :geojson="geojson"
        :loading="loading"
        :view-name="selectedView"
      />
    </div>
  </section>
</template>

<style scoped>
.map-view {
  display: grid;
  gap: 1rem;
}

.sidebar-eyebrow {
  margin: 0;
  font-size: 0.78rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--accent);
}

.sidebar-card {
  display: grid;
  gap: 0.9rem;
  height: 100%;
  padding: 1rem;
  border-radius: 1.3rem;
  background:
    linear-gradient(180deg, rgba(251, 248, 240, 0.92), rgba(243, 238, 226, 0.84));
  border: 1px solid rgba(53, 67, 48, 0.1);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.48),
    0 12px 30px rgba(25, 32, 22, 0.06);
}

.view-control-card {
  gap: 1rem;
}

.view-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.55rem;
}

.map-controls {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr) minmax(240px, 0.9fr);
  gap: 1rem;
}

.view-metric {
  display: grid;
  gap: 0.18rem;
  padding: 0.8rem 0.85rem;
  border-radius: 1rem;
  background: rgba(255, 252, 246, 0.9);
  border: 1px solid rgba(53, 67, 48, 0.08);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5);
}

.view-metric span {
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.view-metric strong {
  font-size: 1.45rem;
  line-height: 1.05;
}

.sidebar-field {
  display: grid;
  gap: 0.45rem;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.sidebar-field span {
  font-size: 0.92rem;
}

.sidebar-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: auto;
}

.sidebar-hint,
.map-control-card {
  margin: 0;
}

.sidebar-hint {
  color: var(--muted);
  line-height: 1.6;
}

.map-stage {
  min-width: 0;
}

@media (max-width: 1080px) {
  .map-controls {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .view-metrics {
    grid-template-columns: 1fr;
  }

  .filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
