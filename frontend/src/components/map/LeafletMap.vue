<script setup>
import L from "leaflet";
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue";
import "leaflet/dist/leaflet.css";

import { useToast } from "../../composables/useToast.js";
import {
  hasFeatureSeverityField,
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
    default: "satellite",
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
    default: true,
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
  whiteMothSiteAddMode: {
    type: Boolean,
    default: false,
  },
  whiteMothSiteDraftLocation: {
    type: Object,
    default: null,
  },
  whiteMothSiteSaving: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits([
  "update:viewName",
  "update:basemapMode",
  "update:showPointLabels",
  "feature-click",
  "map-click",
  "toggle-white-moth-site-add",
]);

const { error, info } = useToast();
const showLayerMenu = ref(false);
const mapElement = ref(null);
const mapRef = shallowRef(null);
const basemapLayerRef = shallowRef(null);
const basemapAnnotationLayerRef = shallowRef(null);
const boundaryLayerRef = shallowRef(null);
const pointLayerRef = shallowRef(null);
const pointLabelLayerRef = shallowRef(null);
const locateMarkerRef = shallowRef(null);
const whiteMothSiteDraftMarkerRef = shallowRef(null);
const locateWatchId = ref(null);
const latestLocateLatLng = shallowRef(null);
const hasCenteredInitialLocate = ref(false);
const isLocatePending = ref(false);
const hasReportedLocateError = ref(false);
const showLegend = ref(true);
const fitPending = ref(false);

const HAZARD_POINT_COLOR = "#EC6D64";
const POINT_OUTLINE_COLOR = "#000000";
const HAZARD_POINT_STYLE = {
  key: "hazard-point",
  color: HAZARD_POINT_COLOR,
  radius: 8,
  label: "危害点位",
};

const featureCount = computed(() => props.geojson?.features?.length || 0);
const activeBasemapLabel = computed(() =>
  props.basemapMode === "satellite" ? "卫星底图" : "标准底图",
);
const isRealtimeLocating = computed(() => locateWatchId.value !== null);
const locateButtonLabel = computed(() =>
  isRealtimeLocating.value ? "重新居中到当前位置" : "开启实时定位",
);
const whiteMothSiteAddButtonLabel = computed(() =>
  props.whiteMothSiteAddMode ? "取消添加美国白蛾点位" : "添加美国白蛾点位",
);
const pointLabelMenuDescription = computed(() =>
  props.showPointLabels ? "当前范围编号已开启" : "开启后显示当前范围编号",
);
const preferIdentifierHover = computed(() => true);
const usesSeverityLegend = computed(() => hasFeatureSeverityField(props.popupFields));

const severityLegendEntries = computed(() =>
  usesSeverityLegend.value
    ? [
        resolveFeatureSeverity("无"),
        resolveFeatureSeverity("轻"),
        resolveFeatureSeverity("中"),
        resolveFeatureSeverity("重"),
      ]
    : [HAZARD_POINT_STYLE],
);

const TIANDITU_IMAGERY_ANNOTATION_URL =
  "https://t0.tianditu.gov.cn/cia_w/wmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER=cia&STYLE=default&FORMAT=tiles&TILEMATRIXSET=w&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=4267820f43926eaf808d61dc07269beb";

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
    annotation: {
      url: TIANDITU_IMAGERY_ANNOTATION_URL,
      options: {
        maxZoom: 19,
        maxNativeZoom: 18,
        attribution: "&copy; 天地图",
      },
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

const WHITE_MOTH_SITE_DRAFT_MARKER_HTML = `
  <div class="white-moth-site-draft-marker">
    <span></span>
  </div>
`;

const POINT_LABEL_RENDER_LIMIT = 100;



function escapeHtml(value) {
  return `${value ?? ""}`
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function resolveBoundaryStyle() {
  return {
    color: "#ff7f00",
    fillOpacity: 0,
  };
}

function clearLayer(layerRef) {
  if (layerRef.value) {
    layerRef.value.remove();
    layerRef.value = null;
  }
}

function updateWhiteMothSiteDraftMarker(location = props.whiteMothSiteDraftLocation) {
  if (!mapRef.value) {
    return;
  }

  clearLayer(whiteMothSiteDraftMarkerRef);
  if (!location || !Number.isFinite(Number(location.latitude)) || !Number.isFinite(Number(location.longitude))) {
    return;
  }

  whiteMothSiteDraftMarkerRef.value = L.marker([location.latitude, location.longitude], {
    interactive: false,
    keyboard: false,
    icon: L.divIcon({
      className: "white-moth-site-draft-marker-wrapper",
      html: WHITE_MOTH_SITE_DRAFT_MARKER_HTML,
      iconSize: [30, 30],
      iconAnchor: [15, 15],
    }),
  }).addTo(mapRef.value);
}

function drawBasemap(mode = "standard") {
  if (!mapRef.value) {
    return;
  }

  const config = BASEMAP_CONFIG[mode] ?? BASEMAP_CONFIG.standard;
  clearLayer(basemapAnnotationLayerRef);
  clearLayer(basemapLayerRef);
  basemapLayerRef.value = L.tileLayer(config.url, config.options).addTo(mapRef.value);

  if (config.annotation) {
    basemapAnnotationLayerRef.value = L.tileLayer(
      config.annotation.url,
      config.annotation.options,
    ).addTo(mapRef.value);
  }
}

function fitMapToAvailableLayer() {
  if (!mapRef.value || fitPending.value) {
    return;
  }

  fitPending.value = true;
  window.requestAnimationFrame(() => {
    fitPending.value = false;
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
  });
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

function buildPointLabelMarker(label, latlng) {
  const safeLabel = escapeHtml(label);

  return L.marker(latlng, {
    interactive: false,
    keyboard: false,
    icon: L.divIcon({
      className: "map-point-label-marker",
      html: `<span class="map-point-label-text">${safeLabel}</span>`,
      iconSize: [1, 1],
      iconAnchor: [0, 0],
    }),
  });
}

function isValidLngLatPair(value) {
  return (
    Array.isArray(value) &&
    value.length >= 2 &&
    Number.isFinite(Number(value[0])) &&
    Number.isFinite(Number(value[1]))
  );
}

function collectFeatureCoordinatePairs(coordinates, pairs = []) {
  if (isValidLngLatPair(coordinates)) {
    pairs.push([Number(coordinates[0]), Number(coordinates[1])]);
    return pairs;
  }

  if (Array.isArray(coordinates)) {
    coordinates.forEach((item) => collectFeatureCoordinatePairs(item, pairs));
  }

  return pairs;
}

function extractFeatureLabelLatLng(feature) {
  if (!feature?.geometry) {
    return null;
  }

  const coordinates = feature.geometry.coordinates;
  if (feature.geometry.type === "Point") {
    if (!isValidLngLatPair(coordinates)) {
      return null;
    }

    return [Number(coordinates[1]), Number(coordinates[0])];
  }

  const pairs = collectFeatureCoordinatePairs(coordinates);
  if (!pairs.length) {
    return null;
  }

  const bounds = pairs.reduce(
    (result, [lng, lat]) => ({
      minLng: Math.min(result.minLng, lng),
      maxLng: Math.max(result.maxLng, lng),
      minLat: Math.min(result.minLat, lat),
      maxLat: Math.max(result.maxLat, lat),
    }),
    {
      minLng: Infinity,
      maxLng: -Infinity,
      minLat: Infinity,
      maxLat: -Infinity,
    },
  );

  if (!Number.isFinite(bounds.minLng) || !Number.isFinite(bounds.minLat)) {
    return null;
  }

  return [(bounds.minLat + bounds.maxLat) / 2, (bounds.minLng + bounds.maxLng) / 2];
}

function renderPointLabels(data = props.geojson) {
  clearLayer(pointLabelLayerRef);

  if (!mapRef.value || !props.showPointLabels || !data?.features?.length) {
    return;
  }

  const bounds = mapRef.value.getBounds?.();
  if (!bounds?.contains) {
    return;
  }

  let renderedCount = 0;
  for (const feature of data.features) {
    if (renderedCount >= POINT_LABEL_RENDER_LIMIT) {
      break;
    }

    const label = resolveFeaturePointLabel(feature?.properties || {});
    if (!label) {
      continue;
    }

    const latlng = extractFeatureLabelLatLng(feature);
    if (!latlng || !bounds.contains(latlng)) {
      continue;
    }

    if (!pointLabelLayerRef.value) {
      pointLabelLayerRef.value = L.layerGroup().addTo(mapRef.value);
    }

    buildPointLabelMarker(label, latlng).addTo(pointLabelLayerRef.value);
    renderedCount += 1;
  }

  pointLabelLayerRef.value?.bringToFront?.();
}

function resolveFeaturePathStyle(properties = {}) {
  const severity = usesSeverityLegend.value
    ? resolveFeatureSeverity(properties)
    : HAZARD_POINT_STYLE;
  const isBlank = usesSeverityLegend.value && severity.key === "level0";

  return {
    color: POINT_OUTLINE_COLOR,
    fillColor: severity.color,
    fillOpacity: isBlank ? 0.52 : 0.36,
    opacity: isBlank ? 0.78 : 0.95,
    weight: isBlank ? 1.2 : 1.6,
  };
}

function resolvePointStyle(properties = {}) {
  return usesSeverityLegend.value ? resolveFeatureSeverity(properties) : HAZARD_POINT_STYLE;
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

  const sortedData = {
    ...data,
    features: usesSeverityLegend.value
      ? [...data.features].sort((a, b) => {
          const sa = resolveFeatureSeverity(a.properties).key;
          const sb = resolveFeatureSeverity(b.properties).key;
          return sa.localeCompare(sb);
        })
      : [...data.features],
  };

  pointLayerRef.value = L.geoJSON(sortedData, {
    style: (feature) =>
      feature?.geometry?.type === "Point" ? {} : resolveFeaturePathStyle(feature?.properties || {}),
    pointToLayer: (feature, latlng) => {
      const severity = resolvePointStyle(feature.properties);
      const isBlank = usesSeverityLegend.value && severity.key === "level0";
      return L.circleMarker(latlng, {
        radius: severity.radius,
        fillColor: severity.color,
        color: POINT_OUTLINE_COLOR,
        weight: 1.45,
        fillOpacity: isBlank ? 0.96 : 0.88,
      });
    },
    onEachFeature: (feature, layer) => {
      const hoverLabel = resolveFeatureHoverLabel(props.popupFields, feature.properties, {
        preferIdentifier: preferIdentifierHover.value,
      });
      if (hoverLabel) {
        layer.bindTooltip(hoverLabel, {
          direction: "top",
          sticky: true,
          opacity: 0.96,
        });
      }

      layer.on("click", () => {
        emit("feature-click", feature);
      });
    },
  }).addTo(mapRef.value);

  pointLayerRef.value.bringToFront();
  if (shouldFit) {
    fitMapToAvailableLayer();
  }
}

function refreshPointLabels() {
  renderPointLabels(props.geojson);
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

function handleMapClick(event) {
  if (!props.whiteMothSiteAddMode || !event?.latlng) {
    return;
  }

  emit("map-click", {
    latitude: event.latlng.lat,
    longitude: event.latlng.lng,
  });
}

defineExpose({
  locateToUser,
});

onMounted(() => {
  mapRef.value = L.map(mapElement.value, {
    zoomControl: false,
    attributionControl: true,
  }).setView([39.91, 116.72], 11);

  drawBasemap(props.basemapMode);
  drawBoundaryGeoJson(props.boundaryGeojson);
  drawGeoJson(props.geojson, props.autoFitOnDataChange);
  renderPointLabels(props.geojson);
  updateWhiteMothSiteDraftMarker();
  mapRef.value.on?.("moveend", refreshPointLabels);
  mapRef.value.on?.("zoomend", refreshPointLabels);
  mapRef.value.on?.("click", handleMapClick);
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
    renderPointLabels(value);
  },
  { deep: true },
);

watch(
  () => props.popupFields,
  () => {
    drawGeoJson(props.geojson, false);
  },
  { deep: true },
);

watch(
  () => props.showPointLabels,
  () => {
    renderPointLabels(props.geojson);
  },
);

watch(
  () => props.whiteMothSiteDraftLocation,
  (value) => {
    updateWhiteMothSiteDraftMarker(value);
  },
  { deep: true },
);

onBeforeUnmount(() => {
  clearLocateWatch();
  clearLayer(basemapAnnotationLayerRef);
  clearLayer(basemapLayerRef);
  clearLayer(boundaryLayerRef);
  clearLayer(pointLayerRef);
  clearLayer(pointLabelLayerRef);
  clearLayer(locateMarkerRef);
  clearLayer(whiteMothSiteDraftMarkerRef);

  if (mapRef.value) {
    mapRef.value.off?.("moveend", refreshPointLabels);
    mapRef.value.off?.("zoomend", refreshPointLabels);
    mapRef.value.off?.("click", handleMapClick);
    mapRef.value.remove();
    mapRef.value = null;
  }
});
</script>

<template>
  <section class="map-shell">
    <div ref="mapElement" class="map-canvas"></div>

    <div class="map-overlay bottom-left">
      <div
        class="map-legend-container"
        @mouseenter="showLegend = true"
        @mouseleave="showLegend = false"
      >
        <div v-show="showLegend" class="map-integrated-panel">
          <div class="panel-header">
            <span class="panel-header-title-group">
              <strong>{{ featureCount }}</strong>
              <span class="panel-header-suffix">个调查点位</span>
            </span>
          </div>
          <div class="panel-divider"></div>
          <div class="map-legend">
            <div v-for="entry in severityLegendEntries" :key="entry.key" class="legend-item">
              <span class="legend-dot" :style="{ backgroundColor: entry.color }"></span>
              <span>{{ entry.label }}</span>
            </div>
          </div>
        </div>
        <button
          v-show="!showLegend"
          type="button"
          class="legend-restore-btn"
          aria-label="显示图例"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="8" y1="6" x2="21" y2="6" />
            <line x1="8" y1="12" x2="21" y2="12" />
            <line x1="8" y1="18" x2="21" y2="18" />
            <circle cx="4" cy="6" r="1" fill="currentColor" stroke="none" />
            <circle cx="4" cy="12" r="1" fill="currentColor" stroke="none" />
            <circle cx="4" cy="18" r="1" fill="currentColor" stroke="none" />
          </svg>
          <span>图例</span>
        </button>
      </div>
    </div>

    <div class="map-overlay right-fab map-side-action map-fab-stack">
      <button
        type="button"
        class="map-fab"
        :class="{ 'is-active': whiteMothSiteAddMode, 'is-loading': whiteMothSiteSaving }"
        data-testid="map-add-white-moth-site-button"
        :aria-label="whiteMothSiteAddButtonLabel"
        :aria-pressed="whiteMothSiteAddMode"
        :disabled="whiteMothSiteSaving"
        @click="emit('toggle-white-moth-site-add')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M12 2.75A7.25 7.25 0 0 0 4.75 10c0 4.97 5.67 10.22 5.91 10.44a2 2 0 0 0 2.68 0c.24-.22 5.91-5.47 5.91-10.44A7.25 7.25 0 0 0 12 2.75Zm0 16.58C10.53 17.88 6.25 13.48 6.25 10a5.75 5.75 0 1 1 11.5 0c0 3.48-4.28 7.88-5.75 9.33ZM12.75 7.25a.75.75 0 0 0-1.5 0v2h-2a.75.75 0 0 0 0 1.5h2v2a.75.75 0 0 0 1.5 0v-2h2a.75.75 0 0 0 0-1.5h-2v-2Z"
          />
        </svg>
      </button>
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
  width: 100%;
  height: 100%;
  min-height: 100%;
  overflow: hidden;
  background: rgba(229, 244, 230, 0.54);
}

.map-canvas {
  width: 100%;
  height: 100%;
  min-height: 100%;
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
  bottom: 1.5rem;
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

.map-integrated-panel {
  position: relative;
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
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.6rem;
  color: var(--color-primary-strong);
}

.panel-header-title-group {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
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

.legend-close-btn {
  width: 1.5rem;
  height: 1.5rem;
  padding: 0;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s;
  margin-left: 0.5rem;
}

.legend-close-btn:hover {
  background: rgba(0, 0, 0, 0.06);
}

.map-legend-container {
  position: relative;
}

.legend-restore-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.85rem;
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--color-primary-strong);
  font-size: 0.82rem;
  font-weight: 700;
  box-shadow: 0 8px 24px rgba(18, 52, 29, 0.1);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  cursor: pointer;
  transition: all 0.15s;
  pointer-events: auto;
}

.legend-restore-btn:hover {
  background: rgba(255, 255, 255, 0.92);
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
  box-sizing: border-box;
  border: 1px solid rgba(0, 0, 0, 0.85);
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

.map-fab-stack {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
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

:deep(.white-moth-site-draft-marker-wrapper) {
  background: transparent;
  border: none;
}

:deep(.white-moth-site-draft-marker) {
  position: relative;
  width: 30px;
  height: 30px;
}

:deep(.white-moth-site-draft-marker::before) {
  content: "";
  position: absolute;
  inset: 1px;
  border-radius: 999px;
  background: rgba(47, 128, 237, 0.18);
  animation: draft-marker-pulse 1.3s ease-in-out infinite;
}

:deep(.white-moth-site-draft-marker span) {
  position: absolute;
  inset: 8px;
  border-radius: 999px;
  background: #2f80ed;
  border: 2px solid #fff;
  box-shadow: 0 8px 16px rgba(47, 128, 237, 0.34);
}

@keyframes draft-marker-pulse {
  0%,
  100% {
    transform: scale(0.82);
    opacity: 0.72;
  }

  50% {
    transform: scale(1);
    opacity: 0.28;
  }
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

:deep(.map-point-label-marker) {
  width: 0;
  height: 0;
  background: transparent;
  border: none;
  pointer-events: none;
}

:deep(.map-point-label-text) {
  position: absolute;
  left: 8px;
  top: -0.45rem;
  color: var(--color-primary-strong);
  font-size: 0.76rem;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
  pointer-events: none;
  text-shadow:
    0 1px 0 #fff,
    1px 0 0 #fff,
    0 -1px 0 #fff,
    -1px 0 0 #fff,
    0 2px 4px rgba(18, 52, 29, 0.18);
}

@media (max-width: 760px) {
  .map-shell,
  .map-canvas {
    min-height: 100%;
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
    bottom: 1rem;
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
