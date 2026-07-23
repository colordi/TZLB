<script setup>
import L from "leaflet";
import { Layers, List, LocateFixed, MapPinPlus, Minus, Plus } from "@lucide/vue";
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue";
import "leaflet/dist/leaflet.css";

import { useToast } from "../../composables/useToast.js";
import {
  ADMIN_BOUNDARY_COLOR,
  HAZARD_POINT_COLOR,
  LOCATE_MARKER_COLOR,
  LOCATE_MARKER_GLOW,
  LOCATE_MARKER_HALO,
  LOCATE_MARKER_PULSE,
  LOCATE_MARKER_RING,
  POINT_LAYER_COLORS,
  POINT_OUTLINE_COLOR,
  REFERENCE_LAYER_COLORS,
  SURVEY_COMPLETION_COLOR,
} from "../../config/map-palette.js";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  hasFeatureParcelStatusField,
  hasFeatureSeverityField,
  resolveFeatureParcelStatus,
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
  referenceLayers: {
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
  mapFocusRequest: {
    type: Object,
    default: null,
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
  "viewport-change",
  "toggle-reference-layer",
  "toggle-white-moth-site-add",
]);

const { error, info } = useToast();
const showLayerMenu = ref(false);
const mapElement = ref(null);
const mapRef = shallowRef(null);
const basemapLayerRef = shallowRef(null);
const basemapAnnotationLayerRef = shallowRef(null);
const boundaryLayerRef = shallowRef(null);
const referenceLayerGroupRef = shallowRef(null);
const pointLayerRef = shallowRef(null);
const pointLabelLayerRef = shallowRef(null);
const surveyCompletionLayerRef = shallowRef(null);
const locateMarkerRef = shallowRef(null);
const whiteMothSiteDraftMarkerRef = shallowRef(null);
const locateWatchId = ref(null);
const latestLocateLatLng = shallowRef(null);
const hasCenteredInitialLocate = ref(false);
const isLocatePending = ref(false);
const hasReportedLocateError = ref(false);
const showLegend = ref(false);
const fitPending = ref(false);
let suppressNextMapClick = false;
let suppressMapClickResetTimer = null;

const HAZARD_POINT_STYLE = {
  key: "hazard-point",
  color: HAZARD_POINT_COLOR,
  radius: 8,
  label: "危害点位",
};
const ADMIN_BOUNDARY_LAYER_NAME = "通州区行政区边界";
const SURVEY_DATE_FIELD_KEYS = ["调查日期", "survey_date", "report_time"];

const featureCount = computed(() => props.geojson?.features?.length || 0);
const isRealtimeLocating = computed(() => locateWatchId.value !== null);
const locateButtonLabel = computed(() =>
  isRealtimeLocating.value ? "重新居中到当前位置" : "开启实时定位",
);
const whiteMothSiteAddButtonLabel = computed(() =>
  props.whiteMothSiteAddMode ? "取消添加美国白蛾点位" : "添加美国白蛾点位",
);
const pointLayerEntries = computed(() => {
  const fallbackName = props.viewName || "当前点位";
  const layerViews = props.views?.length ? props.views : [{ name: fallbackName }];

  return layerViews
    .map((view, index) => {
      const name = `${view?.name || ""}`.trim();
      if (!name) {
        return null;
      }

      return {
        key: name,
        label: name,
        active: name === props.viewName,
        color: POINT_LAYER_COLORS[index % POINT_LAYER_COLORS.length],
        countLabel: name === props.viewName ? featureCount.value : "切换",
      };
    })
    .filter(Boolean);
});
const referenceLayerEntries = computed(() =>
  (props.referenceLayers || [])
    .map((layer) => {
      const name = `${layer?.name || ""}`.trim();
      if (!name) {
        return null;
      }

      return {
        key: name,
        label: `${layer?.label || name}`.trim(),
        active: Boolean(layer?.active),
        loading: Boolean(layer?.loading),
      };
    })
    .filter(Boolean),
);
const preferIdentifierHover = computed(() => true);
const usesSeverityLegend = computed(() => hasFeatureSeverityField(props.popupFields));
const usesParcelStatusLegend = computed(
  () => !usesSeverityLegend.value && hasFeatureParcelStatusField(props.popupFields),
);
const usesSurveyCompletionMarkers = computed(() => hasSurveyDateField(props.popupFields));

const legendEntries = computed(() => {
  if (usesSeverityLegend.value) {
    return [
      resolveFeatureSeverity("无"),
      resolveFeatureSeverity("轻"),
      resolveFeatureSeverity("中"),
      resolveFeatureSeverity("重"),
    ];
  }

  if (usesParcelStatusLegend.value) {
    return [
      resolveFeatureParcelStatus({ "地块状态": "" }),
      resolveFeatureParcelStatus({ "地块状态": "调查" }),
      resolveFeatureParcelStatus({ "地块状态": "伐除" }),
    ];
  }

  return [HAZARD_POINT_STYLE];
});

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
      <svg
        viewBox="0 0 24 24"
        fill="${LOCATE_MARKER_COLOR}"
        style="filter: drop-shadow(0 8px 12px ${LOCATE_MARKER_GLOW}) drop-shadow(0 0 0.5px ${LOCATE_MARKER_HALO});"
        aria-hidden="true"
      >
        <path
          d="M20.28 3.72a1 1 0 0 0-1.04-.24L5.58 8.03a1 1 0 0 0-.13 1.84l5.53 2.51 2.51 5.53a1 1 0 0 0 1.84-.13l4.55-13.66a1 1 0 0 0-.24-1.04Z"
        />
      </svg>
    </span>
  </div>
`;

const WHITE_MOTH_SITE_DRAFT_MARKER_HTML = `
  <div class="white-moth-site-draft-marker">
    <span
      class="white-moth-site-draft-marker__pulse"
      style="background: ${LOCATE_MARKER_PULSE};"
    ></span>
    <span
      class="white-moth-site-draft-marker__dot"
      style="background: ${LOCATE_MARKER_COLOR}; box-shadow: 0 8px 16px ${LOCATE_MARKER_RING};"
    ></span>
  </div>
`;

const POINT_LABEL_FONT_SIZE = 12;
const POINT_LABEL_OFFSET_X = 8;
const POINT_LABEL_OFFSET_Y = -7;
const POINT_LABEL_PADDING_X = 2;
const POINT_LABEL_PADDING_Y = 2;

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
    color: ADMIN_BOUNDARY_COLOR,
    weight: 3,
    opacity: 0.72,
    fillOpacity: 0,
  };
}

function clearLayer(layerRef) {
  if (layerRef.value) {
    layerRef.value.remove();
    layerRef.value = null;
  }
}

function hasSurveyDateField(fields = []) {
  const dateFieldKeys = new Set(SURVEY_DATE_FIELD_KEYS.map((field) => field.toLowerCase()));
  return (fields || []).some((field) => {
    const normalizedField = `${field ?? ""}`.trim();
    return dateFieldKeys.has(normalizedField.toLowerCase());
  });
}

function hasFeatureCollectionFeatures(data) {
  return Array.isArray(data?.features) && data.features.length > 0;
}

function resolveReferenceLayerColor(index = 0) {
  return REFERENCE_LAYER_COLORS[index % REFERENCE_LAYER_COLORS.length];
}

function resolveReferenceLayerStyle(layer = {}, index = 0) {
  if (layer.name === ADMIN_BOUNDARY_LAYER_NAME) {
    return {
      ...resolveBoundaryStyle(),
      weight: 3.5,
      opacity: 0.88,
    };
  }

  const color = resolveReferenceLayerColor(index);
  return {
    color,
    fillColor: color,
    fillOpacity: 0.12,
    opacity: 0.82,
    weight: 1.5,
  };
}

function isNeutralPointStyle(pointStyle = {}) {
  return pointStyle?.key === "level0" || pointStyle?.key === "parcel-default";
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
      return;
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

function drawReferenceLayers(layers = props.referenceLayers) {
  if (!mapRef.value) {
    return;
  }

  clearLayer(referenceLayerGroupRef);
  const drawableLayers = (layers || [])
    .map((layer, index) => ({ layer, index }))
    .filter(({ layer }) => layer?.active && hasFeatureCollectionFeatures(layer.geojson));
  if (!drawableLayers.length) {
    return;
  }

  referenceLayerGroupRef.value = L.featureGroup().addTo(mapRef.value);
  drawableLayers.forEach(({ layer, index }) => {
    const layerStyle = resolveReferenceLayerStyle(layer, index);
    L.geoJSON(layer.geojson, {
      interactive: false,
      style: () => layerStyle,
      pointToLayer: (feature, latlng) =>
        L.circleMarker(latlng, {
          radius: 6,
          fillColor: layerStyle.fillColor || layerStyle.color,
          color: layerStyle.color,
          interactive: false,
          weight: 1.4,
          fillOpacity: 0.74,
        }),
    }).addTo(referenceLayerGroupRef.value);
  });
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

function buildSurveyCompletionMarker(latlng) {
  return L.marker(latlng, {
    interactive: false,
    keyboard: false,
    icon: L.divIcon({
      className: "map-survey-completion-marker",
      html: `<span class="map-survey-completion-check" style="background: ${SURVEY_COMPLETION_COLOR};" aria-hidden="true">✓</span>`,
      iconSize: [16, 16],
      iconAnchor: [8, 8],
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

function isPointFeature(feature) {
  return feature?.geometry?.type === "Point" && isValidLngLatPair(feature.geometry.coordinates);
}

function getPointFeatureLatLng(feature) {
  if (!isPointFeature(feature)) {
    return null;
  }

  const [lng, lat] = feature.geometry.coordinates;
  return [Number(lat), Number(lng)];
}

function getFeatureLatLngBounds(feature) {
  const pairs = collectFeatureCoordinatePairs(feature?.geometry?.coordinates);
  if (!pairs.length) {
    return null;
  }

  const bounds = L.latLngBounds(pairs.map(([lng, lat]) => [lat, lng]));
  return bounds.isValid?.() ? bounds : null;
}

function focusFeature(feature) {
  if (!mapRef.value || !feature?.geometry) {
    return;
  }

  const latlng = getPointFeatureLatLng(feature);
  if (latlng) {
    mapRef.value.setView(latlng, Math.max(mapRef.value.getZoom?.() || 11, 15), {
      animate: true,
    });
    return;
  }

  const bounds = getFeatureLatLngBounds(feature);
  if (bounds?.isValid?.()) {
    mapRef.value.fitBounds(bounds.pad(0.18), {
      animate: true,
      maxZoom: 16,
    });
  }
}

function getProjectedPoint(latlng) {
  const projected = mapRef.value?.latLngToLayerPoint?.(latlng);
  if (
    projected &&
    Number.isFinite(Number(projected.x)) &&
    Number.isFinite(Number(projected.y))
  ) {
    return {
      x: Number(projected.x),
      y: Number(projected.y),
    };
  }

  return null;
}

function estimateLabelTextWidth(label) {
  return Array.from(`${label}`).reduce((width, char) => {
    const isWideChar = /[^\x00-\xff]/.test(char);
    return width + (isWideChar ? POINT_LABEL_FONT_SIZE : POINT_LABEL_FONT_SIZE * 0.68);
  }, POINT_LABEL_FONT_SIZE * 0.2);
}

function estimateLabelBounds(label, projected) {
  const textWidth = estimateLabelTextWidth(label);
  const textHeight = POINT_LABEL_FONT_SIZE * 1.25;
  const left = projected.x + POINT_LABEL_OFFSET_X - POINT_LABEL_PADDING_X;
  const top = projected.y + POINT_LABEL_OFFSET_Y - POINT_LABEL_PADDING_Y;

  return {
    left,
    top,
    right: left + textWidth + POINT_LABEL_PADDING_X * 2,
    bottom: top + textHeight + POINT_LABEL_PADDING_Y * 2,
  };
}

function boundsIntersect(left, right) {
  return !(
    left.right <= right.left ||
    left.left >= right.right ||
    left.bottom <= right.top ||
    left.top >= right.bottom
  );
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

  const renderedLabelBounds = [];
  for (const feature of getTopmostPointFeatures(data.features)) {
    const label = resolveFeaturePointLabel(feature?.properties || {});
    if (!label) {
      continue;
    }

    const latlng = extractFeatureLabelLatLng(feature);
    if (!latlng || !bounds.contains(latlng)) {
      continue;
    }

    const projected = getProjectedPoint(latlng);
    if (!projected) {
      continue;
    }

    const labelBounds = estimateLabelBounds(label, projected);
    if (renderedLabelBounds.some((item) => boundsIntersect(item, labelBounds))) {
      continue;
    }

    if (!pointLabelLayerRef.value) {
      pointLabelLayerRef.value = L.layerGroup().addTo(mapRef.value);
    }

    buildPointLabelMarker(label, latlng).addTo(pointLabelLayerRef.value);
    renderedLabelBounds.push(labelBounds);
  }

  pointLabelLayerRef.value?.bringToFront?.();
}

function getSurveyDateValue(properties = {}) {
  for (const key of SURVEY_DATE_FIELD_KEYS) {
    const value = `${properties?.[key] ?? ""}`.trim();
    if (value) {
      return value;
    }
  }
  return "";
}

function renderSurveyCompletionMarkers(data = props.geojson) {
  clearLayer(surveyCompletionLayerRef);

  if (!mapRef.value || !usesSurveyCompletionMarkers.value || !data?.features?.length) {
    return;
  }

  for (const feature of data.features) {
    if (!getSurveyDateValue(feature?.properties || {})) {
      continue;
    }

    const latlng = extractFeatureLabelLatLng(feature);
    if (!latlng) {
      continue;
    }

    if (!surveyCompletionLayerRef.value) {
      surveyCompletionLayerRef.value = L.layerGroup().addTo(mapRef.value);
    }

    buildSurveyCompletionMarker(latlng).addTo(surveyCompletionLayerRef.value);
  }

  surveyCompletionLayerRef.value?.bringToFront?.();
}

function resolveFeaturePathStyle(properties = {}) {
  const pointStyle = resolvePointStyle(properties);
  if (usesParcelStatusLegend.value) {
    if (pointStyle.key === "parcel-default") {
      return {
        color: POINT_OUTLINE_COLOR,
        fillColor: pointStyle.color,
        fillOpacity: 0.88,
        opacity: 0.98,
        weight: 1.5,
      };
    }

    return {
      color: POINT_OUTLINE_COLOR,
      fillColor: pointStyle.color,
      fillOpacity: 0.7,
      opacity: 0.98,
      weight: 1.5,
    };
  }

  const isNeutral = isNeutralPointStyle(pointStyle);

  return {
    color: POINT_OUTLINE_COLOR,
    fillColor: pointStyle.color,
    fillOpacity: isNeutral ? 0.52 : 0.36,
    opacity: isNeutral ? 0.78 : 0.95,
    weight: isNeutral ? 1.2 : 1.6,
  };
}

function resolvePointStyle(properties = {}) {
  if (usesSeverityLegend.value) {
    return resolveFeatureSeverity(properties);
  }
  if (usesParcelStatusLegend.value) {
    return resolveFeatureParcelStatus(properties);
  }
  return HAZARD_POINT_STYLE;
}

function getPointRenderFeatures(features = []) {
  return usesSeverityLegend.value
    ? [...features].sort((a, b) => {
        const sa = resolveFeatureSeverity(a.properties).key;
        const sb = resolveFeatureSeverity(b.properties).key;
        return sa.localeCompare(sb);
      })
    : [...features];
}

function getTopmostPointFeatures(features = []) {
  return getPointRenderFeatures(features).reverse();
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
    features: getPointRenderFeatures(data.features),
  };

  pointLayerRef.value = L.geoJSON(sortedData, {
    style: (feature) =>
      feature?.geometry?.type === "Point"
        ? {}
        : resolveFeaturePathStyle(feature?.properties || {}),
    pointToLayer: (feature, latlng) => {
      const pointStyle = resolvePointStyle(feature.properties);
      const isNeutral = isNeutralPointStyle(pointStyle);
      return L.circleMarker(latlng, {
        radius: pointStyle.radius,
        fillColor: pointStyle.color,
        color: POINT_OUTLINE_COLOR,
        weight: 1.45,
        fillOpacity: isNeutral ? 0.96 : 0.88,
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

      layer.on("click", (event) => {
        if (event?.originalEvent) {
          L.DomEvent?.stopPropagation?.(event.originalEvent);
        }
        showLayerMenu.value = false;
        suppressMapClickOnce();
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

function refreshPointRendering() {
  drawGeoJson(props.geojson, false);
  renderSurveyCompletionMarkers(props.geojson);
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

function toggleLayerMenu() {
  showLayerMenu.value = !showLayerMenu.value;
}

function suppressMapClickOnce() {
  suppressNextMapClick = true;
  if (suppressMapClickResetTimer) {
    window.clearTimeout(suppressMapClickResetTimer);
  }
  suppressMapClickResetTimer = window.setTimeout(() => {
    suppressNextMapClick = false;
    suppressMapClickResetTimer = null;
  }, 0);
}

function selectBasemapMode(mode) {
  emit("update:basemapMode", mode);
  showLayerMenu.value = false;
}

function selectPointLayer(viewName) {
  if (viewName && viewName !== props.viewName) {
    emit("update:viewName", viewName);
  }
}

function togglePointLabels() {
  emit("update:showPointLabels", !props.showPointLabels);
}

function toggleReferenceLayer(layerName) {
  if (layerName) {
    emit("toggle-reference-layer", layerName);
  }
}

function zoomInMap() {
  mapRef.value?.zoomIn?.();
}

function zoomOutMap() {
  mapRef.value?.zoomOut?.();
}

function handleMapClick(event) {
  if (suppressNextMapClick) {
    suppressNextMapClick = false;
    if (suppressMapClickResetTimer) {
      window.clearTimeout(suppressMapClickResetTimer);
      suppressMapClickResetTimer = null;
    }
    return;
  }

  showLayerMenu.value = false;

  if (!event?.latlng) {
    return;
  }

  emit("map-click", {
    latitude: event.latlng.lat,
    longitude: event.latlng.lng,
  });
}

function getCurrentViewport() {
  const map = mapRef.value;
  const bounds = map?.getBounds?.();
  if (!bounds?.getWest || !bounds?.getSouth || !bounds?.getEast || !bounds?.getNorth) {
    return null;
  }

  return {
    bbox: [
      bounds.getWest(),
      bounds.getSouth(),
      bounds.getEast(),
      bounds.getNorth(),
    ],
    zoom: map.getZoom?.() ?? null,
  };
}

function emitViewportChange() {
  const viewport = getCurrentViewport();
  if (viewport) {
    emit("viewport-change", viewport);
  }
}

function handleMoveEnd() {
  refreshPointLabels();
  emitViewportChange();
}

function handleZoomEnd() {
  refreshPointRendering();
  emitViewportChange();
}

defineExpose({
  locateToUser,
});

onMounted(() => {
  mapRef.value = L.map(mapElement.value, {
    zoomControl: false,
    attributionControl: false,
  }).setView([39.91, 116.72], 11);

  drawBasemap(props.basemapMode);
  drawBoundaryGeoJson(props.boundaryGeojson);
  drawReferenceLayers(props.referenceLayers);
  drawGeoJson(props.geojson, props.autoFitOnDataChange);
  renderSurveyCompletionMarkers(props.geojson);
  renderPointLabels(props.geojson);
  updateWhiteMothSiteDraftMarker();
  emitViewportChange();
  mapRef.value.on?.("moveend", handleMoveEnd);
  mapRef.value.on?.("zoomend", handleZoomEnd);
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
  () => props.referenceLayers,
  (value) => {
    drawReferenceLayers(value);
    drawGeoJson(props.geojson, false);
    renderSurveyCompletionMarkers(props.geojson);
    renderPointLabels(props.geojson);
  },
  { deep: true },
);

watch(
  () => props.geojson,
  (value) => {
    drawGeoJson(value, props.autoFitOnDataChange);
    renderSurveyCompletionMarkers(value);
    renderPointLabels(value);
  },
  { deep: true },
);

watch(
  () => props.popupFields,
  () => {
    drawGeoJson(props.geojson, false);
    renderSurveyCompletionMarkers(props.geojson);
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
  () => props.mapFocusRequest,
  (request) => {
    focusFeature(request?.feature);
  },
  { deep: true },
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
  clearLayer(referenceLayerGroupRef);
  clearLayer(pointLayerRef);
  clearLayer(pointLabelLayerRef);
  clearLayer(surveyCompletionLayerRef);
  clearLayer(locateMarkerRef);
  clearLayer(whiteMothSiteDraftMarkerRef);
  if (suppressMapClickResetTimer) {
    window.clearTimeout(suppressMapClickResetTimer);
    suppressMapClickResetTimer = null;
  }
  suppressNextMapClick = false;

  if (mapRef.value) {
    mapRef.value.off?.("moveend", handleMoveEnd);
    mapRef.value.off?.("zoomend", handleZoomEnd);
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
      <div class="map-legend-container">
        <div
          v-if="showLegend"
          class="map-integrated-panel rounded-xl border bg-card/95 shadow-md backdrop-blur"
          data-testid="map-legend-panel"
        >
          <div class="panel-header">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              class="panel-header-title-group"
              data-testid="map-legend-collapse-button"
              aria-label="收起图例"
              @click="showLegend = false"
            >
              <List aria-hidden="true" />
              <strong>图例</strong>
            </Button>
          </div>
          <div class="panel-divider"></div>
          <div class="map-legend">
            <div v-for="entry in legendEntries" :key="entry.key" class="legend-item">
              <span class="legend-dot" :style="{ backgroundColor: entry.color }"></span>
              <span>{{ entry.label }}</span>
            </div>
          </div>
        </div>
        <div
          v-else
          class="legend-restore-group rounded-xl border bg-card/95 shadow-md backdrop-blur"
        >
          <Button
            type="button"
            variant="ghost"
            size="icon"
            class="legend-restore-btn"
            data-testid="map-legend-expand-button"
            aria-label="展开图例"
            @click="showLegend = true"
          >
            <List aria-hidden="true" />
          </Button>
        </div>
      </div>
    </div>

    <div class="map-overlay map-tool-stack" aria-label="地图工具">
      <div class="map-tool-group rounded-xl border bg-card/95 shadow-md backdrop-blur">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="map-tool-btn"
          :class="{ 'is-active': showLayerMenu }"
          data-testid="map-layer-button"
          aria-label="图层控制"
          aria-controls="map-layer-panel"
          :aria-expanded="showLayerMenu"
          @click="toggleLayerMenu"
        >
          <Layers aria-hidden="true" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="map-tool-btn"
          :class="{ 'is-active': isRealtimeLocating, 'is-loading': isLocatePending }"
          data-testid="map-locate-button"
          :aria-label="locateButtonLabel"
          :aria-pressed="isRealtimeLocating"
          @click="locateToUser"
        >
          <LocateFixed aria-hidden="true" />
        </Button>
      </div>

      <div class="map-tool-group rounded-xl border bg-card/95 shadow-md backdrop-blur">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="map-tool-btn"
          data-testid="map-zoom-in-button"
          aria-label="放大地图"
          @click="zoomInMap"
        >
          <Plus aria-hidden="true" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="map-tool-btn"
          data-testid="map-zoom-out-button"
          aria-label="缩小地图"
          @click="zoomOutMap"
        >
          <Minus aria-hidden="true" />
        </Button>
      </div>

      <div class="map-tool-group rounded-xl border bg-card/95 shadow-md backdrop-blur">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="map-tool-btn"
          :class="{ 'is-active': whiteMothSiteAddMode, 'is-loading': whiteMothSiteSaving }"
          data-testid="map-add-white-moth-site-button"
          :aria-label="whiteMothSiteAddButtonLabel"
          :aria-pressed="whiteMothSiteAddMode"
          :disabled="whiteMothSiteSaving"
          @click="emit('toggle-white-moth-site-add')"
        >
          <MapPinPlus aria-hidden="true" />
        </Button>
      </div>
    </div>

    <aside
      v-if="showLayerMenu"
      id="map-layer-panel"
      class="map-layer-panel rounded-xl border bg-card/95 shadow-md backdrop-blur"
      aria-label="地图图层"
    >
      <h2>地图图层</h2>
      <section class="map-layer-panel-group">
        <h3>基础图层</h3>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          class="map-base-layer-option"
          :class="{ 'is-active': basemapMode === 'standard' }"
          data-testid="map-layer-standard"
          @click="selectBasemapMode('standard')"
        >
          <Checkbox
            :model-value="basemapMode === 'standard'"
            as="span"
            tabindex="-1"
            aria-hidden="true"
            class="pointer-events-none"
          />
          <span>标准地图</span>
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          class="map-base-layer-option"
          :class="{ 'is-active': basemapMode === 'satellite' }"
          data-testid="map-layer-satellite"
          @click="selectBasemapMode('satellite')"
        >
          <Checkbox
            :model-value="basemapMode === 'satellite'"
            as="span"
            tabindex="-1"
            aria-hidden="true"
            class="pointer-events-none"
          />
          <span>卫星地图</span>
        </Button>
        <Button
          v-for="layer in referenceLayerEntries"
          :key="layer.key"
          type="button"
          variant="ghost"
          size="sm"
          class="map-base-layer-option"
          :class="{ 'is-active': layer.active, 'is-loading': layer.loading }"
          :data-testid="`map-reference-layer-${layer.key}`"
          :aria-pressed="layer.active"
          @click="toggleReferenceLayer(layer.key)"
        >
          <Checkbox
            :model-value="layer.active"
            as="span"
            tabindex="-1"
            aria-hidden="true"
            class="pointer-events-none"
          />
          <span>{{ layer.label }}</span>
          <span v-if="layer.loading" class="map-layer-count">加载中</span>
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          class="map-base-layer-option"
          :class="{ 'is-active': showPointLabels }"
          data-testid="map-layer-labels"
          :aria-pressed="showPointLabels"
          @click="togglePointLabels"
        >
          <Checkbox
            :model-value="showPointLabels"
            as="span"
            tabindex="-1"
            aria-hidden="true"
            class="pointer-events-none"
          />
          <span>编号标签</span>
        </Button>
      </section>
      <section class="map-layer-panel-group">
        <h3>点位图层</h3>
        <Button
          v-for="layer in pointLayerEntries"
          :key="layer.key"
          type="button"
          variant="ghost"
          size="sm"
          class="map-point-layer"
          :class="{ 'is-active': layer.active }"
          :data-testid="`map-point-layer-${layer.key}`"
          @click="selectPointLayer(layer.key)"
        >
          <span class="map-point-layer-dot" :style="{ background: layer.color }"></span>
          <span>{{ layer.label }}</span>
          <span class="map-layer-count">{{ layer.countLabel }}</span>
        </Button>
      </section>
    </aside>
  </section>
</template>

<style scoped>
/* 浮层视觉（bg-card/95、backdrop-blur、圆角、边框、阴影）走模板 Tailwind 类（规范 §7），
 * 此处只保留布局结构与 Leaflet 自有 DOM 的 :deep() 定制，颜色一律 var(--*) token。 */
.map-shell {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 100%;
  overflow: hidden;
  background: var(--muted);
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

.bottom-left {
  left: 1.25rem;
  bottom: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  align-items: flex-start;
  pointer-events: auto;
}

:deep(.leaflet-right .leaflet-control) {
  margin-right: 1.25rem;
}

:deep(.leaflet-bottom .leaflet-control) {
  margin-bottom: 1.5rem;
}

.map-integrated-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 0.85rem 1.05rem;
}

.map-integrated-panel .panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.6rem;
  color: var(--primary);
}

.panel-header-title-group {
  gap: 0.5rem;
  padding: 0 0.25rem;
  color: var(--primary);
}

.map-integrated-panel .panel-header strong {
  font-size: 0.98rem;
  font-weight: 800;
  line-height: 1;
}

.map-legend-container {
  position: relative;
}

.legend-restore-group {
  display: grid;
  overflow: hidden;
  pointer-events: auto;
}

.legend-restore-btn {
  width: 2.75rem;
  height: 2.75rem;
  padding: 0;
  border-radius: 0;
  color: var(--primary);
}

.map-integrated-panel .panel-divider {
  height: 1px;
  background: linear-gradient(
    to right,
    color-mix(in oklch, var(--primary) 20%, transparent),
    transparent
  );
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
  color: var(--foreground);
  font-size: 0.875rem;
  font-weight: 600;
  white-space: nowrap;
}

.map-legend .legend-dot {
  width: 0.85rem;
  height: 0.85rem;
  box-sizing: border-box;
  border: 1px solid color-mix(in oklch, var(--foreground) 85%, transparent);
  border-radius: 999px;
  box-shadow: inset 0 0 0 1px color-mix(in oklch, var(--foreground) 12%, transparent);
}

.map-tool-stack {
  top: 1.5rem;
  right: 1.5rem;
  display: grid;
  gap: 0.75rem;
  pointer-events: auto;
}

.map-tool-group {
  display: grid;
  overflow: hidden;
}

.map-tool-btn {
  width: 2.75rem;
  height: 2.75rem;
  padding: 0;
  border-radius: 0;
  color: var(--primary);
}

.map-tool-btn + .map-tool-btn {
  border-top: 1px solid var(--border);
}

.map-tool-btn.is-active {
  background: color-mix(in oklch, var(--primary) 12%, transparent);
  color: var(--primary);
}

.map-tool-btn.is-loading svg {
  animation: locate-pulse 1.1s ease-in-out infinite;
}

.map-layer-panel {
  position: absolute;
  top: 1.5rem;
  right: 4.9rem;
  z-index: 1001;
  width: min(250px, calc(100% - 6rem));
  max-height: calc(100% - 3rem);
  overflow: auto;
  padding: 1.15rem;
}

.map-layer-panel h2 {
  margin: 0 0 1rem;
  color: var(--primary);
  font-size: 1.125rem;
  font-weight: 700;
}

.map-layer-panel h3 {
  margin: 0 0 0.75rem;
  color: var(--muted-foreground);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.map-layer-panel-group + .map-layer-panel-group {
  margin-top: 1.15rem;
  padding-top: 1.15rem;
  border-top: 1px solid var(--border);
}

.map-base-layer-option,
.map-point-layer {
  justify-content: flex-start;
  gap: 0.75rem;
  width: 100%;
  min-height: 34px;
  padding: 0 0.75rem;
  color: var(--foreground);
  font-size: 0.875rem;
  font-weight: 500;
  text-align: left;
}

.map-base-layer-option:hover {
  color: var(--primary);
}

.map-base-layer-option span:nth-child(2),
.map-point-layer span:nth-child(2) {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.map-point-layer:hover,
.map-point-layer.is-active {
  background: color-mix(in oklch, var(--primary) 10%, transparent);
}

.map-point-layer-dot {
  width: 10px;
  height: 10px;
  flex: 0 0 auto;
  border-radius: 999px;
  background: var(--primary);
}

.map-layer-count {
  min-width: 1.6rem;
  color: var(--muted-foreground);
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
  font-weight: 800;
  text-align: right;
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
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: 0 12px 26px color-mix(in oklch, var(--foreground) 8%, transparent);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
}

:deep(.leaflet-bar a:hover) {
  background: var(--accent);
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
  background: color-mix(in oklch, var(--foreground) 18%, transparent);
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
  /* 填充色与投影为内联样式，取自 config/map-palette.js */
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

:deep(.white-moth-site-draft-marker__pulse) {
  position: absolute;
  inset: 1px;
  border-radius: 999px;
  animation: draft-marker-pulse 1.3s ease-in-out infinite;
  /* 背景色为内联样式，取自 config/map-palette.js */
}

:deep(.white-moth-site-draft-marker__dot) {
  position: absolute;
  inset: 8px;
  border: 2px solid var(--card);
  border-radius: 999px;
  /* 背景色与阴影为内联样式，取自 config/map-palette.js */
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
  background: color-mix(in oklch, var(--foreground) 88%, transparent);
  color: var(--primary-foreground);
  box-shadow: 0 10px 26px color-mix(in oklch, var(--foreground) 22%, transparent);
}

:deep(.leaflet-tooltip-top:before) {
  border-top-color: color-mix(in oklch, var(--foreground) 88%, transparent);
}

:deep(.map-survey-completion-marker) {
  width: 16px;
  height: 16px;
  background: transparent;
  border: none;
  pointer-events: none;
}

:deep(.map-survey-completion-check) {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border: 1.5px solid var(--card);
  border-radius: 999px;
  color: var(--card);
  font-size: 10px;
  font-weight: 900;
  line-height: 1;
  box-shadow:
    0 1px 3px color-mix(in oklch, var(--foreground) 24%, transparent),
    0 0 0 1px color-mix(in oklch, var(--success) 25%, transparent);
  pointer-events: none;
  /* 背景色为内联样式，取自 config/map-palette.js */
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
  color: var(--primary);
  font-size: 0.76rem;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
  pointer-events: none;
  text-shadow:
    0 1px 0 var(--card),
    1px 0 0 var(--card),
    0 -1px 0 var(--card),
    -1px 0 0 var(--card),
    0 2px 4px color-mix(in oklch, var(--foreground) 18%, transparent);
}

@media (max-width: 760px) {
  .map-shell,
  .map-canvas {
    min-height: 100%;
  }

  .bottom-left {
    left: 1rem;
    bottom: 1rem;
  }

  .map-tool-stack {
    right: 1rem;
    top: 4rem;
  }

  .map-layer-panel {
    top: 4rem;
    right: 4.25rem;
    width: min(15rem, calc(100% - 5.5rem));
    max-height: calc(100% - 5rem);
  }

  :deep(.leaflet-right .leaflet-control) {
    margin-right: 1rem;
  }

  :deep(.leaflet-bottom .leaflet-control) {
    margin-bottom: 1rem;
  }
}
</style>
