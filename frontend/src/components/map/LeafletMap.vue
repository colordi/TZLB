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
  if (count <= 0) return "#c2c7bf";
  if (count <= 10) return "#9eb76a";
  if (count <= 50) return "#e19d46";
  return "#ba4b33";
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
  min-height: 620px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: rgba(233, 238, 228, 0.62);
  box-shadow: var(--shadow-elevated);
}

.leaflet-map {
  width: 100%;
  min-height: 620px;
  background: linear-gradient(135deg, rgba(224, 231, 219, 0.92), rgba(209, 220, 206, 0.88));
}

.map-badges {
  position: absolute;
  top: 0.9rem;
  left: 0.9rem;
  right: 0.9rem;
  z-index: 500;
  display: flex;
  justify-content: space-between;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.map-badge {
  padding: 0.5rem 0.8rem;
  border: 1px solid rgba(255, 255, 255, 0.42);
  border-radius: 999px;
  background: rgba(251, 248, 241, 0.84);
  color: rgba(35, 48, 39, 0.94);
  font-size: 0.78rem;
  letter-spacing: 0.06em;
  backdrop-filter: blur(12px);
}

.map-badge.subtle {
  color: var(--muted);
}

.leaflet-overlay {
  position: absolute;
  inset: auto 0.9rem 0.9rem 0.9rem;
  padding: 0.9rem 1rem;
  border-radius: 1rem;
  background: rgba(35, 48, 39, 0.74);
  color: #f8f4ec;
  backdrop-filter: blur(12px);
}

.leaflet-overlay.empty {
  background: rgba(96, 106, 90, 0.76);
}

:deep(.leaflet-control-zoom) {
  border: 0;
  box-shadow: var(--shadow-soft);
}

:deep(.leaflet-control-zoom a) {
  border-bottom-color: var(--line-soft);
  background: rgba(251, 248, 241, 0.96);
  color: var(--ink);
}

:deep(.leaflet-control-attribution) {
  padding: 0.15rem 0.4rem;
  background: rgba(251, 248, 241, 0.82);
}

:deep(.survey-popup .leaflet-popup-content-wrapper) {
  border-radius: 1rem;
  background: rgba(255, 252, 246, 0.96);
  box-shadow: var(--shadow-soft);
}

:deep(.survey-popup .leaflet-popup-tip) {
  background: rgba(255, 252, 246, 0.96);
}

:deep(.map-popup) {
  min-width: 210px;
  display: grid;
  gap: 0.45rem;
  color: var(--ink);
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
}

:deep(.map-popup-row) {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  font-size: 0.86rem;
}

:deep(.map-popup-row strong) {
  color: var(--ink-soft);
}

@media (max-width: 760px) {
  .leaflet-shell,
  .leaflet-map {
    min-height: 500px;
  }

  .map-badges {
    justify-content: flex-start;
  }
}
</style>
