<script setup>
import {
  DESIGN_MAP_CLUSTERS,
  DESIGN_MAP_DISTRICTS,
  DESIGN_MAP_MARKERS,
} from "../../../fixtures/design/mapWorkspace.js";

const props = defineProps({
  activeStatus: {
    type: String,
    default: "all",
  },
  enabledLayers: {
    type: Array,
    required: true,
  },
  selectedPointId: {
    type: String,
    default: "",
  },
});

defineEmits(["select-point"]);

function isHidden(status) {
  return props.activeStatus !== "all" && props.activeStatus !== status;
}
</script>

<template>
  <div
    class="design-map-canvas"
    :class="{
      'hide-grid': !enabledLayers.includes('grid'),
      'hide-roads': !enabledLayers.includes('roads'),
      'hide-water': !enabledLayers.includes('water'),
      'hide-points': !enabledLayers.includes('points'),
      'show-heat': enabledLayers.includes('risk'),
    }"
    aria-label="静态模拟地图画布"
  >
    <span
      v-for="district in DESIGN_MAP_DISTRICTS"
      :key="district.key"
      class="design-map-district"
      :class="`is-${district.key}`"
    >
      {{ district.label }}
    </span>

    <button
      v-for="marker in DESIGN_MAP_MARKERS"
      :key="marker.key"
      type="button"
      class="design-map-marker"
      :class="[
        `is-${marker.key}`,
        `is-${marker.status}`,
        { 'is-hidden': isHidden(marker.status), 'is-selected': selectedPointId === marker.pointId },
      ]"
      :aria-label="marker.label"
      :data-testid="`design-map-point-${marker.pointId}`"
      @click="$emit('select-point', marker.pointId)"
    ></button>

    <button
      v-for="cluster in DESIGN_MAP_CLUSTERS"
      :key="cluster.key"
      type="button"
      class="design-map-cluster design-num"
      :class="[
        `is-${cluster.key}`,
        `is-${cluster.status}`,
        { 'is-hidden': isHidden(cluster.status), 'is-selected': selectedPointId === cluster.pointId },
      ]"
      :aria-label="cluster.label"
      :data-testid="`design-map-point-${cluster.pointId}`"
      @click="$emit('select-point', cluster.pointId)"
    >
      {{ cluster.count }}
    </button>
  </div>
</template>
