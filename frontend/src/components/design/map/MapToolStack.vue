<script setup>
defineProps({
  layersOpen: {
    type: Boolean,
    required: true,
  },
});

defineEmits(["toggle-layers", "locate", "zoom-in", "zoom-out"]);
</script>

<template>
  <div class="design-map-tool-stack" aria-label="地图工具">
    <div class="design-map-tool-group">
      <button
        class="design-icon-button"
        type="button"
        aria-label="图层控制"
        data-testid="design-map-layer-button"
        :aria-pressed="layersOpen"
        @click="$emit('toggle-layers')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
          <path d="m12 3 9 5-9 5-9-5Zm-9 9 9 5 9-5m-18 4 9 5 9-5" />
        </svg>
      </button>
      <button
        class="design-icon-button"
        type="button"
        aria-label="定位当前区域"
        @click="$emit('locate')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
          <circle cx="12" cy="12" r="3" />
          <circle cx="12" cy="12" r="8" />
          <path d="M12 2v2m0 16v2M2 12h2m16 0h2" />
        </svg>
      </button>
    </div>
    <div class="design-map-tool-group">
      <button class="design-icon-button" type="button" aria-label="放大地图" @click="$emit('zoom-in')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>
      <button class="design-icon-button" type="button" aria-label="缩小地图" @click="$emit('zoom-out')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M5 12h14" />
        </svg>
      </button>
    </div>
  </div>
</template>
