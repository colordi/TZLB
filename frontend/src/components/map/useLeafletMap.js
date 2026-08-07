import L from "leaflet";
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue";

import { useToast } from "../../composables/useToast.js";
import { POINT_LAYER_COLORS } from "../../config/map-palette.js";
import { getBasemapConfig } from "./leaflet/basemap.js";
import {
  collectFeatureCoordinatePairs,
  extractFeatureLabelLatLng,
  getPointFeatureLatLng,
} from "./leaflet/geometry.js";
import { boundsIntersect, estimateLabelBounds } from "./leaflet/labels.js";
import { clearLayer } from "./leaflet/layerUtils.js";
import {
  buildDraftSiteMarker,
  buildLocateMarker,
  buildPointLabelMarker,
  buildSurveyCompletionMarker,
} from "./leaflet/markers.js";
import {
  getLegendEntries,
  getPointRenderFeatures,
  getSurveyDateValue,
  getTopmostPointFeatures,
  hasFeatureCollectionFeatures,
  isNeutralPointStyle,
  POINT_OUTLINE_COLOR,
  resolveBoundaryStyle,
  resolveFeaturePathStyle,
  resolvePointStyle,
  resolveReferenceLayerStyle,
  usesParcelStatusLegend as computeUsesParcelStatusLegend,
  usesSeverityLegend as computeUsesSeverityLegend,
  usesSurveyCompletionMarkers as computeUsesSurveyCompletionMarkers,
} from "./leaflet/styles.js";
import { resolveFeatureHoverLabel, resolveFeaturePointLabel } from "./popupFields.js";

/**
 * Map lifecycle, layer drawing, locate, and UI state for LeafletMap.
 *
 * @param {import('vue').ToRefs<Record<string, unknown>> | Record<string, unknown>} props
 * @param {(event: string, ...args: unknown[]) => void} emit
 */
export function useLeafletMap(props, emit) {
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

  const featureCount = computed(() => props.geojson?.features?.length || 0);
  const isRealtimeLocating = computed(() => locateWatchId.value !== null);
  const locateButtonLabel = computed(() =>
    isRealtimeLocating.value ? "重新居中到当前位置" : "开启实时定位",
  );
  const whiteMothSiteAddButtonLabel = computed(() =>
    props.whiteMothSiteAddMode ? `取消${props.siteAddLabel}` : props.siteAddLabel,
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
          label: `${view?.label || name}`.trim(),
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
  const usesSeverityLegend = computed(() => computeUsesSeverityLegend(props.popupFields));
  const usesParcelStatusLegend = computed(() =>
    computeUsesParcelStatusLegend(props.popupFields),
  );
  const usesSurveyCompletionMarkers = computed(() =>
    computeUsesSurveyCompletionMarkers(props.popupFields),
  );

  const legendEntries = computed(() => getLegendEntries(props.popupFields));

  function updateWhiteMothSiteDraftMarker(location = props.whiteMothSiteDraftLocation) {
    if (!mapRef.value) {
      return;
    }

    clearLayer(whiteMothSiteDraftMarkerRef);
    if (
      !location ||
      !Number.isFinite(Number(location.latitude)) ||
      !Number.isFinite(Number(location.longitude))
    ) {
      return;
    }

    whiteMothSiteDraftMarkerRef.value = buildDraftSiteMarker(location).addTo(mapRef.value);
  }

  function drawBasemap(mode = "standard") {
    if (!mapRef.value) {
      return;
    }

    const config = getBasemapConfig(mode);
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
    for (const feature of getTopmostPointFeatures(data.features, props.popupFields)) {
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
      features: getPointRenderFeatures(data.features, props.popupFields),
    };

    pointLayerRef.value = L.geoJSON(sortedData, {
      style: (feature) =>
        feature?.geometry?.type === "Point"
          ? {}
          : resolveFeaturePathStyle(feature?.properties || {}, props.popupFields),
      pointToLayer: (feature, latlng) => {
        const pointStyle = resolvePointStyle(feature.properties, props.popupFields);
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
    locateMarkerRef.value = buildLocateMarker(latlng).addTo(mapRef.value);
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
      bbox: [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()],
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

  return {
    mapElement,
    showLayerMenu,
    showLegend,
    isRealtimeLocating,
    isLocatePending,
    locateButtonLabel,
    whiteMothSiteAddButtonLabel,
    pointLayerEntries,
    referenceLayerEntries,
    legendEntries,
    locateToUser,
    toggleLayerMenu,
    selectBasemapMode,
    selectPointLayer,
    togglePointLabels,
    toggleReferenceLayer,
    zoomInMap,
    zoomOutMap,
  };
}
