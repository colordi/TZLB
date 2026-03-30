<script setup>
import L from "leaflet";
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue";
import "leaflet/dist/leaflet.css";
import { buildPopupRows } from "./popupFields.js";

const props = defineProps({
  autoFitOnDataChange: {
    type: Boolean,
    default: true,
  },
  basemapMode: {
    type: String,
    default: "standard",
  },
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
  popupFields: {
    type: Array,
    default: () => [],
  },
  viewName: {
    type: String,
    default: "",
  },
});

const mapElement = ref(null);
const mapRef = shallowRef(null);
const basemapLayerRef = shallowRef(null);
const boundaryLayerRef = shallowRef(null);
const pointLayerRef = shallowRef(null);

const featureCount = computed(() => props.geojson?.features?.length || 0);
const activeBasemapLabel = computed(() =>
  props.basemapMode === "satellite" ? "卫星地图" : "标准地图",
);

const BASEMAP_CONFIG = {
  standard: {
    url: "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
    options: {
      maxZoom: 19,
      attribution:
        "&copy; OpenStreetMap contributors, Tiles style by Humanitarian OpenStreetMap Team hosted by OpenStreetMap France",
    },
  },
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    options: {
      maxZoom: 19,
      attribution: "Source: Esri, Vantor, Earthstar Geographics, and the GIS User Community",
    },
  },
};

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
  if (count <= 0) return "#94a3b8";
  if (count <= 10) return "#22c55e";
  if (count <= 50) return "#f59e0b";
  return "#ef4444";
}

function renderPopup(properties = {}) {
  const rows = buildPopupRows(props.popupFields, properties);

  return `
    <div class="map-popup">
      ${rows
        .map(
          ([label, value]) => `
            <div class="map-popup-row">
              <strong>${label}</strong>
              <span>${value ?? "-"}</span>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function resolveBoundaryStyle() {
  return {
    color: "#d78b41",
    fillColor: "#eed6b6",
    fillOpacity: 0.05,
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

function clearBasemapLayer() {
  if (basemapLayerRef.value) {
    basemapLayerRef.value.remove();
    basemapLayerRef.value = null;
  }
}

function drawBasemap(mode = "standard") {
  if (!mapRef.value) {
    return;
  }

  const config = BASEMAP_CONFIG[mode] ?? BASEMAP_CONFIG.standard;
  clearBasemapLayer();
  basemapLayerRef.value = L.tileLayer(config.url, config.options).addTo(mapRef.value);
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
    interactive: false,
    style: () => ({
      ...resolveBoundaryStyle(),
      weight: 4,
      opacity: 0.9,
    }),
  }).addTo(mapRef.value);

  fitMapToAvailableLayer();
}

function drawGeoJson(data, shouldFit = true) {
  if (!mapRef.value) {
    return;
  }

  clearPointLayer();
  if (!data?.features?.length) {
    if (shouldFit) {
      fitMapToAvailableLayer();
    }
    return;
  }

  pointLayerRef.value = L.geoJSON(data, {
    pointToLayer: (feature, latlng) => {
      const count = normalizeInsectCount(feature.properties);
      return L.circleMarker(latlng, {
        radius: count > 50 ? 11 : count > 10 ? 9 : count > 0 ? 7 : 6,
        fillColor: resolveColor(count),
        color: "rgba(21, 28, 22, 0.72)",
        weight: 1,
        fillOpacity: 0.88,
      });
    },
    onEachFeature: (feature, layer) => {
      layer.bindPopup(renderPopup(feature.properties), {
        className: "survey-popup",
      });
    },
  }).addTo(mapRef.value);

  pointLayerRef.value.bringToFront();
  if (shouldFit) {
    fitMapToAvailableLayer();
  }
}

onMounted(() => {
  mapRef.value = L.map(mapElement.value, {
    zoomControl: true,
    attributionControl: true,
  }).setView([39.91, 116.72], 11);

  drawBasemap(props.basemapMode);
  drawBoundaryGeoJson(props.boundaryGeojson);
  drawGeoJson(props.geojson, props.autoFitOnDataChange);
});

watch(
  () => props.basemapMode,
  (value) => {
    drawBasemap(value);
  },
);

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
    drawGeoJson(value, props.autoFitOnDataChange);
  },
  { deep: true },
);

onBeforeUnmount(() => {
  clearBasemapLayer();
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
    <div class="map-badges">
      <div class="map-badge">当前底图：{{ activeBasemapLabel }}</div>
      <div class="map-badge subtle">点位 {{ featureCount }}</div>
    </div>

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
  min-height: 600px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--bg-deep);
  box-shadow: var(--shadow-elevated);
}

.leaflet-map {
  width: 100%;
  min-height: 600px;
  background: var(--bg-deep);
}

.map-badges {
  position: absolute;
  top: 0.75rem;
  left: 0.75rem;
  right: 0.75rem;
  z-index: 500;
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.map-badge {
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-base);
  color: var(--ink);
  font-size: 0.75rem;
  font-weight: 500;
  box-shadow: var(--shadow-soft);
}

.map-badge.subtle {
  color: var(--muted);
}

.leaflet-overlay {
  position: absolute;
  inset: auto 0.75rem 0.75rem 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  background: rgba(15, 23, 42, 0.8);
  color: #ffffff;
  font-size: 0.875rem;
}

.leaflet-overlay.empty {
  background: rgba(100, 116, 139, 0.8);
}

:deep(.leaflet-control-zoom) {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-soft);
}

:deep(.leaflet-control-zoom a) {
  border-bottom-color: var(--border);
  background: var(--surface-base);
  color: var(--ink);
  width: 32px;
  height: 32px;
  line-height: 32px;
  font-size: 18px;
}

:deep(.leaflet-control-zoom a:hover) {
  background: var(--hover-tint);
}

:deep(.leaflet-control-attribution) {
  padding: 0.25rem 0.5rem;
  background: var(--surface-base);
  font-size: 0.75rem;
}

:deep(.survey-popup .leaflet-popup-content-wrapper) {
  border-radius: var(--radius-md);
  background: var(--surface-base);
  box-shadow: var(--shadow-soft);
  padding: 0.5rem;
}

:deep(.survey-popup .leaflet-popup-tip) {
  background: var(--surface-base);
}

:deep(.map-popup) {
  min-width: 200px;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  color: var(--ink);
}

:deep(.map-popup-row) {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  font-size: 0.875rem;
}

:deep(.map-popup-row strong) {
  color: var(--muted);
  font-weight: 500;
}

@media (max-width: 760px) {
  .leaflet-shell,
  .leaflet-map {
    min-height: 480px;
  }

  .map-badges {
    justify-content: flex-start;
  }
}
</style>
