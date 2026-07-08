<script setup>
import { computed, onMounted, ref } from "vue";
import { RefreshCw, Save, Eye, EyeOff, GripVertical } from "@lucide/vue";

import { fetchLayers, updateLayers } from "../api/admin.js";
import { fetchMapFilterOptions } from "../api/map.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";

const { error, info } = useToast();
const loading = ref(false);
const saving = ref(false);
const viewLayers = ref([]);
const referenceLayers = ref([]);
const editCache = ref({});
const hasChanges = ref(false);
const filterOptionsByLayerKey = ref({});

const dragKey = ref(null);
const dragType = ref(null);
const dragOverKey = ref(null);
const dragOverPos = ref(null);

const layerTypeLabel = {
  view: "点位图层",
  reference: "参考图层",
};

const EXCLUDED_FILTER_KEYS = new Set(["属地", "调查状态"]);

const totalCount = computed(
  () => viewLayers.value.length + referenceLayers.value.length
);

function listFor(typeKey) {
  return typeKey === "view" ? viewLayers.value : referenceLayers.value;
}

function buildCache(data) {
  const cache = {};
  for (const layer of data) {
    cache[layer.id] = {
      display_name: layer.display_name || "",
      sort_order: layer.sort_order,
      default_visible: layer.default_visible,
      is_enabled: layer.is_enabled,
      default_filters: { ...(layer.default_filters || {}) },
    };
  }
  return cache;
}

async function loadFilterOptionsForViews(layers) {
  const enabledViewLayers = layers.filter(
    (l) => l.layer_type === "view" && l.is_enabled,
  );
  const results = await Promise.allSettled(
    enabledViewLayers.map((layer) => fetchMapFilterOptions(layer.layer_key)),
  );
  const optionsMap = {};
  enabledViewLayers.forEach((layer, idx) => {
    const result = results[idx];
    if (result.status === "fulfilled" && result.value) {
      optionsMap[layer.layer_key] = result.value;
    }
  });
  filterOptionsByLayerKey.value = optionsMap;
}

async function load() {
  if (loading.value) return;
  loading.value = true;
  try {
    const data = await fetchLayers();
    viewLayers.value = data.filter((l) => l.layer_type === "view");
    referenceLayers.value = data.filter((l) => l.layer_type === "reference");
    editCache.value = buildCache(data);
    hasChanges.value = false;
    await loadFilterOptionsForViews(data);
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`加载图层元数据失败：${err.message || err}`, "加载失败");
  } finally {
    loading.value = false;
  }
}

function getEdit(layer) {
  return editCache.value[layer.id] || {};
}

function markChanged() {
  hasChanges.value = true;
}

function configurableFieldsFor(layer) {
  const options = filterOptionsByLayerKey.value[layer.layer_key];
  if (!options) return [];
  return (options.filter_fields || []).filter(
    (field) => !EXCLUDED_FILTER_KEYS.has(field.key),
  );
}

function getFilterValue(layer, fieldKey) {
  return getEdit(layer).default_filters?.[fieldKey] || "";
}

function isStaleFilterValue(layer, field) {
  const value = getFilterValue(layer, field.key);
  if (!value) return false;
  return !field.options.some((option) => option.value === value);
}

function setFilterValue(layer, fieldKey, value) {
  const edit = getEdit(layer);
  const filters = { ...(edit.default_filters || {}) };
  if (value) {
    filters[fieldKey] = value;
  } else {
    delete filters[fieldKey];
  }
  edit.default_filters = filters;
  markChanged();
}

function toggleEnabled(layer) {
  const edit = getEdit(layer);
  edit.is_enabled = !edit.is_enabled;
  markChanged();
}

function toggleDefaultVisible(layer) {
  const edit = getEdit(layer);
  edit.default_visible = !edit.default_visible;
  markChanged();
}

/* ── 拖拽排序（组内，不跨 layer_type） ── */
function onDragStart(e, layer, typeKey) {
  dragKey.value = layer.layer_key;
  dragType.value = typeKey;
  e.dataTransfer.effectAllowed = "move";
  e.dataTransfer.setData("text/plain", layer.layer_key);
}

function onDragOver(e, layer, typeKey) {
  if (dragType.value !== typeKey) return;
  e.preventDefault();
  e.dataTransfer.dropEffect = "move";
  if (!dragKey.value || dragKey.value === layer.layer_key) {
    dragOverKey.value = null;
    dragOverPos.value = null;
    return;
  }
  const rect = e.currentTarget.getBoundingClientRect();
  const offset = e.clientX - rect.left;
  dragOverKey.value = layer.layer_key;
  dragOverPos.value = offset < rect.width / 2 ? "before" : "after";
}

function onDrop(e, targetLayer, typeKey) {
  e.preventDefault();
  if (!dragKey.value || dragType.value !== typeKey) {
    resetDrag();
    return;
  }
  const list = listFor(typeKey);
  const fromIdx = list.findIndex((l) => l.layer_key === dragKey.value);
  if (fromIdx === -1) {
    resetDrag();
    return;
  }
  const toIdx = list.findIndex((l) => l.layer_key === targetLayer.layer_key);
  if (toIdx === -1) {
    resetDrag();
    return;
  }
  const insertAfter = dragOverPos.value === "after";
  let target = insertAfter ? toIdx + 1 : toIdx;
  const [moved] = list.splice(fromIdx, 1);
  if (fromIdx < target) target -= 1;
  list.splice(target, 0, moved);
  reindex(list);
  markChanged();
  resetDrag();
}

function onDragEnd() {
  resetDrag();
}

function resetDrag() {
  dragKey.value = null;
  dragType.value = null;
  dragOverKey.value = null;
  dragOverPos.value = null;
}

function reindex(list) {
  list.forEach((layer, idx) => {
    layer.sort_order = idx;
    const edit = editCache.value[layer.id];
    if (edit) edit.sort_order = idx;
  });
}

async function handleSave() {
  saving.value = true;
  try {
    const items = [
      ...viewLayers.value,
      ...referenceLayers.value,
    ].map((layer) => {
      const edit = editCache.value[layer.id] || {};
      return {
        layer_key: layer.layer_key,
        layer_type: layer.layer_type,
        display_name: edit.display_name || null,
        sort_order: edit.sort_order ?? layer.sort_order,
        default_visible: edit.default_visible ?? layer.default_visible,
        is_enabled: edit.is_enabled ?? layer.is_enabled,
        default_filters: edit.default_filters || {},
      };
    });

    const updated = await updateLayers(items);
    viewLayers.value = updated.filter((l) => l.layer_type === "view");
    referenceLayers.value = updated.filter((l) => l.layer_type === "reference");
    editCache.value = buildCache(updated);
    hasChanges.value = false;
    info("图层元数据已更新", "保存成功");
  } catch (err) {
    error(`保存图层元数据失败：${err.message || err}`, "保存失败");
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  load();
});
</script>

<template>
  <div class="admin-page">
    <div class="page-header">
      <div class="page-header-copy">
        <h1 class="page-title">图层管理</h1>
        <p class="page-desc">拖拽调整图层显示顺序，编辑别名与启用状态，共 {{ totalCount }} 项</p>
      </div>
      <div class="page-actions">
        <button type="button" class="btn btn-secondary" :disabled="loading" @click="load">
          <RefreshCw :size="16" :stroke-width="2" :class="{ 'is-spinning': loading }" />
          <span>{{ loading ? "加载中" : "刷新" }}</span>
        </button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="!hasChanges || saving"
          @click="handleSave"
        >
          <Save :size="16" :stroke-width="2" />
          <span>{{ saving ? "保存中…" : "保存更改" }}</span>
        </button>
      </div>
    </div>

    <template v-for="(typeKey, typeIdx) in ['view', 'reference']" :key="typeKey">
      <div class="section-head" :class="{ 'section-head--first': typeIdx === 0 }">
        <h2 class="section-title">{{ layerTypeLabel[typeKey] }}</h2>
        <span class="section-count">{{ listFor(typeKey).length }}</span>
      </div>

      <div class="layer-grid">
        <div
          v-for="(layer, index) in listFor(typeKey)"
          :key="layer.id"
          class="layer-card"
          :class="{
            'is-disabled': !getEdit(layer).is_enabled,
            'is-dragging': dragKey === layer.layer_key,
            'is-drag-over-before':
              dragOverKey === layer.layer_key && dragOverPos === 'before',
            'is-drag-over-after':
              dragOverKey === layer.layer_key && dragOverPos === 'after',
          }"
          @dragover="onDragOver($event, layer, typeKey)"
          @drop="onDrop($event, layer, typeKey)"
          @dragend="onDragEnd"
        >
          <div class="layer-card-head">
            <div
              class="layer-handle"
              draggable="true"
              title="拖拽排序"
              @dragstart="onDragStart($event, layer, typeKey)"
            >
              <GripVertical :size="16" :stroke-width="2" />
            </div>
            <span class="layer-index">{{ index + 1 }}</span>
            <input
              v-model="getEdit(layer).display_name"
              class="name-input"
              draggable="false"
              :placeholder="layer.layer_key"
              @input="markChanged"
            />
          </div>

          <code class="layer-key">{{ layer.layer_key }}</code>

          <div class="layer-toggles">
            <button
              type="button"
              class="switch"
              draggable="false"
              :class="{ 'is-on': getEdit(layer).is_enabled }"
              :title="getEdit(layer).is_enabled ? '点击停用' : '点击启用'"
              @click="toggleEnabled(layer)"
            >
              <span class="switch-track"></span>
              <span class="switch-label">
                <Eye v-if="getEdit(layer).is_enabled" :size="13" :stroke-width="2" />
                <EyeOff v-else :size="13" :stroke-width="2" />
                {{ getEdit(layer).is_enabled ? "启用" : "停用" }}
              </span>
            </button>

            <button
              v-if="layer.layer_type === 'reference'"
              type="button"
              class="switch"
              draggable="false"
              :class="{ 'is-on': getEdit(layer).default_visible }"
              title="默认显隐"
              @click="toggleDefaultVisible(layer)"
            >
              <span class="switch-track"></span>
              <span class="switch-label">
                {{ getEdit(layer).default_visible ? "默认显示" : "默认隐藏" }}
              </span>
            </button>
          </div>

          <div
            v-if="layer.layer_type === 'view' && configurableFieldsFor(layer).length"
            class="layer-default-filters"
            data-testid="layer-default-filters"
          >
            <span class="layer-default-filters-label">默认筛选</span>
            <div class="layer-default-filters-fields">
              <label
                v-for="field in configurableFieldsFor(layer)"
                :key="field.key"
                class="layer-default-filter"
              >
                <span class="layer-default-filter-name">{{ field.label }}</span>
                <select
                  :value="getFilterValue(layer, field.key)"
                  :data-testid="`layer-filter-${field.key}`"
                  @change="setFilterValue(layer, field.key, $event.target.value)"
                >
                  <option value="">全部</option>
                  <option
                    v-for="option in field.options"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.label }}
                  </option>
                  <option
                    v-if="isStaleFilterValue(layer, field)"
                    disabled
                    :value="getFilterValue(layer, field.key)"
                  >
                    {{ getFilterValue(layer, field.key) }}（当前无此值）
                  </option>
                </select>
              </label>
            </div>
          </div>
        </div>

        <div v-if="listFor(typeKey).length === 0 && !loading" class="layer-empty">
          暂无数据
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.admin-page {
  max-width: var(--content-width, 1200px);
  width: 100%;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-6, 1.5rem);
  margin-bottom: var(--space-6, 1.5rem);
}

.page-header-copy {
  min-width: 0;
}

.page-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-2xl, 1.5rem);
  font-weight: 700;
  color: var(--color-text);
}

.page-desc {
  margin: var(--space-1, 0.25rem) 0 0;
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-muted, #666);
}

.page-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3, 0.75rem);
  flex-shrink: 0;
}

/* section */
.section-head {
  display: flex;
  align-items: center;
  gap: var(--space-3, 0.75rem);
  margin: 0 0 var(--space-3, 0.75rem);
  padding-bottom: var(--space-2, 0.5rem);
  border-bottom: 1px solid var(--color-border);
}

.section-head--first {
  margin-top: 0;
}

.section-head:not(.section-head--first) {
  margin-top: var(--space-8, 2rem);
}

.section-title {
  margin: 0;
  font-size: var(--text-base, 1rem);
  font-weight: 700;
  color: var(--color-text);
}

.section-count {
  display: inline-grid;
  place-items: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: var(--radius-pill, 999px);
  background: var(--color-surface-container, #eee);
  color: var(--color-text-muted, #666);
  font-size: var(--text-xs, 0.75rem);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

/* layer grid */
.layer-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-3, 0.75rem);
}

.layer-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 0.5rem);
  padding: var(--space-3, 0.75rem);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: var(--color-surface);
  transition: box-shadow var(--motion-fast, 150ms) ease,
    opacity var(--motion-fast, 150ms) ease,
    border-color var(--motion-fast, 150ms) ease;
}

.layer-card:hover {
  border-color: color-mix(
    in oklch,
    var(--color-primary, #2a7a5a) 30%,
    var(--color-border, #ddd)
  );
  box-shadow: var(--shadow-sm, 0 4px 16px rgba(0, 0, 0, 0.06));
}

.layer-card.is-disabled {
  opacity: 0.55;
}

.layer-card.is-dragging {
  opacity: 0.4;
  box-shadow: var(--shadow-hover, 0 16px 40px rgba(0, 0, 0, 0.12));
}

/* 拖拽插入指示线（左右） */
.layer-card::before {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--color-primary, #2a7a5a);
  border-radius: 3px;
  opacity: 0;
  pointer-events: none;
  z-index: 2;
  transition: opacity var(--motion-fast, 150ms) ease;
}

.layer-card.is-drag-over-before::before {
  opacity: 1;
  left: -4px;
}

.layer-card.is-drag-over-after::before {
  opacity: 1;
  right: -4px;
}

.layer-card-head {
  display: flex;
  align-items: center;
  gap: var(--space-2, 0.5rem);
}

.layer-handle {
  display: grid;
  place-items: center;
  width: 18px;
  flex-shrink: 0;
  color: var(--color-text-muted, #bbb);
  cursor: grab;
  transition: color var(--motion-fast, 150ms) ease;
}

.layer-card:hover .layer-handle {
  color: var(--color-text-muted, #999);
}

.layer-handle:active {
  cursor: grabbing;
}

.layer-index {
  flex-shrink: 0;
  min-width: 1.5em;
  text-align: center;
  font-size: var(--text-xs, 0.75rem);
  font-weight: 600;
  color: var(--color-text-muted, #999);
  font-variant-numeric: tabular-nums;
}

.name-input {
  flex: 1;
  min-width: 0;
  box-sizing: border-box;
  padding: 0.35rem 0.55rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm, 6px);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
  transition: border-color var(--motion-fast, 150ms) ease,
    box-shadow var(--motion-fast, 150ms) ease;
}

.name-input:hover {
  border-color: color-mix(
    in oklch,
    var(--color-primary, #2a7a5a) 25%,
    var(--color-border, #ddd)
  );
}

.name-input:focus {
  outline: none;
  border-color: var(--color-primary, #2a7a5a);
  box-shadow: 0 0 0 2px
    color-mix(in oklch, var(--color-primary, #2a7a5a) 18%, transparent);
}

.name-input::placeholder {
  color: var(--color-text-muted, #bbb);
  font-weight: 400;
}

.layer-key {
  display: block;
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-text-muted, #999);
  padding: 0 0.3rem;
  font-family: var(--font-mono, monospace);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.layer-toggles {
  display: flex;
  align-items: center;
  gap: var(--space-3, 0.75rem);
  flex-wrap: wrap;
}

.switch {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
  font-size: var(--text-xs, 0.75rem);
  font-weight: 600;
  color: var(--color-text-muted, #999);
  transition: color var(--motion-fast, 150ms) ease;
}

.switch:hover {
  color: var(--color-text, #333);
}

.switch-track {
  position: relative;
  width: 34px;
  height: 20px;
  border-radius: var(--radius-pill, 999px);
  background: #d1d5db;
  transition: background var(--motion-base, 160ms) ease;
}

.switch-track::after {
  content: "";
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: var(--radius-round, 50%);
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
  transition: transform var(--motion-base, 160ms) ease;
}

.switch.is-on {
  color: var(--color-text, #333);
}

.switch.is-on .switch-track {
  background: var(--color-primary, #2a7a5a);
}

.switch.is-on .switch-track::after {
  transform: translateX(14px);
}

.switch-label {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  white-space: nowrap;
}

.layer-default-filters {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 0.5rem);
  padding-top: var(--space-2, 0.5rem);
  border-top: 1px solid var(--color-border);
}

.layer-default-filters-label {
  font-size: var(--text-xs, 0.75rem);
  font-weight: 700;
  color: var(--color-text-muted, #666);
  letter-spacing: 0.04em;
}

.layer-default-filters-fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 0.5rem);
}

.layer-default-filter {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.35rem;
}

.layer-default-filter-name {
  flex-shrink: 0;
  font-size: var(--text-xs, 0.75rem);
  font-weight: 600;
  color: var(--color-text-muted, #666);
}

.layer-default-filter select {
  min-width: 0;
  flex: 1;
  min-height: 28px;
  padding: 0 0.4rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm, 6px);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--text-xs, 0.75rem);
  font-weight: 600;
  cursor: pointer;
}

.layer-default-filter select:hover {
  border-color: color-mix(
    in oklch,
    var(--color-primary, #2a7a5a) 25%,
    var(--color-border, #ddd)
  );
}

.layer-default-filter select:focus {
  outline: none;
  border-color: var(--color-primary, #2a7a5a);
  box-shadow: 0 0 0 2px
    color-mix(in oklch, var(--color-primary, #2a7a5a) 18%, transparent);
}

.layer-empty {
  grid-column: 1 / -1;
  text-align: center;
  padding: 2rem;
  color: var(--color-text-muted, #999);
  font-size: var(--text-sm, 0.875rem);
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2, 0.5rem);
  min-height: 2.5rem;
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--motion-fast, 150ms) var(--ease-standard, ease);
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--color-surface);
  color: var(--color-text);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-surface-container, #f0f0f0);
}

.btn-primary {
  background: var(--color-primary, #2a7a5a);
  color: #fff;
  border-color: var(--color-primary, #2a7a5a);
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.is-spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
