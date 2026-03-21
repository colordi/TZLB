<script setup>
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const props = defineProps({
  boundaryGeojson: {
    type: Object,
    default: () => ({ type: "FeatureCollection", features: [] }),
  },
  geojson: {
    type: Object,
    default: () => ({ type: "FeatureCollection", features: [] }),
  },
  loading: {
    type: Boolean,
    default: false,
  },
  viewName: {
    type: String,
    default: "",
  },
});

const mapElement = ref(null);
const mapRef = shallowRef(null);
const boundaryLayerRef = shallowRef(null);
const pointLayerRef = shallowRef(null);

const featureCount = computed(() => props.geojson?.features?.length || 0);

function normalizeInsectCount(properties = {}) {
  const value =
    properties["总虫口数"] ??
    properties["虫口数"] ??
    properties.total_insect_count ??
    properties.total_insect ??
    0;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}

function resolveColor(count) {
  if (count <= 0) return "#c2c7bf";
  if (count <= 10) return "#9eb76a";
  if (count <= 50) return "#e19d46";
  return "#ba4b33";
}

function renderPopup(properties = {}) {
  const rows = [
    ["编号", properties["编号"] ?? properties.location_id ?? "-"],
    ["乡镇", properties["乡镇"] ?? properties.town_or_street ?? "-"],
    ["村", properties["村"] ?? properties.location_name ?? "-"],
    ["调查日期", properties["调查日期"] ?? properties.survey_date ?? "-"],
    ["总虫口数", properties["总虫口数"] ?? properties.total_insect_count ?? "-"],
  ];

  return `
    <div style="min-width: 200px; font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;">
      ${rows
        .map(
          ([label, value]) =>
            `<div style="display:flex;justify-content:space-between;gap:12px;margin:4px 0;"><strong>${label}</strong><span>${value ?? "-"}</span></div>`,
        )
        .join("")}
    </div>
  `;
}

function renderBoundaryPopup(properties = {}) {
  const rows = [
    ["区域", properties["区域"] ?? "-"],
    ["分类", properties["分类"] ?? "-"],
  ];

  return `
    <div style="min-width: 180px; font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;">
      ${rows
        .map(
          ([label, value]) =>
            `<div style="display:flex;justify-content:space-between;gap:12px;margin:4px 0;"><strong>${label}</strong><span>${value ?? "-"}</span></div>`,
        )
        .join("")}
    </div>
  `;
}

function resolveBoundaryStyle(properties = {}) {
  return {
    color: "#e28b34",
    fillColor: "#f3d5ad",
    fillOpacity: 0.06,
  };
}

function clearBoundaryLayer() {
  if (boundaryLayerRef.value) {
    boundaryLayerRef.value.remove();
    boundaryLayerRef.value = null;
  }
}

function clearPointLayer() {
  if (pointLayerRef.value) {
    pointLayerRef.value.remove();
    pointLayerRef.value = null;
  }
}

function fitMapToAvailableLayer() {
  if (!mapRef.value) {
    return;
  }

  const pointBounds = pointLayerRef.value?.getBounds?.();
  if (pointBounds?.isValid?.()) {
    mapRef.value.fitBounds(pointBounds.pad(0.18));
    return;
  }

  const boundaryBounds = boundaryLayerRef.value?.getBounds?.();
  if (boundaryBounds?.isValid?.()) {
    mapRef.value.fitBounds(boundaryBounds.pad(0.04));
  }
}

function drawBoundaryGeoJson(data) {
  if (!mapRef.value) {
    return;
  }

  clearBoundaryLayer();
  if (!data?.features?.length) {
    return;
  }

  boundaryLayerRef.value = L.geoJSON(data, {
    style: (feature) => ({
      ...resolveBoundaryStyle(feature?.properties),
      weight: 5,
      opacity: 0.96,
    }),
    onEachFeature: (feature, layer) => {
      layer.bindPopup(renderBoundaryPopup(feature.properties));
    },
  }).addTo(mapRef.value);

  fitMapToAvailableLayer();
}

function drawGeoJson(data) {
  if (!mapRef.value) {
    return;
  }

  clearPointLayer();
  if (!data?.features?.length) {
    fitMapToAvailableLayer();
    return;
  }

  pointLayerRef.value = L.geoJSON(data, {
    pointToLayer: (feature, latlng) => {
      const count = normalizeInsectCount(feature.properties);
      return L.circleMarker(latlng, {
        radius: count > 50 ? 11 : count > 10 ? 9 : count > 0 ? 7 : 6,
        fillColor: resolveColor(count),
        color: "rgba(14, 16, 12, 0.72)",
        weight: 1,
        fillOpacity: 0.88,
      });
    },
    onEachFeature: (feature, layer) => {
      layer.bindPopup(renderPopup(feature.properties));
    },
  }).addTo(mapRef.value);

  pointLayerRef.value.bringToFront();
  fitMapToAvailableLayer();
}

onMounted(() => {
  mapRef.value = L.map(mapElement.value, {
    zoomControl: true,
    attributionControl: true,
  }).setView([39.91, 116.72], 11);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(mapRef.value);

  drawBoundaryGeoJson(props.boundaryGeojson);
  drawGeoJson(props.geojson);
});

watch(
  () => props.boundaryGeojson,
  (value) => {
    drawBoundaryGeoJson(value);
  },
  { deep: true },
);

watch(
  () => props.geojson,
  (value) => {
    drawGeoJson(value);
  },
  { deep: true },
);

onBeforeUnmount(() => {
  clearBoundaryLayer();
  clearPointLayer();
  if (mapRef.value) {
    mapRef.value.remove();
    mapRef.value = null;
  }
});
</script>

<template>
  <div class="leaflet-shell">
    <div ref="mapElement" class="leaflet-map"></div>

    <div v-if="loading" class="leaflet-overlay">
      正在加载 {{ viewName || "地图视图" }} …
    </div>

    <div v-else-if="!featureCount" class="leaflet-overlay empty">
      当前查询没有返回点位数据。
    </div>
  </div>
</template>

<style scoped>
.leaflet-shell {
  position: relative;
  min-height: 620px;
  border-radius: 1.8rem;
  overflow: hidden;
  box-shadow: 0 26px 60px rgba(20, 28, 21, 0.18);
}

.leaflet-map {
  width: 100%;
  min-height: 620px;
  background: linear-gradient(135deg, rgba(224, 231, 219, 0.9), rgba(209, 220, 206, 0.88));
}

.leaflet-overlay {
  position: absolute;
  inset: auto 1.1rem 1.1rem 1.1rem;
  padding: 0.95rem 1.1rem;
  border-radius: 1rem;
  background: rgba(14, 16, 12, 0.72);
  color: #f6f2e9;
  backdrop-filter: blur(14px);
}

.leaflet-overlay.empty {
  background: rgba(80, 89, 72, 0.78);
}
</style>
