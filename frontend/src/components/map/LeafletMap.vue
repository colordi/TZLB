<script setup>
import L from "leaflet";
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue";
import "leaflet/dist/leaflet.css";

import { useToast } from "../../composables/useToast.js";
import {
  buildPopupRows,
  normalizeInsectCount,
  resolveFeatureHoverLabel,
  resolveFeatureSeverity,
} from "./popupFields.js";

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

const { error, info } = useToast();
const mapElement = ref(null);
const mapRef = shallowRef(null);
const zoomControlRef = shallowRef(null);
const basemapLayerRef = shallowRef(null);
const boundaryLayerRef = shallowRef(null);
const pointLayerRef = shallowRef(null);
const locateMarkerRef = shallowRef(null);

const featureCount = computed(() => props.geojson?.features?.length || 0);
const activeBasemapLabel = computed(() =>
  props.basemapMode === "satellite" ? "卫星底图" : "标准底图",
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

const LOCATE_MARKER_HTML = `
  <div class="locate-user-marker">
    <span class="locate-user-marker__shadow"></span>
    <span class="locate-user-marker__body">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M20.28 3.72a1 1 0 0 0-1.04-.24L5.58 8.03a1 1 0 0 0-.13 1.84l5.53 2.51 2.51 5.53a1 1 0 0 0 1.84-.13l4.55-13.66a1 1 0 0 0-.24-1.04Z"
        />
      </svg>
    </span>
  </div>
`;

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
    color: "#6AA570",
    fillColor: "#B9DDB3",
    fillOpacity: 0.08,
  };
}

function clearLayer(layerRef) {
  if (layerRef.value) {
    layerRef.value.remove();
    layerRef.value = null;
  }
}

function drawBasemap(mode = "standard") {
  if (!mapRef.value) {
    return;
  }

  const config = BASEMAP_CONFIG[mode] ?? BASEMAP_CONFIG.standard;
  clearLayer(basemapLayerRef);
  basemapLayerRef.value = L.tileLayer(config.url, config.options).addTo(mapRef.value);
}

function fitMapToAvailableLayer() {
  if (!mapRef.value) {
    return;
  }

  const pointBounds = pointLayerRef.value?.getBounds?.();
  if (pointBounds?.isValid?.()) {
    mapRef.value.fitBounds(pointBounds.pad(0.16));
    return;
  }

  const boundaryBounds = boundaryLayerRef.value?.getBounds?.();
  if (boundaryBounds?.isValid?.()) {
    mapRef.value.fitBounds(boundaryBounds.pad(0.03));
  }
}

function drawBoundaryGeoJson(data) {
  if (!mapRef.value) {
    return;
  }

  clearLayer(boundaryLayerRef);
  if (!data?.features?.length) {
    return;
  }

  boundaryLayerRef.value = L.geoJSON(data, {
    interactive: false,
    style: () => ({
      ...resolveBoundaryStyle(),
      weight: 3.5,
      opacity: 0.88,
    }),
  }).addTo(mapRef.value);

  fitMapToAvailableLayer();
}

function drawGeoJson(data, shouldFit = true) {
  if (!mapRef.value) {
    return;
  }

  clearLayer(pointLayerRef);
  if (!data?.features?.length) {
    if (shouldFit) {
      fitMapToAvailableLayer();
    }
    return;
  }

  pointLayerRef.value = L.geoJSON(data, {
    pointToLayer: (feature, latlng) => {
      const count = normalizeInsectCount(feature.properties);
      const severity = resolveFeatureSeverity(count);
      return L.circleMarker(latlng, {
        radius: severity.radius,
        fillColor: severity.color,
        color: "rgba(24, 50, 35, 0.78)",
        weight: 1.25,
        fillOpacity: 0.9,
      });
    },
    onEachFeature: (feature, layer) => {
      const hoverLabel = resolveFeatureHoverLabel(props.popupFields, feature.properties);
      if (hoverLabel) {
        layer.bindTooltip(hoverLabel, {
          direction: "top",
          sticky: true,
          opacity: 0.96,
        });
      }

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

function locateToUser() {
  if (!navigator.geolocation) {
    error("当前浏览器不支持定位能力。", "定位不可用");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      if (!mapRef.value) {
        return;
      }

      const latlng = [position.coords.latitude, position.coords.longitude];
      clearLayer(locateMarkerRef);
      locateMarkerRef.value = L.marker(latlng, {
        icon: L.divIcon({
          className: "locate-user-marker-wrapper",
          html: LOCATE_MARKER_HTML,
          iconSize: [32, 32],
          iconAnchor: [16, 16],
        }),
      }).addTo(mapRef.value);

      mapRef.value.setView(latlng, Math.max(mapRef.value.getZoom(), 13), {
        animate: true,
      });
      info("地图已定位到当前设备位置。", "定位成功");
    },
    (positionError) => {
      const message =
        positionError?.code === 1
          ? "未授予定位权限，请在浏览器中允许访问位置信息。"
          : "暂时无法获取当前位置，请检查定位权限或网络。";
      error(message, "定位失败");
    },
    {
      enableHighAccuracy: true,
      timeout: 8000,
      maximumAge: 60_000,
    },
  );
}

defineExpose({
  locateToUser,
});

onMounted(() => {
  mapRef.value = L.map(mapElement.value, {
    zoomControl: false,
    attributionControl: true,
  }).setView([39.91, 116.72], 11);

  zoomControlRef.value = L.control.zoom({
    position: "bottomright",
  }).addTo(mapRef.value);

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
  clearLayer(basemapLayerRef);
  clearLayer(boundaryLayerRef);
  clearLayer(pointLayerRef);
  clearLayer(locateMarkerRef);

  if (zoomControlRef.value) {
    zoomControlRef.value.remove();
    zoomControlRef.value = null;
  }

  if (mapRef.value) {
    mapRef.value.remove();
    mapRef.value = null;
  }
});
</script>

<template>
  <section class="map-shell">
    <div ref="mapElement" class="map-canvas"></div>

    <div class="map-overlay top-left">
      <div class="map-badge">
        <strong>{{ viewName || "未选择视图" }}</strong>
        <span>{{ activeBasemapLabel }}</span>
      </div>
      <div v-if="loading" class="map-loading">正在刷新点位数据…</div>
    </div>

    <div class="map-overlay bottom-left">
      <div class="map-chip">{{ featureCount }} 个点位</div>
    </div>

    <div class="map-overlay middle-right map-side-action">
      <button
        type="button"
        class="map-fab"
        data-testid="map-locate-button"
        aria-label="定位到当前位置"
        @click="locateToUser"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M19.7 11.25h-1.02a6.77 6.77 0 0 0-5.93-5.93V4.3a.75.75 0 0 0-1.5 0v1.02a6.77 6.77 0 0 0-5.93 5.93H4.3a.75.75 0 0 0 0 1.5h1.02a6.77 6.77 0 0 0 5.93 5.93v1.02a.75.75 0 0 0 1.5 0v-1.02a6.77 6.77 0 0 0 5.93-5.93h1.02a.75.75 0 0 0 0-1.5ZM12 17.2A5.2 5.2 0 1 1 17.2 12 5.2 5.2 0 0 1 12 17.2Zm0-7.05A1.85 1.85 0 1 0 13.85 12 1.85 1.85 0 0 0 12 10.15Z"
          />
        </svg>
      </button>
    </div>
  </section>
</template>

<style scoped>
.map-shell {
  position: relative;
  min-height: 34rem;
  border: 1px solid rgba(46, 125, 50, 0.14);
  border-radius: 26px;
  overflow: hidden;
  background: rgba(229, 244, 230, 0.54);
}

.map-canvas {
  min-height: 34rem;
  width: 100%;
}

.map-overlay {
  position: absolute;
  z-index: 401;
  pointer-events: none;
}

.top-left {
  top: 1rem;
  left: 1rem;
}

.bottom-left {
  left: 1rem;
  bottom: 1rem;
}

.middle-right {
  top: 50%;
  right: 1rem;
  transform: translateY(-50%);
}

.map-badge,
.map-chip,
.map-loading {
  display: inline-flex;
  flex-direction: column;
  gap: 0.18rem;
  padding: 0.78rem 0.95rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--color-ink);
  box-shadow: 0 12px 30px rgba(18, 52, 29, 0.12);
  backdrop-filter: blur(14px);
}

.map-badge span,
.map-loading {
  color: var(--color-muted);
  font-size: 0.82rem;
}

.map-chip {
  flex-direction: row;
  align-items: center;
  color: var(--color-primary-strong);
  font-size: 0.86rem;
  font-weight: 700;
}

.map-loading {
  margin-top: 0.65rem;
}

.map-side-action {
  pointer-events: auto;
}

.map-fab {
  min-height: 0;
  width: 3rem;
  height: 3rem;
  padding: 0;
  border: 1px solid rgba(46, 125, 50, 0.14);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-primary-strong);
  box-shadow: 0 12px 26px rgba(18, 52, 29, 0.12);
}

.map-fab svg {
  width: 1.15rem;
  height: 1.15rem;
  fill: currentColor;
}

:deep(.leaflet-bar) {
  border: 1px solid rgba(46, 125, 50, 0.14);
  border-radius: 0;
  overflow: hidden;
  box-shadow: 0 12px 26px rgba(18, 52, 29, 0.12);
}

:deep(.leaflet-control-zoom) {
  border: none;
  box-shadow: none;
}

:deep(.leaflet-control-zoom a) {
  width: 2.8rem;
  height: 2.8rem;
  line-height: 2.7rem;
  border: none;
  border-bottom: 1px solid rgba(46, 125, 50, 0.14);
  border-radius: 0;
  color: var(--color-primary-strong);
  background: rgba(255, 255, 255, 0.92);
}

:deep(.leaflet-control-zoom a:last-child) {
  border-bottom: none;
}

:deep(.leaflet-bar a:hover) {
  background: rgba(244, 250, 244, 0.96);
}

:deep(.leaflet-control-attribution) {
  background: rgba(255, 255, 255, 0.76);
}

:deep(.locate-user-marker-wrapper) {
  background: transparent;
  border: none;
}

:deep(.locate-user-marker) {
  position: relative;
  width: 32px;
  height: 32px;
}

:deep(.locate-user-marker__shadow) {
  position: absolute;
  inset: 8px 9px 3px 9px;
  border-radius: 999px;
  background: rgba(19, 50, 33, 0.18);
  filter: blur(5px);
}

:deep(.locate-user-marker__body) {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transform: rotate(18deg);
}

:deep(.locate-user-marker__body svg) {
  width: 26px;
  height: 26px;
  fill: #2f80ed;
  filter:
    drop-shadow(0 8px 12px rgba(47, 128, 237, 0.3))
    drop-shadow(0 0 0.5px rgba(255, 255, 255, 0.9));
}

:deep(.leaflet-tooltip) {
  border: none;
  border-radius: 999px;
  padding: 0.38rem 0.65rem;
  background: rgba(21, 47, 31, 0.86);
  color: #fff;
  box-shadow: 0 10px 26px rgba(18, 52, 29, 0.22);
}

:deep(.leaflet-tooltip-top:before) {
  border-top-color: rgba(21, 47, 31, 0.86);
}

:deep(.leaflet-popup-content-wrapper) {
  border-radius: 18px;
  box-shadow: 0 18px 36px rgba(18, 52, 29, 0.16);
}

:deep(.leaflet-popup-content) {
  margin: 0;
}

:deep(.map-popup) {
  padding: 0.9rem 1rem;
  min-width: 15rem;
}

:deep(.map-popup-row) {
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
}

:deep(.map-popup-row + .map-popup-row) {
  margin-top: 0.65rem;
}

:deep(.map-popup-row strong) {
  color: var(--color-muted);
  font-size: 0.76rem;
}

:deep(.map-popup-row span) {
  color: var(--color-ink);
  font-size: 0.88rem;
  font-weight: 600;
}

@media (max-width: 760px) {
  .map-shell,
  .map-canvas {
    min-height: 28rem;
  }

  .top-left {
    top: 0.75rem;
    left: 0.75rem;
  }

  .bottom-left {
    left: 0.75rem;
    bottom: 0.75rem;
  }

  .middle-right {
    right: 0.75rem;
  }

  .map-badge,
  .map-chip,
  .map-loading {
    padding: 0.62rem 0.78rem;
  }
}
</style>
