<script setup>
import { ref } from "vue";

import { DESIGN_MAP_STATUS_FILTERS } from "../../../fixtures/design/mapWorkspace.js";

defineProps({
  activeStatus: {
    type: String,
    required: true,
  },
});

const emit = defineEmits(["update:active-status"]);

const collapsed = ref(false);
const searchQuery = ref("");
</script>

<template>
  <section class="design-map-filter-card" :class="{ 'is-collapsed': collapsed }">
    <header class="design-map-filter-head">
      <label class="design-map-search">
        <span class="design-map-sr-only">搜索点位、工单编号或区县</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
          <circle cx="11" cy="11" r="6" />
          <path d="m16 16 4 4" />
        </svg>
        <input
          v-model="searchQuery"
          placeholder="搜索点位、工单编号或区县"
          data-testid="design-map-search"
        />
      </label>
      <button
        class="design-icon-button design-map-filter-toggle"
        type="button"
        :aria-label="collapsed ? '展开筛选面板' : '收起筛选面板'"
        data-testid="design-map-filter-toggle"
        @click="collapsed = !collapsed"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          :class="{ 'is-rotated': collapsed }"
        >
          <path d="m18 15-6-6-6 6" />
        </svg>
      </button>
    </header>

    <div v-if="!collapsed" class="design-map-filter-body">
      <div class="design-map-filter-caption">
        <span>点位状态</span>
        <span class="design-num">127 个点位</span>
      </div>
      <div class="design-map-status-list">
        <button
          v-for="filter in DESIGN_MAP_STATUS_FILTERS"
          :key="filter.key"
          type="button"
          class="design-map-status-filter"
          :class="{ 'is-active': activeStatus === filter.key }"
          :data-testid="`design-map-status-${filter.key}`"
          @click="emit('update:active-status', filter.key)"
        >
          <span class="design-map-legend-dot" :class="`is-${filter.tone}`"></span>
          <span>{{ filter.label }}</span>
          <span class="design-num">{{ filter.count }}</span>
        </button>
      </div>
    </div>
  </section>
</template>
