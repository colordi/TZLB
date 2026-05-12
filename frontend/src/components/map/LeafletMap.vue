<script setup>
import L from "leaflet";
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue";
import "leaflet/dist/leaflet.css";

import { useToast } from "../../composables/useToast.js";
import {
  buildPopupRows,
  resolveFeatureHoverLabel,
  resolveFeaturePointLabel,
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
  showPointLabels: {
    type: Boolean,
    default: false,
  },
  viewName: {
    type: String,
    default: "",
  },
  views: {
    type: Array,
    default: () => [],
  },
  loadingViews: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:viewName", "update:basemapMode", "update:showPointLabels"]);

const { error, info } = useToast();
const showLayerMenu = ref(false);
const mapElement = ref(null);
const mapRef = shallowRef(null);
const zoomControlRef = shallowRef(null);
const basemapLayerRef = shallowRef(null);
const boundaryLayerRef = shallowRef(null);
const pointLayerRef = shallowRef(null);
const pointLabelLayerRef = shallowRef(null);
const locateMarkerRef = shallowRef(null);
const locateWatchId = ref(null);
const latestLocateLatLng = shallowRef(null);
const hasCenteredInitialLocate = ref(false);
const isLocatePending = ref(false);
const hasReportedLocateError = ref(false);

const featureCount = computed(() => props.geojson?.features?.length || 0);
const activeBasemapLabel = computed(() =>
  props.basemapMode === "satellite" ? "卫星底图" : "标准底图",
);
const isRealtimeLocating = computed(() => locateWatchId.value !== null);
const locateButtonLabel = computed(() =>
  isRealtimeLocating.value ? "重新居中到当前位置" : "开启实时定位",
);

const legendEntries = computed(() => [
  resolveFeatureSeverity("白"),
  resolveFeatureSeverity("轻"),
  resolveFeatureSeverity("中"),
  resolveFeatureSeverity("重"),
]);

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

function addPointLabel(feature, latlng) {
  const label = resolveFeaturePointLabel(feature.properties);
  if (!props.showPointLabels || !label || !pointLabelLayerRef.value) {
    return;
  }

  L.marker(latlng, {
    interactive: false,
    keyboard: false,
    icon: L.divIcon({
      className: "map-point-label-anchor",
      html: "",
      iconSize: [0, 0],
      iconAnchor: [0, 0],
    }),
  })
    .bindTooltip(label, {
      permanent: true,
      direction: "right",
      offset: [10, 0],
      opacity: 0.96,
      className: "map-point-label-tooltip",
    })
    .addTo(pointLabelLayerRef.value);
}

function drawGeoJson(data, shouldFit = true) {
  if (!mapRef.value) {
    return;
  }

  clearLayer(pointLayerRef);
  clearLayer(pointLabelLayerRef);
  if (!data?.features?.length) {
    if (shouldFit) {
      fitMapToAvailableLayer();
    }
    return;
  }

  const sortedData = {
    ...data,
    features: [...data.features].sort((a, b) => {
      const sa = resolveFeatureSeverity(a.properties).key;
      const sb = resolveFeatureSeverity(b.properties).key;
      return sa.localeCompare(sb);
    }),
  };

  if (props.showPointLabels) {
    pointLabelLayerRef.value = L.layerGroup().addTo(mapRef.value);
  }

  pointLayerRef.value = L.geoJSON(sortedData, {
    pointToLayer: (feature, latlng) => {
      const severity = resolveFeatureSeverity(feature.properties);
      const isBlank = severity.key === "level0";
      addPointLabel(feature, latlng);
      return L.circleMarker(latlng, {
        radius: severity.radius,
        fillColor: severity.color,
        color: isBlank ? "rgba(24, 50, 35, 0.5)" : "rgba(24, 50, 35, 0.78)",
        weight: isBlank ? 1.0 : 1.25,
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

function centerMapToLocatedPosition(latlng) {
  if (!mapRef.value) {
    return;
  }

  mapRef.value.setView(latlng, Math.max(mapRef.value.getZoom(), 13), {
    animate: true,
  });
}

function updateLocateMarker(latlng) {
  if (!mapRef.value) {
    return;
  }

  if (locateMarkerRef.value?.setLatLng) {
    locateMarkerRef.value.setLatLng(latlng);
    return;
  }

  clearLayer(locateMarkerRef);
  locateMarkerRef.value = L.marker(latlng, {
    icon: L.divIcon({
      className: "locate-user-marker-wrapper",
      html: LOCATE_MARKER_HTML,
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    }),
  }).addTo(mapRef.value);
}

function clearLocateWatch() {
  if (locateWatchId.value === null || !navigator.geolocation?.clearWatch) {
    locateWatchId.value = null;
    return;
  }

  navigator.geolocation.clearWatch(locateWatchId.value);
  locateWatchId.value = null;
}

function handleLocateSuccess(position) {
  if (!mapRef.value) {
    return;
  }

  const latlng = [position.coords.latitude, position.coords.longitude];
  latestLocateLatLng.value = latlng;
  isLocatePending.value = false;
  hasReportedLocateError.value = false;
  updateLocateMarker(latlng);

  if (!hasCenteredInitialLocate.value) {
    centerMapToLocatedPosition(latlng);
    hasCenteredInitialLocate.value = true;
    info("实时定位已开启，当前位置会持续更新。", "定位成功");
  }
}

function handleLocateError(positionError) {
  isLocatePending.value = false;
  const message =
    positionError?.code === 1
      ? "未授予定位权限，请在浏览器中允许访问位置信息。"
      : "暂时无法获取当前位置，请检查定位权限或网络。";

  if (positionError?.code === 1) {
    clearLocateWatch();
  }

  if (!hasReportedLocateError.value) {
    error(message, "定位失败");
    hasReportedLocateError.value = true;
  }
}

function locateToUser() {
  if (!navigator.geolocation?.watchPosition) {
    error("当前浏览器不支持定位能力。", "定位不可用");
    return;
  }

  if (isRealtimeLocating.value) {
    if (latestLocateLatLng.value) {
      centerMapToLocatedPosition(latestLocateLatLng.value);
      info("地图已重新居中到当前位置。", "定位成功");
      return;
    }
    info("正在获取当前位置，请稍候。", "定位中");
    return;
  }

  isLocatePending.value = true;
  latestLocateLatLng.value = null;
  hasCenteredInitialLocate.value = false;
  hasReportedLocateError.value = false;

  try {
    locateWatchId.value = navigator.geolocation.watchPosition(
      handleLocateSuccess,
      handleLocateError,
      {
        enableHighAccuracy: true,
        timeout: 8000,
        maximumAge: 60_000,
      },
    );
  } catch (locateError) {
    isLocatePending.value = false;
    hasReportedLocateError.value = true;
    error(`${locateError.message || locateError}`, "定位失败");
  }
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

watch(
  () => props.showPointLabels,
  () => {
    drawGeoJson(props.geojson, false);
  },
);

onBeforeUnmount(() => {
  clearLocateWatch();
  clearLayer(basemapLayerRef);
  clearLayer(boundaryLayerRef);
  clearLayer(pointLayerRef);
  clearLayer(pointLabelLayerRef);
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

    <div class="map-overlay top-left map-interactive-controls">
      <div class="control-row">
        <select
          class="map-overlay-select"
          :value="viewName"
          :disabled="loadingViews || !views.length"
          @change="emit('update:viewName', $event.target.value)"
        >
          <option v-if="!views.length" value="">暂无可用视图</option>
          <option v-for="view in views" :key="view.name" :value="view.name">
            {{ view.name }}
          </option>
        </select>
      </div>
      <div v-if="loading" class="map-loading">正在刷新点位数据…</div>
    </div>

    <div class="map-overlay top-right map-side-action">
      <div class="map-layer-control">
        <button
          type="button"
          class="map-fab"
          aria-label="切换图层"
          aria-controls="map-layer-menu"
          :aria-expanded="showLayerMenu"
          @click="showLayerMenu = !showLayerMenu"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
            <path d="M12.01 2.92a1.23 1.23 0 0 0-1.12.02l-8.5 4.5a1.2 1.2 0 0 0 0 2.12l8.5 4.5c.34.18.76.18 1.1 0l8.5-4.5a1.2 1.2 0 0 0 0-2.12l-8.5-4.5a1.23 1.23 0 0 0-1.1-.02ZM12.56 12.06c-.34.18-.76.18-1.1 0L2.96 7.56a.2.2 0 0 1 0-.36l8.5-4.5a.23.23 0 0 1 .2 0l8.5 4.5a.2.2 0 0 1 0 .36l-8.5 4.5Z" />
            <path d="M2.38 10.94a.5.5 0 0 0 .12.92l9.04 4.79a.99.99 0 0 0 .94 0l9.02-4.78a.5.5 0 0 0-.23-.94l-8.79 4.65a.99.99 0 0 1-.94 0l-8.8-4.66a.5.5 0 0 0-.36.02Z" />
            <path d="M2.38 14.94a.5.5 0 0 0 .12.92l9.04 4.79c.28.14.65.14.94 0l9.02-4.78a.5.5 0 0 0-.23-.94l-8.79 4.65a.99.99 0 0 1-.94 0l-8.8-4.66a.5.5 0 0 0-.36.02Z" />
          </svg>
        </button>
        
        <transition name="fade">
          <div id="map-layer-menu" v-show="showLayerMenu" class="layer-menu-popup">
            <button
               type="button"
               class="layer-menu-item"
               :class="{ 'is-active': basemapMode === 'standard' }"
               @click="emit('update:basemapMode', 'standard'); showLayerMenu = false"
             >
               <strong>标准地图</strong>
               <span>包含政区街道</span>
             </button>
             <button
               type="button"
               class="layer-menu-item"
               :class="{ 'is-active': basemapMode === 'satellite' }"
               @click="emit('update:basemapMode', 'satellite'); showLayerMenu = false"
             >
               <strong>卫星地图</strong>
               <span>高分辨率影像</span>
             </button>
             <button
               type="button"
               class="layer-menu-item"
               :class="{ 'is-active': showPointLabels }"
               :aria-pressed="showPointLabels"
               data-testid="point-label-toggle"
               @click="emit('update:showPointLabels', !showPointLabels)"
             >
               <strong>显示编号</strong>
               <span>{{ showPointLabels ? "编号标签已开启" : "点位旁显示编号" }}</span>
             </button>
          </div>
        </transition>
      </div>
    </div>

    <div class="map-overlay bottom-left">
      <div class="map-integrated-panel">
        <div class="panel-header">
          <strong>{{ featureCount }}</strong><span class="panel-header-suffix">个调查点位</span>
        </div>
        <div class="panel-divider"></div>
        <div class="map-legend">
          <div v-for="entry in legendEntries" :key="entry.key" class="legend-item">
            <span class="legend-dot" :style="{ backgroundColor: entry.color }"></span>
            <span>{{ entry.label }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="map-overlay right-fab map-side-action">
      <button
        type="button"
        class="map-fab"
        :class="{ 'is-active': isRealtimeLocating, 'is-loading': isLocatePending }"
        data-testid="map-locate-button"
        :aria-label="locateButtonLabel"
        :aria-pressed="isRealtimeLocating"
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
  z-index: 1001;
  pointer-events: none;
}

.top-left {
  top: 1.25rem;
  left: 1.25rem;
}

.top-right {
  top: 1.25rem;
  right: 1.25rem;
}

.bottom-left {
  left: 1.25rem;
  bottom: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  align-items: flex-start;
  pointer-events: auto;
}

.right-fab {
  right: 1.25rem;
  bottom: 8.5rem;
  pointer-events: auto;
}

:deep(.leaflet-right .leaflet-control) {
  margin-right: 1.25rem;
}

:deep(.leaflet-bottom .leaflet-control) {
  margin-bottom: 1.5rem;
}

.map-loading {
  display: inline-flex;
  flex-direction: column;
  gap: 0.18rem;
  padding: 0.78rem 0.95rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.8);
  color: var(--color-ink);
  box-shadow: 0 8px 30px rgba(18, 52, 29, 0.08);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
}

.map-interactive-controls {
  pointer-events: auto;
}

.control-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.map-overlay-select {
  padding: 0.55rem 2.2rem 0.55rem 1.05rem;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.75);
  color: var(--color-primary-strong);
  font-weight: 700;
  font-size: 0.92rem;
  box-shadow: 0 12px 30px rgba(18, 52, 29, 0.08);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  appearance: none;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23183223' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  background-size: 1.1rem;
  cursor: pointer;
  outline: none;
  transition: all 0.2s ease;
}

.map-overlay-select:focus {
  border-color: rgba(46, 125, 50, 0.3);
  box-shadow: 0 0 0 3px rgba(46, 125, 50, 0.1);
}

.map-overlay-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.map-layer-control {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.layer-menu-popup {
  position: absolute;
  top: calc(100% + 0.65rem);
  right: 0;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 18px;
  box-shadow: 0 16px 40px rgba(18, 52, 29, 0.12);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  width: 10rem;
}

.layer-menu-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 0.65rem 0.85rem;
  border-radius: 12px;
  text-align: left;
  border: 2px solid transparent;
  background: transparent;
  color: var(--color-ink);
  transition: all 0.2s;
  cursor: pointer;
}

.layer-menu-item:hover {
  background: rgba(46, 125, 50, 0.05);
}

.layer-menu-item.is-active {
  border-color: var(--color-primary-strong);
  background: rgba(240, 250, 240, 0.9);
}

.layer-menu-item strong {
  font-size: 0.95rem;
  font-weight: 700;
  margin-bottom: 0.2rem;
}

.layer-menu-item span {
  font-size: 0.78rem;
  color: var(--color-muted);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
  transform-origin: top right;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

.map-integrated-panel {
  display: flex;
  flex-direction: column;
  padding: 0.85rem 1.05rem;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 12px 36px rgba(18, 52, 29, 0.1);
  border-radius: 18px;
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
}

.map-integrated-panel .panel-header {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
  margin-bottom: 0.6rem;
  color: var(--color-primary-strong);
}

.map-integrated-panel .panel-header strong {
  font-size: 1.25rem;
  font-weight: 800;
  line-height: 1;
}

.map-integrated-panel .panel-header-suffix {
  font-size: 0.82rem;
  font-weight: 600;
}

.map-integrated-panel .panel-divider {
  height: 1px;
  background: linear-gradient(to right, rgba(46, 125, 50, 0.15), transparent);
  margin-bottom: 0.65rem;
}

.map-legend {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.map-legend .legend-item {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  color: var(--color-ink);
  font-size: 0.85rem;
  font-weight: 600;
  white-space: nowrap;
}

.map-legend .legend-dot {
  width: 0.85rem;
  height: 0.85rem;
  border-radius: 999px;
  box-shadow: inset 0 0 0 1px rgba(18, 52, 29, 0.12);
}

.map-loading {
  color: var(--color-muted);
  font-size: 0.82rem;
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
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.75);
  color: var(--color-primary-strong);
  box-shadow: 0 12px 26px rgba(18, 52, 29, 0.08);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  transition: all 0.2s ease;
}

.map-fab:hover {
  background: rgba(255, 255, 255, 0.9);
}

.map-fab.is-active {
  border-color: rgba(47, 128, 237, 0.34);
  background: rgba(232, 241, 255, 0.92);
  color: #2f80ed;
}

.map-fab.is-loading svg {
  animation: locate-pulse 1.1s ease-in-out infinite;
}

.map-fab svg {
  width: 1.15rem;
  height: 1.15rem;
  fill: currentColor;
}

@keyframes locate-pulse {
  0%,
  100% {
    transform: scale(1);
  }

  50% {
    transform: scale(0.88);
  }
}

:deep(.leaflet-bar) {
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 12px 26px rgba(18, 52, 29, 0.08);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
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
  border-bottom: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 0;
  color: var(--color-primary-strong);
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
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

:deep(.map-point-label-anchor) {
  background: transparent;
  border: none;
}

:deep(.map-point-label-tooltip) {
  padding: 0.26rem 0.48rem;
  border: 1px solid rgba(46, 125, 50, 0.2);
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-primary-strong);
  font-size: 0.76rem;
  font-weight: 800;
  pointer-events: none;
  box-shadow: 0 8px 18px rgba(18, 52, 29, 0.16);
}

:deep(.leaflet-tooltip-right.map-point-label-tooltip:before) {
  border-right-color: rgba(255, 255, 255, 0.92);
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

  .top-right {
    top: 0.75rem;
    right: 1rem;
  }

  .bottom-left {
    left: 1rem;
    bottom: 1rem;
  }

  .right-fab {
    right: 1rem;
    bottom: 8rem;
  }

  :deep(.leaflet-right .leaflet-control) {
    margin-right: 1rem;
  }
  
  :deep(.leaflet-bottom .leaflet-control) {
    margin-bottom: 1rem;
  }

  .map-chip,
  .map-loading {
    padding: 0.62rem 0.78rem;
  }
}
</style>
