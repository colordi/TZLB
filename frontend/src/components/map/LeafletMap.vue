<script setup>
import { Layers, List, LocateFixed, MapPinPlus, Minus, Plus } from "@lucide/vue";
import "leaflet/dist/leaflet.css";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { useLeafletMap } from "./useLeafletMap.js";

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
  siteAddLabel: {
    type: String,
    default: "",
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

const {
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
} = useLeafletMap(props, emit);

defineExpose({
  locateToUser,
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

      <div
        v-if="siteAddLabel"
        class="map-tool-group rounded-xl border bg-card/95 shadow-md backdrop-blur"
      >
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="map-tool-btn"
          :class="{ 'is-active': whiteMothSiteAddMode, 'is-loading': whiteMothSiteSaving }"
          data-testid="map-add-site-button"
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

<style scoped src="./leaflet-map.css"></style>
