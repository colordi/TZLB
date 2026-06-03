<script setup>
import { computed, ref, watch } from "vue";
import { ChevronDown, Filter, Layers, X } from "@lucide/vue";

const props = defineProps({
  views: { type: Array, default: () => [] },
  viewName: { type: String, default: "" },
  loadingViews: { type: Boolean, default: false },
  filterFields: { type: Array, default: () => [] },
  activeFilters: { type: Object, default: () => ({}) },
  filterOptions: { type: Object, default: () => ({}) },
  basemapMode: { type: String, default: "satellite" },
  showPointLabels: { type: Boolean, default: true },
  loading: { type: Boolean, default: false },
});

const emit = defineEmits([
  "update:viewName",
  "update:basemapMode",
  "update:showPointLabels",
  "apply-filters",
  "reset-filters",
  "update:activeFilters",
]);

const isFilterPanelOpen = ref(false);
const showLayerMenu = ref(false);
const openFilterMenus = ref({});

const hasFilterFields = computed(() => props.filterFields.length > 0);

const filterHint = computed(() => {
  if (hasFilterFields.value) {
    return "按当前视图筛选点位。";
  }
  return "当前视图暂无可用筛选。";
});

const activeFilterCount = computed(() => {
  return Object.values(props.activeFilters).reduce((count, values) => {
    const arr = Array.isArray(values) ? values : [values];
    return count + arr.filter((v) => v !== "" && v != null).length;
  }, 0);
});

function isFilterMenuOpen(key) {
  return openFilterMenus.value[key] === true;
}

function toggleFilterMenu(key) {
  openFilterMenus.value = { [key]: !openFilterMenus.value[key] };
}

function isFilterSummaryMuted(field) {
  const values = props.activeFilters[field.key];
  return !values || (Array.isArray(values) && values.length === 0);
}

function getFilterSummary(field) {
  const values = props.activeFilters[field.key];
  if (!values || (Array.isArray(values) && values.length === 0)) {
    return "全部";
  }
  if (Array.isArray(values)) {
    return `已选 ${values.length} 项`;
  }
  return values;
}

function hasSelectedFilterValues(key) {
  const values = props.activeFilters[key];
  return values && (Array.isArray(values) ? values.length > 0 : values !== "");
}

function onFilterChange(key, optionValues) {
  const newFilters = { ...props.activeFilters };
  newFilters[key] = optionValues;
  emit("update:activeFilters", newFilters);
}

function applyFilter() {
  emit("apply-filters");
  isFilterPanelOpen.value = false;
}

function resetFilter() {
  emit("reset-filters");
}

function closeLayerMenu() {
  showLayerMenu.value = false;
}

watch(isFilterPanelOpen, (isOpen) => {
  if (!isOpen) {
    openFilterMenus.value = {};
  }
});
</script>

<template>
  <div class="map-toolbar">
    <div class="toolbar-row">
      <div class="toolbar-view-select">
        <select
          class="view-select"
          :value="viewName"
          :disabled="loadingViews || !views.length"
          @change="emit('update:viewName', $event.target.value)"
        >
          <option v-if="!views.length" value="">暂无可用视图</option>
          <option v-for="view in views" :key="view.name" :value="view.name">
            {{ view.name }}
          </option>
        </select>
      </div>

      <button
        v-if="hasFilterFields"
        type="button"
        class="toolbar-btn"
        :class="{ 'is-active': isFilterPanelOpen, 'has-badge': activeFilterCount > 0 }"
        aria-label="筛选配置"
        aria-controls="map-filter-panel"
        :aria-expanded="isFilterPanelOpen"
        @click="isFilterPanelOpen = !isFilterPanelOpen"
      >
        <Filter :size="18" :stroke-width="2" />
        <span class="toolbar-btn-label">筛选</span>
        <span v-if="activeFilterCount > 0" class="filter-badge">{{ activeFilterCount }}</span>
      </button>

      <div class="toolbar-layer-control">
        <button
          type="button"
          class="toolbar-btn"
          :class="{ 'is-active': showLayerMenu }"
          aria-label="切换图层"
          aria-controls="map-layer-menu"
          :aria-expanded="showLayerMenu"
          @click="showLayerMenu = !showLayerMenu"
        >
          <Layers :size="18" :stroke-width="2" />
          <span class="toolbar-btn-label">图层</span>
        </button>

        <transition name="toolbar-menu-fade">
          <div v-show="showLayerMenu" class="layer-menu-popup" @click.stop>
            <button
              type="button"
              class="layer-menu-item"
              :class="{ 'is-active': basemapMode === 'standard' }"
              @click="emit('update:basemapMode', 'standard'); closeLayerMenu()"
            >
              <strong>标准地图</strong>
              <span>包含政区街道</span>
            </button>
            <button
              type="button"
              class="layer-menu-item"
              :class="{ 'is-active': basemapMode === 'satellite' }"
              @click="emit('update:basemapMode', 'satellite'); closeLayerMenu()"
            >
              <strong>卫星地图</strong>
              <span>高分辨率影像</span>
            </button>
            <button
              type="button"
              class="layer-menu-item"
              :class="{ 'is-active': showPointLabels }"
              :aria-pressed="showPointLabels"
              data-testid="point-label-toggle"
              @click="emit('update:showPointLabels', !showPointLabels)"
            >
              <strong>显示编号</strong>
              <span>{{ showPointLabels ? "当前已开启" : "当前已关闭" }}</span>
            </button>
          </div>
        </transition>
      </div>
    </div>

    <transition name="toolbar-panel-slide">
      <div
        v-if="isFilterPanelOpen"
        class="toolbar-filter-backdrop"
        @click="isFilterPanelOpen = false"
      ></div>
    </transition>

    <transition name="toolbar-panel-slide">
      <div
        v-if="isFilterPanelOpen"
        id="map-filter-panel"
        class="toolbar-filter-panel"
      >
        <div class="filter-panel-content">
          <div v-if="hasFilterFields" class="filter-fields">
            <div
              v-for="field in filterFields"
              :key="field.key"
              class="filter-field-item"
              :class="{ 'is-open': isFilterMenuOpen(field.key) }"
            >
              <button
                type="button"
                class="filter-field-trigger"
                :class="{ 'is-open': isFilterMenuOpen(field.key) }"
                :data-testid="`map-filter-trigger-${field.key}`"
                :aria-expanded="isFilterMenuOpen(field.key)"
                :aria-controls="`map-filter-menu-${field.key}`"
                :disabled="loading || field.options.length === 0"
                @click="toggleFilterMenu(field.key)"
              >
                <span class="filter-field-copy">
                  <span class="filter-field-label">{{ field.label }}</span>
                  <span
                    class="filter-field-summary"
                    :class="{ 'is-muted': isFilterSummaryMuted(field) }"
                  >
                    {{ getFilterSummary(field) }}
                  </span>
                </span>
                <span class="filter-field-meta">
                  <span v-if="hasSelectedFilterValues(field.key)" class="filter-field-count" aria-hidden="true">
                    {{ activeFilters[field.key]?.length || 0 }}
                  </span>
                  <ChevronDown :size="14" :stroke-width="2" class="filter-field-chevron" />
                </span>
              </button>

              <div
                v-if="isFilterMenuOpen(field.key)"
                :id="`map-filter-menu-${field.key}`"
                class="filter-option-dropdown"
                :data-testid="`map-filter-${field.key}`"
                role="group"
                :aria-label="field.label"
                :aria-disabled="loading || field.options.length === 0"
              >
                <label
                  v-for="option in field.options"
                  :key="option.value"
                  class="filter-option"
                  :class="{ 'is-disabled': loading }"
                >
                  <input
                    type="checkbox"
                    :value="option.value"
                    :checked="activeFilters[field.key]?.includes(option.value)"
                    :data-testid="`map-filter-${field.key}-${option.value}`"
                    :disabled="loading"
                    @change="onFilterChange(field.key, option.value)"
                  />
                  <span>{{ option.label }}</span>
                </label>
              </div>
            </div>
          </div>

          <div v-else class="filter-empty-state">
            当前视图暂无筛选字段
          </div>

          <div class="filter-actions">
            <button type="button" class="filter-apply-btn" :disabled="loading || !viewName" @click="applyFilter">
              应用筛选
            </button>
            <button type="button" class="filter-reset-btn" :disabled="loading" @click="resetFilter">
              清空
            </button>
          </div>

          <p class="filter-hint">{{ filterHint }}</p>
        </div>
      </div>
    </transition>

    <div v-if="loading" class="toolbar-loading">正在刷新点位数据…</div>
  </div>
</template>

<style scoped>
.map-toolbar {
  position: absolute;
  top: 1.25rem;
  left: 1.25rem;
  z-index: 1200;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  pointer-events: auto;
}

.toolbar-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: var(--color-surface);
  backdrop-filter: blur(24px);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  box-shadow: var(--elev-ring);
}

.toolbar-view-select {
  position: relative;
}

.view-select {
  appearance: none;
  min-width: 10rem;
  padding: 0.625rem 2rem 0.625rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-ink);
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23796f91' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.5rem center;
}

.view-select:hover {
  border-color: var(--color-line-strong);
  background-color: var(--color-surface);
}

.view-select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: var(--focus-ring);
}

.view-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toolbar-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 2.75rem;
  height: 2.75rem;
  padding: 0 0.5rem;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-ink-soft);
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
  gap: 0.35rem;
}

.toolbar-btn:hover {
  background: var(--color-surface-container);
  color: var(--color-accent);
}

.toolbar-btn.is-active {
  background: var(--color-accent);
  color: var(--color-accent-on);
  border-color: var(--color-accent);
}

.filter-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 1rem;
  height: 1rem;
  padding: 0 4px;
  border-radius: var(--radius-pill);
  background: var(--color-danger);
  color: var(--color-surface);
  font-size: 0.625rem;
  font-weight: 700;
  line-height: 1rem;
  text-align: center;
}

.toolbar-layer-control {
  position: relative;
}

.layer-menu-popup {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  min-width: 14rem;
  padding: 0.5rem;
  background: var(--color-surface);
  backdrop-filter: blur(24px);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  box-shadow: var(--elev-raised);
  transform-origin: top right;
}

.layer-menu-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  width: 100%;
  padding: 0.6rem 0.75rem;
  border: 2px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
}

.layer-menu-item:hover {
  background: var(--color-surface-container-low);
}

.layer-menu-item.is-active {
  border-color: var(--color-accent);
  background: var(--color-surface-container-low);
}

.layer-menu-item strong {
  color: var(--color-ink);
  font-size: 0.875rem;
  font-weight: 600;
}

.layer-menu-item span {
  color: var(--color-muted);
  font-size: 0.75rem;
}

.toolbar-filter-backdrop {
  display: none;
}

.toolbar-filter-panel {
  background: var(--color-surface);
  backdrop-filter: blur(24px);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  box-shadow: var(--elev-raised);
  overflow: hidden;
}

.filter-panel-content {
  padding: 1rem;
  max-height: 60vh;
  overflow-y: auto;
}

.filter-fields {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-field-item {
  position: relative;
}

.filter-field-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
}

.filter-field-trigger:hover {
  border-color: var(--color-line-strong);
  background: var(--color-surface);
}

.filter-field-trigger.is-open {
  border-color: var(--color-accent);
  background: var(--color-surface);
}

.filter-field-copy {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.1rem;
  min-width: 0;
}

.filter-field-label {
  color: var(--color-ink);
  font-size: 0.8125rem;
  font-weight: 600;
}

.filter-field-summary {
  color: var(--color-accent);
  font-size: 0.75rem;
  font-weight: 500;
}

.filter-field-summary.is-muted {
  color: var(--color-muted);
}

.filter-field-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-field-count {
  min-width: 1.25rem;
  height: 1.25rem;
  padding: 0 4px;
  border-radius: var(--radius-pill);
  background: var(--color-accent);
  color: var(--color-accent-on);
  font-size: 0.6875rem;
  font-weight: 700;
  line-height: 1.25rem;
  text-align: center;
}

.filter-field-chevron {
  color: var(--color-muted);
  transition: transform 150ms ease;
}

.filter-field-item.is-open .filter-field-chevron {
  transform: rotate(180deg);
}

.filter-option-dropdown {
  position: absolute;
  top: calc(100% + 0.35rem);
  left: 0;
  right: 0;
  padding: 0.5rem;
  background: var(--color-surface);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  box-shadow: var(--elev-raised);
  z-index: 10;
  max-height: 12rem;
  overflow-y: auto;
}

.filter-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.6rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--motion-fast) var(--ease-standard);
  font-size: 0.8125rem;
  color: var(--color-ink);
}

.filter-option:hover {
  background: var(--color-surface-container-low);
}

.filter-option.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.filter-option input[type="checkbox"] {
  width: 1rem;
  height: 1rem;
  accent-color: var(--color-accent);
  cursor: inherit;
}

.filter-empty-state {
  padding: 2rem 1rem;
  text-align: center;
  color: var(--color-muted);
  font-size: 0.875rem;
}

.filter-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}

.filter-apply-btn {
  flex: 1;
  padding: 0.6rem 1rem;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--color-accent);
  color: var(--color-accent-on);
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
}

.filter-apply-btn:hover:not(:disabled) {
  background: var(--color-accent-hover);
  transform: translateY(-1px);
  box-shadow: var(--elev-raised);
}

.filter-apply-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.filter-reset-btn {
  padding: 0.6rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-ink-soft);
  font-weight: 500;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
}

.filter-reset-btn:hover:not(:disabled) {
  background: var(--color-surface-container-low);
  border-color: var(--color-line-strong);
}

.filter-reset-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.filter-hint {
  margin-top: 0.75rem;
  color: var(--color-muted);
  font-size: 0.75rem;
  text-align: center;
}

.toolbar-loading {
  padding: 0.5rem 1rem;
  background: var(--color-surface);
  backdrop-filter: blur(24px);
  border-radius: var(--radius-sm);
  color: var(--color-accent);
  font-size: 0.8125rem;
  font-weight: 500;
  text-align: center;
}

.toolbar-menu-fade-enter-active,
.toolbar-menu-fade-leave-active {
  transition: all 150ms ease;
}

.toolbar-menu-fade-enter-from,
.toolbar-menu-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

.toolbar-panel-slide-enter-active,
.toolbar-panel-slide-leave-active {
  transition: all 180ms ease;
}

.toolbar-panel-slide-enter-from,
.toolbar-panel-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 760px) {
  .map-toolbar {
    top: 0.75rem;
    left: 0.75rem;
    right: 0.75rem;
  }

  .toolbar-row {
    flex-wrap: wrap;
    padding: 0.4rem;
    gap: 0.35rem;
  }

  .view-select {
    min-width: 0;
    flex: 1;
    padding: 0.5rem 1.75rem 0.5rem 0.625rem;
    font-size: 0.8125rem;
  }

  .toolbar-btn {
    min-width: 2.5rem;
    height: 2.5rem;
    padding: 0 0.4rem;
  }

  .toolbar-btn-label {
    display: none;
  }

  .toolbar-filter-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(29, 24, 54, 0.3);
    backdrop-filter: blur(4px);
    z-index: 1299;
  }

  .toolbar-filter-panel {
    position: fixed;
    top: auto;
    left: 0;
    right: 0;
    bottom: 0;
    max-width: 100%;
    border-radius: 16px 16px 0 0;
    max-height: 70vh;
    z-index: 1300;
  }

  .filter-panel-content {
    padding: 1.25rem;
    padding-bottom: calc(1.25rem + env(safe-area-inset-bottom));
    max-height: calc(70vh - 2.5rem);
  }

  .filter-option-dropdown {
    position: fixed;
    left: 0.75rem;
    right: 0.75rem;
    top: auto;
    max-height: 50vh;
  }

  .layer-menu-popup {
    right: 0;
    min-width: 12rem;
  }

  .filter-actions {
    flex-direction: column;
  }

  .filter-apply-btn,
  .filter-reset-btn {
    width: 100%;
    text-align: center;
    padding: 0.75rem;
  }
}

@media (max-width: 480px) {
  .map-toolbar {
    top: 0.5rem;
    left: 0.5rem;
    right: 0.5rem;
  }

  .toolbar-row {
    padding: 0.3rem;
    gap: 0.25rem;
  }

  .view-select {
    font-size: 0.75rem;
    padding: 0.45rem 1.5rem 0.45rem 0.5rem;
  }

  .toolbar-btn {
    min-width: 2.25rem;
    height: 2.25rem;
    padding: 0 0.3rem;
  }

  .toolbar-btn :deep(svg) {
    width: 16px;
    height: 16px;
  }
}
</style>
