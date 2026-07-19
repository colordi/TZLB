<script setup>
import { computed, onMounted, ref } from "vue";
import { RefreshCw, Save, Eye, EyeOff, GripVertical } from "@lucide/vue";

import { fetchLayers, updateLayers } from "../api/admin.js";
import { fetchMapFilterOptions } from "../api/map.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

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
  <div class="mx-auto w-full max-w-6xl space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="space-y-1">
        <h1 class="text-2xl font-bold tracking-tight">图层管理</h1>
        <p class="text-sm text-muted-foreground">
          拖拽调整图层显示顺序，编辑别名与启用状态，共 {{ totalCount }} 项
        </p>
      </div>
      <div class="page-actions flex items-center gap-2">
        <Button type="button" variant="outline" size="sm" :disabled="loading" @click="load">
          <RefreshCw class="size-4" :class="{ 'animate-spin': loading }" />
          <span>{{ loading ? "加载中" : "刷新" }}</span>
        </Button>
        <Button
          type="button"
          size="sm"
          :disabled="!hasChanges || saving"
          @click="handleSave"
        >
          <Save class="size-4" />
          <span>{{ saving ? "保存中…" : "保存更改" }}</span>
        </Button>
      </div>
    </div>

    <template v-for="(typeKey, typeIdx) in ['view', 'reference']" :key="typeKey">
      <div
        class="flex items-center gap-2 border-b pb-2"
        :class="typeIdx === 0 ? '' : 'mt-8'"
      >
        <h2 class="text-base font-bold">{{ layerTypeLabel[typeKey] }}</h2>
        <Badge variant="secondary">{{ listFor(typeKey).length }}</Badge>
      </div>

      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <Card
          v-for="(layer, index) in listFor(typeKey)"
          :key="layer.id"
          class="relative transition-opacity"
          :class="cn(
            !getEdit(layer).is_enabled && 'opacity-55',
            dragKey === layer.layer_key && 'opacity-40',
            dragOverKey === layer.layer_key && dragOverPos === 'before' && 'ring-2 ring-primary ring-offset-2',
            dragOverKey === layer.layer_key && dragOverPos === 'after' && 'ring-2 ring-primary ring-offset-2',
          )"
          @dragover="onDragOver($event, layer, typeKey)"
          @drop="onDrop($event, layer, typeKey)"
          @dragend="onDragEnd"
        >
          <CardContent class="space-y-3 p-3">
            <div class="flex items-center gap-2">
              <div
                class="flex size-8 cursor-grab items-center justify-center rounded-md text-muted-foreground hover:bg-muted"
                draggable="true"
                title="拖拽排序"
                @dragstart="onDragStart($event, layer, typeKey)"
              >
                <GripVertical class="size-4" />
              </div>
              <span class="w-6 text-center text-xs font-semibold text-muted-foreground">
                {{ index + 1 }}
              </span>
              <Input
                v-model="getEdit(layer).display_name"
                class="h-8"
                draggable="false"
                :placeholder="layer.layer_key"
                @input="markChanged"
              />
            </div>

            <code class="block truncate text-xs text-muted-foreground">{{ layer.layer_key }}</code>

            <div class="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                :variant="getEdit(layer).is_enabled ? 'default' : 'outline'"
                draggable="false"
                :title="getEdit(layer).is_enabled ? '点击停用' : '点击启用'"
                @click="toggleEnabled(layer)"
              >
                <Eye v-if="getEdit(layer).is_enabled" class="size-3.5" />
                <EyeOff v-else class="size-3.5" />
                {{ getEdit(layer).is_enabled ? "启用" : "停用" }}
              </Button>

              <Button
                v-if="layer.layer_type === 'reference'"
                type="button"
                size="sm"
                :variant="getEdit(layer).default_visible ? 'secondary' : 'outline'"
                draggable="false"
                title="默认显隐"
                @click="toggleDefaultVisible(layer)"
              >
                {{ getEdit(layer).default_visible ? "默认显示" : "默认隐藏" }}
              </Button>
            </div>

            <div
              v-if="layer.layer_type === 'view' && configurableFieldsFor(layer).length"
              class="space-y-2 rounded-md border bg-muted/30 p-2"
              data-testid="layer-default-filters"
            >
              <span class="text-xs font-semibold text-muted-foreground">默认筛选</span>
              <div class="grid gap-2">
                <label
                  v-for="field in configurableFieldsFor(layer)"
                  :key="field.key"
                  class="grid gap-1 text-xs"
                >
                  <span class="text-muted-foreground">{{ field.label }}</span>
                  <select
                    class="h-8 rounded-md border border-input bg-background px-2 text-sm"
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
          </CardContent>
        </Card>

        <div
          v-if="listFor(typeKey).length === 0 && !loading"
          class="col-span-full py-8 text-center text-sm text-muted-foreground"
        >
          暂无数据
        </div>
      </div>
    </template>
  </div>
</template>
