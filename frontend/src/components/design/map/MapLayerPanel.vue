<script setup>
import {
  DESIGN_MAP_BASE_LAYERS,
  DESIGN_MAP_POINT_LAYERS,
} from "../../../fixtures/design/mapWorkspace.js";

defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  enabledLayers: {
    type: Array,
    required: true,
  },
  activePointLayers: {
    type: Array,
    required: true,
  },
});

defineEmits(["toggle-base-layer", "toggle-point-layer"]);
</script>

<template>
  <aside class="design-map-layer-panel" :class="{ 'is-open': open }" aria-label="地图图层">
    <h2>地图图层</h2>
    <section class="design-map-layer-group">
      <h3>基础图层</h3>
      <label v-for="layer in DESIGN_MAP_BASE_LAYERS" :key="layer.key">
        <input
          type="checkbox"
          :checked="enabledLayers.includes(layer.key)"
          @change="$emit('toggle-base-layer', layer.key)"
        />
        {{ layer.label }}
      </label>
    </section>

    <section class="design-map-layer-group">
      <h3>点位图层</h3>
      <button
        v-for="layer in DESIGN_MAP_POINT_LAYERS"
        :key="layer.key"
        type="button"
        class="design-map-point-layer"
        :class="{ 'is-active': activePointLayers.includes(layer.key) }"
        :data-testid="`design-map-point-layer-${layer.key}`"
        @click="$emit('toggle-point-layer', layer.key)"
      >
        <span class="design-map-point-layer-dot" :style="{ background: layer.color }"></span>
        <span>{{ layer.label }}</span>
        <span class="design-num">{{ layer.count }}</span>
      </button>
    </section>
  </aside>
</template>
