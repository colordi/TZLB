<script setup>
import { computed, ref } from "vue";

import MapDetailDrawer from "../../components/design/map/MapDetailDrawer.vue";
import MapFilterCard from "../../components/design/map/MapFilterCard.vue";
import MapLayerPanel from "../../components/design/map/MapLayerPanel.vue";
import MapMockCanvas from "../../components/design/map/MapMockCanvas.vue";
import MapToolStack from "../../components/design/map/MapToolStack.vue";
import MobileMapBar from "../../components/design/map/MobileMapBar.vue";
import {
  DESIGN_MAP_BASE_LAYERS,
  DESIGN_MAP_POINT_DETAILS,
  DESIGN_MAP_POINT_LAYERS,
} from "../../fixtures/design/mapWorkspace.js";
import "../../styles/design-map.css";

const activeStatus = ref("all");
const layersOpen = ref(false);
const activeMobileAction = ref("points");
const selectedPointId = ref("p1");
const detailOpen = ref(true);
const actionNote = ref("静态点位详情已加载，当前显示香山公园东门林带。");
const enabledLayers = ref(
  DESIGN_MAP_BASE_LAYERS.filter((layer) => layer.enabled).map((layer) => layer.key),
);
const activePointLayers = ref(DESIGN_MAP_POINT_LAYERS.slice(0, 1).map((layer) => layer.key));
const activePoint = computed(() => DESIGN_MAP_POINT_DETAILS[selectedPointId.value]);

function toggleBaseLayer(key) {
  enabledLayers.value = enabledLayers.value.includes(key)
    ? enabledLayers.value.filter((layerKey) => layerKey !== key)
    : [...enabledLayers.value, key];
}

function togglePointLayer(key) {
  activePointLayers.value = activePointLayers.value.includes(key)
    ? activePointLayers.value.filter((layerKey) => layerKey !== key)
    : [...activePointLayers.value, key];
}

function setStatusFilter(key) {
  activeStatus.value = key;
  actionNote.value =
    key === "all" ? "已显示全部点位。" : "状态筛选仅改变静态代表点位的可见状态。";
}

function selectPoint(pointId) {
  const point = DESIGN_MAP_POINT_DETAILS[pointId];
  if (!point) {
    return;
  }
  selectedPointId.value = pointId;
  detailOpen.value = true;
  activeMobileAction.value = "points";
  actionNote.value = `已打开点位详情：${point.title}。`;
}

function handleToolAction(action) {
  const notes = {
    locate: "已定位到当前负责区域：海淀区。",
    zoomIn: "地图已放大一级，静态聚合保持展示。",
    zoomOut: "地图已缩小一级，静态聚合保持展示。",
  };
  actionNote.value = notes[action];
}

function handleMobileAction(action) {
  activeMobileAction.value = action;
  if (action === "layers") {
    layersOpen.value = !layersOpen.value;
  }
  if (action === "filter") {
    actionNote.value = "可使用左上角筛选卡切换点位状态。";
  }
  if (action === "menu") {
    actionNote.value = "菜单仍由设计预览共享壳层控制。";
  }
  if (action === "points") {
    selectPoint(selectedPointId.value || "p1");
  }
}
</script>

<template>
  <main class="design-map-page">
    <MapMockCanvas
      :active-status="activeStatus"
      :enabled-layers="enabledLayers"
      :selected-point-id="selectedPointId"
      @select-point="selectPoint"
    />

    <MapFilterCard :active-status="activeStatus" @update:active-status="setStatusFilter" />

    <MapToolStack
      :layers-open="layersOpen"
      @toggle-layers="layersOpen = !layersOpen"
      @locate="handleToolAction('locate')"
      @zoom-in="handleToolAction('zoomIn')"
      @zoom-out="handleToolAction('zoomOut')"
    />

    <MapLayerPanel
      :open="layersOpen"
      :enabled-layers="enabledLayers"
      :active-point-layers="activePointLayers"
      @toggle-base-layer="toggleBaseLayer"
      @toggle-point-layer="togglePointLayer"
    />

    <MapDetailDrawer
      :point="activePoint"
      :open="detailOpen"
      @close="detailOpen = false"
    />

    <div class="design-map-stage-note" role="status" data-testid="design-map-stage-note">
      <span class="design-map-stage-dot"></span>
      <span>{{ actionNote }}</span>
    </div>

    <MobileMapBar :active-action="activeMobileAction" @select="handleMobileAction" />
  </main>
</template>
