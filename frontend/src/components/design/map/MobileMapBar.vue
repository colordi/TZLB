<script setup>
import { DESIGN_MAP_MOBILE_ACTIONS } from "../../../fixtures/design/mapWorkspace.js";

defineProps({
  activeAction: {
    type: String,
    default: "points",
  },
});

defineEmits(["select"]);
</script>

<template>
  <nav class="design-map-mobile-bar" aria-label="移动端地图操作">
    <button
      v-for="action in DESIGN_MAP_MOBILE_ACTIONS"
      :key="action.key"
      type="button"
      :class="{ 'is-active': activeAction === action.key }"
      :data-testid="`design-map-mobile-${action.key}`"
      @click="$emit('select', action.key)"
    >
      <svg
        v-if="action.key === 'menu'"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
      >
        <path d="M4 7h16M4 12h16M4 17h16" />
      </svg>
      <svg
        v-else-if="action.key === 'filter'"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.7"
      >
        <path d="M4 6h16M7 12h10m-7 6h4" />
      </svg>
      <svg
        v-else-if="action.key === 'layers'"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.7"
      >
        <path d="m12 3 9 5-9 5-9-5Zm-9 9 9 5 9-5" />
      </svg>
      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
        <path d="M12 21s6-5.1 6-11a6 6 0 1 0-12 0c0 5.9 6 11 6 11Z" />
        <circle cx="12" cy="10" r="2" />
      </svg>
      <span>{{ action.label }}</span>
    </button>
  </nav>
</template>
